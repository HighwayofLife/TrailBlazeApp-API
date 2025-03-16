#!/usr/bin/env python
"""
AERC Calendar Scraper with enhanced error logging and debugging capabilities
"""

import os
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import re
import hashlib
import traceback

import aiohttp
from bs4 import BeautifulSoup
import google.generativeai as genai
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

# Add project root to import paths
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.config import get_settings
from app.logging_config import get_logger
from app.schemas.event import EventCreate
from app.crud.event import create_event, get_events
from scrapers.aerc_scraper.schema import AERC_EVENT_SCHEMA
from scrapers.aerc_scraper.metrics import ScraperMetrics

# Configure logger
logger = get_logger("scrapers.aerc")
settings = get_settings()

# Configure Gemini
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", settings.gemini_api_key)
genai.configure(api_key=GEMINI_API_KEY)

# Pydantic models for structured output
class RideManagerContact(BaseModel):
    name: Optional[str] = Field(None, description="Name of the ride manager")
    email: Optional[str] = Field(None, description="Email of the ride manager")
    phone: Optional[str] = Field(None, description="Phone number of the ride manager")

class ControlJudge(BaseModel):
    role: str = Field(..., description="Role of the judge (e.g., Head Control Judge)")
    name: str = Field(..., description="Name of the judge")

class Distance(BaseModel):
    distance: str = Field(..., description="Distance of the ride")
    date: str = Field(..., description="Date of the ride (YYYY-MM-DD)")
    startTime: Optional[str] = Field(None, description="Start time of the ride")

class AERCEvent(BaseModel):
    rideName: str = Field(..., description="Name of the ride")
    date: str = Field(..., description="Primary date of the event (YYYY-MM-DD)")
    region: str = Field(..., description="AERC region")
    location: str = Field(..., description="Location of the event")
    distances: List[Distance] = Field(default_factory=list, description="Available ride distances")
    rideManager: Optional[str] = Field(None, description="Name of the ride manager")
    rideManagerContact: Optional[RideManagerContact] = Field(None, description="Contact details for the ride manager")
    controlJudges: List[ControlJudge] = Field(default_factory=list, description="Control judges for the event")
    mapLink: Optional[str] = Field(None, description="Google Maps link to the event location")
    hasIntroRide: Optional[bool] = Field(False, description="Whether the event has an intro ride")
    tag: Optional[int] = Field(None, description="External ID for the event")

# Define Gemini schema as a dictionary
GEMINI_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "rideName": {"type": "string"},
            "date": {"type": "string", "format": "date"},
            "region": {"type": "string"},
            "location": {"type": "string"},
            "distances": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "distance": {"type": "string"},
                        "date": {"type": "string", "format": "date"},
                        "startTime": {"type": "string"}
                    },
                    "required": ["distance", "date"]
                }
            },
            "rideManager": {"type": "string"},
            "rideManagerContact": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": "string", "format": "email"},
                    "phone": {"type": "string"}
                }
            },
            "controlJudges": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "role": {"type": "string"},
                        "name": {"type": "string"}
                    },
                    "required": ["role", "name"]
                }
            }
        },
        "required": ["rideName", "date", "region", "location"]
    }
}

class AERCScraper:
    """Scraper for the AERC calendar website."""
    
    BASE_URL = "https://aerc.org/wp-admin/admin-ajax.php"
    CALENDAR_URL = "https://aerc.org/calendar"
    CACHE_DIR = "cache"
    MAX_RETRIES = 3
    RETRY_DELAY = 5  # seconds
    REQUEST_TIMEOUT = 30  # seconds
    INITIAL_CHUNK_SIZE = 30000  # Initial characters for Gemini input
    MIN_CHUNK_SIZE = 15000     # Minimum chunk size to try
    MAX_CHUNK_SIZE = 45000     # Maximum chunk size to try
    CHUNK_ADJUST_FACTOR = 0.75  # Factor to reduce chunk size on failure
    
    def __init__(self):
        """Initialize the AERC scraper with enhanced debugging."""
        self.debug_mode = os.getenv('SCRAPER_DEBUG', 'false').lower() == 'true'
        
        # Configure Gemini models with detailed logging
        self.primary_model = genai.GenerativeModel(
            'gemini-2.0-flash-lite',
            generation_config={
                "temperature": 0.1,
                "candidate_count": 1,
                "max_output_tokens": 8192,
                "stop_sequences": ["]"]  # Ensure we get complete JSON arrays
            }
        )
        
        self.fallback_model = genai.GenerativeModel(
            'gemini-2.0-flash',
            generation_config={
                "temperature": 0.3,
                "candidate_count": 1,
                "max_output_tokens": 8192,
                "stop_sequences": ["]"]
            }
        )
        
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Referer": "https://aerc.org/",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1"
        }
        # Ensure cache directory exists
        os.makedirs(self.CACHE_DIR, exist_ok=True)
        # Initialize metrics with enhanced tracking
        self.metrics = ScraperMetrics(start_time=datetime.now())
        self.metrics.calendar_rows_found = 0
        self.metrics.events_skipped = 0
        self.metrics.events_duplicate = 0
        self.metrics.validation_errors = 0
        self.metrics.primary_model_failures = 0
        self.metrics.fallback_model_successes = 0
        
        # Add chunk size tracking
        self.current_chunk_size = self.INITIAL_CHUNK_SIZE
        self.chunk_success_count = 0
        self.chunk_failure_count = 0

        # Initialize debugging directory
        self.debug_dir = os.path.join(self.CACHE_DIR, 'debug')
        if self.debug_mode:
            os.makedirs(self.debug_dir, exist_ok=True)
        
        # Initialize error tracking
        self.chunk_errors = {}

    def _adjust_chunk_size(self, success: bool, processing_time: float = None) -> None:
        """
        Adjust chunk size based on success/failure patterns and processing time.
        
        Args:
            success: Whether the chunk processing was successful
            processing_time: Time taken to process the chunk in seconds
        """
        if success:
            self.chunk_success_count += 1
            self.chunk_failure_count = 0
            
            # After 3 consecutive successes, consider increasing chunk size
            if self.chunk_success_count >= 3:
                if processing_time and processing_time < 5.0:  # If processing is fast
                    new_size = min(
                        int(self.current_chunk_size * 1.5),  # More aggressive increase
                        self.MAX_CHUNK_SIZE
                    )
                else:
                    new_size = min(
                        int(self.current_chunk_size * 1.25),  # Conservative increase
                        self.MAX_CHUNK_SIZE
                    )
                
                if new_size != self.current_chunk_size:
                    logger.info(f"Increasing chunk size from {self.current_chunk_size} to {new_size}")
                    self.current_chunk_size = new_size
                self.chunk_success_count = 0
        else:
            self.chunk_failure_count += 1
            self.chunk_success_count = 0
            
            # Adjust reduction factor based on consecutive failures
            reduction_factor = max(0.5, 0.75 - (self.chunk_failure_count * 0.1))
            
            new_size = max(
                int(self.current_chunk_size * reduction_factor),
                self.MIN_CHUNK_SIZE
            )
            
            if new_size != self.current_chunk_size:
                logger.info(
                    f"Reducing chunk size from {self.current_chunk_size} to {new_size} "
                    f"(failure #{self.chunk_failure_count})"
                )
                self.current_chunk_size = new_size
                
        # Log chunk size metrics
        if self.debug_mode:
            self._save_debug_info('chunk_size_adjustment', {
                'timestamp': datetime.now().isoformat(),
                'success': success,
                'processing_time': processing_time,
                'new_chunk_size': self.current_chunk_size,
                'consecutive_successes': self.chunk_success_count,
                'consecutive_failures': self.chunk_failure_count
            })

    def _get_cache_path(self, key: str) -> str:
        """Generate a cache file path for a given key."""
        hash_key = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self.CACHE_DIR, f"{hash_key}.json")

    def _load_cache(self, key: str) -> Optional[Any]:
        """Load cached data for a given key."""
        cache_path = self._get_cache_path(key)
        if os.path.exists(cache_path):
            with open(cache_path, 'r') as cache_file:
                return json.load(cache_file)
        return None

    def _save_cache(self, key: str, data: Any) -> None:
        """Save data to cache for a given key."""
        cache_path = self._get_cache_path(key)
        with open(cache_path, 'w') as cache_file:
            json.dump(data, cache_file)

    def _save_debug_info(self, chunk_idx: int, stage: str, data: Any, error: Optional[Exception] = None) -> None:
        """Save debugging information for failed chunks."""
        if not self.debug_mode:
            return
            
        debug_file = os.path.join(
            self.debug_dir, 
            f'chunk_{chunk_idx}_{stage}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        )
        
        debug_info = {
            'timestamp': datetime.now().isoformat(),
            'chunk_index': chunk_idx,
            'stage': stage,
            'chunk_size': len(str(data)) if isinstance(data, (str, dict, list)) else 0
        }
        
        if error:
            debug_info.update({
                'error_type': type(error).__name__,
                'error_message': str(error),
                'traceback': traceback.format_exc()
            })
            
        if isinstance(data, (str, dict, list)):
            debug_info['data'] = data
            
        try:
            with open(debug_file, 'w') as f:
                json.dump(debug_info, f, indent=2)
            logger.debug(f"Saved debug info to {debug_file}")
        except Exception as e:
            logger.error(f"Failed to save debug info: {e}")
    
    async def _make_request(self, url: str, method: str = "GET", data: Dict = None, retry_count: int = 0) -> Optional[str]:
        """Make an HTTP request with retry logic."""
        self.metrics.http_requests += 1
        
        if retry_count >= self.MAX_RETRIES:
            self.metrics.http_errors += 1
            logger.error(f"Max retries ({self.MAX_RETRIES}) exceeded for {url}")
            return None
            
        try:
            timeout = aiohttp.ClientTimeout(total=self.REQUEST_TIMEOUT)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                request_func = session.post if method == "POST" else session.get
                async with request_func(url, data=data, headers=self.headers) as response:
                    if response.status == 429:  # Too Many Requests
                        retry_after = int(response.headers.get('Retry-After', self.RETRY_DELAY))
                        logger.warning(f"Rate limited. Waiting {retry_after} seconds before retry")
                        await asyncio.sleep(retry_after)
                        self.metrics.request_retries += 1
                        return await self._make_request(url, method, data, retry_count + 1)
                        
                    elif response.status >= 500:  # Server errors
                        logger.warning(f"Server error {response.status}. Retrying in {self.RETRY_DELAY} seconds")
                        await asyncio.sleep(self.RETRY_DELAY)
                        self.metrics.request_retries += 1
                        return await self._make_request(url, method, data, retry_count + 1)
                        
                    elif response.status != 200:
                        self.metrics.http_errors += 1
                        logger.error(f"HTTP {response.status} error for {url}")
                        return None
                        
                    return await response.text()
                    
        except asyncio.TimeoutError:
            logger.warning(f"Request timeout. Retrying in {self.RETRY_DELAY} seconds")
            await asyncio.sleep(self.RETRY_DELAY)
            self.metrics.request_retries += 1
            return await self._make_request(url, method, data, retry_count + 1)
            
        except Exception as e:
            self.metrics.http_errors += 1
            logger.error(f"Request error: {e}")
            if retry_count < self.MAX_RETRIES:
                self.metrics.request_retries += 1
                await asyncio.sleep(self.RETRY_DELAY)
                return await self._make_request(url, method, data, retry_count + 1)
            return None

    async def extract_season_ids(self) -> List[str]:
        """Extract season IDs from the AERC calendar page."""
        response_text = await self._make_request(self.CALENDAR_URL)
        if not response_text:
            return []
            
        try:
            soup = BeautifulSoup(response_text, 'html.parser')
            season_inputs = soup.select('input[name="season[]"]')
            season_ids = []
            
            for input_tag in season_inputs:
                season_id = input_tag.get('value')
                year_text = input_tag.find_next_sibling(string=True) or input_tag.parent.get_text()
                year_match = re.search(r'20\d{2}', year_text)
                
                if season_id and year_match:
                    year = year_match.group(0)
                    logger.info(f"Found season ID {season_id} for year {year}")
                    season_ids.append(season_id)
            
            return season_ids[:2]  # Get current and next year IDs
            
        except Exception as e:
            logger.exception(f"Error extracting season IDs: {e}")
            return []

    async def fetch_calendar_html(self, season_ids: List[str]) -> str:
        """Fetch calendar HTML from AERC website."""
        if not season_ids:
            logger.error("No season IDs provided")
            return ""

        cache_key = f"calendar_html_{'_'.join(season_ids)}"
        cached_html = self._load_cache(cache_key)
        if cached_html:
            logger.info("Loaded calendar HTML from cache")
            return cached_html

        data = {
            'action': 'aerc_calendar_form',
            'calendar': 'calendar',
            'country[]': ['United States', 'Canada'],
            'within': '',
            'zip': '',
            'span[]': '#cal-span-season',
            'season[]': season_ids,
            'daterangefrom': '',
            'daterangeto': '',
            'distance[]': 'any',
        }

        response_text = await self._make_request(self.BASE_URL, "POST", data)
        if not response_text:
            return ""
            
        try:
            json_data = json.loads(response_text)
            if 'html' in json_data:
                html_content = json_data['html']
                logger.info(f"Extracted HTML from JSON response (length: {len(html_content)})")
                self._save_cache(cache_key, html_content)
                return html_content
            else:
                logger.error("JSON response does not contain 'html' field")
                return ""
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON response")
            # If we can't parse as JSON, return the raw response as it may be direct HTML
            self._save_cache(cache_key, response_text)
            return response_text
    
    def clean_html(self, html: str) -> str:
        """Clean the HTML to prepare for processing."""
        if not html:
            return ""
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove unnecessary elements
            for tag in ['script', 'style', 'header', 'footer', 'nav']:
                for element in soup.find_all(tag):
                    element.decompose()
            
            # Focus on calendar rows
            calendar_rows = soup.find_all('div', class_='calendarRow')
            row_count = len(calendar_rows)
            logger.info(f"Found {row_count} calendar rows")
            self.metrics.calendar_rows_found = row_count
            
            if not calendar_rows:
                logger.error("No calendar rows found in the HTML")
                return ""
            
            # Create a container for the rows
            container = soup.new_tag('div')
            container['id'] = 'calendar-content'
            
            for row in calendar_rows:
                container.append(row)
            
            return str(container)
        
        except Exception as e:
            logger.exception(f"Error cleaning HTML: {e}")
            return ""

    async def extract_structured_data(self, html: str) -> List[Dict[str, Any]]:
        """Extract structured data from HTML with enhanced error logging."""
        if not html:
            logger.error("No HTML provided for extraction")
            return []
        
        # Take initial memory sample
        self.metrics.sample_memory()
        
        cache_key = f"structured_data_{hashlib.md5(html.encode()).hexdigest()}"
        cached_data = self._load_cache(cache_key)
        if cached_data:
            logger.info("Loaded structured data from cache")
            return cached_data
        
        self.metrics.gemini_calls += 1
        chunks = self._chunk_html(html)
        all_events = []
        chunk_errors = []
        
        for chunk_idx, chunk in enumerate(chunks):
            # Take memory sample before processing each chunk
            mem_sample = self.metrics.sample_memory()
            logger.debug(
                f"Memory before chunk {chunk_idx + 1}: "
                f"RSS={mem_sample['rss']:.1f}MB, "
                f"VMS={mem_sample['vms']:.1f}MB"
            )
            
            logger.info(f"Processing chunk {chunk_idx + 1} of {len(chunks)} (size: {len(chunk)})")
            
            if self.debug_mode:
                self._save_debug_info(chunk_idx, 'input_chunk', chunk)
            
            success = False
            retry_count = 0
            current_chunk = chunk
            
            while not success and retry_count < self.MAX_RETRIES:
                try:
                    # Try primary model
                    prompt = self._create_prompt(current_chunk)
                    if self.debug_mode:
                        self._save_debug_info(chunk_idx, f'prompt_attempt_{retry_count}', prompt)
                    
                    response = await asyncio.to_thread(
                        lambda: self.primary_model.generate_content(prompt)
                    )
                    
                    events = await self._process_gemini_response(response, chunk_idx)
                    if events:
                        all_events.extend(events)
                        success = True
                        break
                    
                    # Try fallback model
                    logger.info(f"Primary model failed for chunk {chunk_idx + 1}, trying fallback")
                    response = await asyncio.to_thread(
                        lambda: self.fallback_model.generate_content(prompt)
                    )
                    
                    events = await self._process_gemini_response(response, chunk_idx)
                    if events:
                        all_events.extend(events)
                        self.metrics.fallback_model_successes += 1
                        success = True
                        break
                    
                    # Handle failure
                    if retry_count < self.MAX_RETRIES - 1:
                        current_chunk = self._split_chunk(current_chunk)
                        logger.info(f"Retrying chunk {chunk_idx + 1} with size {len(current_chunk)}")
                        retry_count += 1
                    else:
                        error_info = {
                            'chunk_idx': chunk_idx,
                            'attempts': retry_count + 1,
                            'final_chunk_size': len(current_chunk)
                        }
                        chunk_errors.append(error_info)
                        logger.error(f"Failed to process chunk {chunk_idx + 1} after {retry_count + 1} attempts")
                        
                except Exception as e:
                    logger.exception(f"Error processing chunk {chunk_idx + 1}")
                    if retry_count < self.MAX_RETRIES - 1:
                        current_chunk = self._split_chunk(current_chunk)
                        retry_count += 1
                    else:
                        chunk_errors.append({
                            'chunk_idx': chunk_idx,
                            'error': str(e),
                            'traceback': traceback.format_exc()
                        })
                        break
            
            # Take memory sample after processing chunk
            mem_sample = self.metrics.sample_memory()
            logger.debug(
                f"Memory after chunk {chunk_idx + 1}: "
                f"RSS={mem_sample['rss']:.1f}MB, "
                f"VMS={mem_sample['vms']:.1f}MB"
            )
        
        # Take final memory sample
        self.metrics.sample_memory()
        
        # Save error summary if in debug mode
        if self.debug_mode and chunk_errors:
            error_file = os.path.join(self.debug_dir, f'chunk_errors_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
            with open(error_file, 'w') as f:
                json.dump(chunk_errors, f, indent=2)
        
        if all_events:
            self._save_cache(cache_key, all_events)
            logger.info(f"Total events extracted: {len(all_events)}")
            return all_events
        else:
            logger.error("No events extracted from any method")
            return []

    async def _process_gemini_response(self, response, chunk_idx: int) -> List[Dict[str, Any]]:
        """Process Gemini API response with enhanced error logging."""
        # Take memory sample before processing
        mem_before = self.metrics.sample_memory()
        
        try:
            # Log raw response for debugging
            if self.debug_mode:
                self._save_debug_info(chunk_idx, 'raw_response', response.text)
            
            # Clean and process the response
            text = response.text.strip()
            
            # Take memory sample after text processing
            mem_after = self.metrics.sample_memory()
            logger.debug(
                f"Memory usage during response processing: "
                f"Before={mem_before['rss']:.1f}MB, "
                f"After={mem_after['rss']:.1f}MB"
            )
            
            # Remove any markdown code block syntax
            text = re.sub(r'```(?:json)?\s*(.*?)\s*```', r'\1', text, flags=re.DOTALL)
            
            # Find the JSON array
            start_idx = text.find('[')
            end_idx = text.rfind(']')
            
            if start_idx == -1 or end_idx == -1:
                logger.warning(f"No JSON array found in response for chunk {chunk_idx}")
                self._save_debug_info(chunk_idx, 'no_json_array', text)
                return []
            
            # Extract and clean JSON string
            json_str = text[start_idx:end_idx + 1]
            json_str = re.sub(r',\s*]', ']', json_str)  # Fix trailing commas
            json_str = re.sub(r',\s*}', '}', json_str)  # Fix trailing commas in objects
            
            if self.debug_mode:
                self._save_debug_info(chunk_idx, 'cleaned_json', json_str)
            
            try:
                events_json = json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error in chunk {chunk_idx}: {e}")
                self._save_debug_info(chunk_idx, 'json_decode_error', {
                    'error_position': e.pos,
                    'error_message': e.msg,
                    'json_context': json_str[max(0, e.pos-100):min(len(json_str), e.pos+100)]
                }, error=e)
                return []
            
            # Validate and clean events
            valid_events = []
            for idx, event in enumerate(events_json):
                try:
                    validated_event = AERCEvent.model_validate(event)
                    valid_events.append(validated_event.model_dump())
                except ValidationError as e:
                    logger.warning(f"Validation error in event {idx} of chunk {chunk_idx}")
                    self._save_debug_info(
                        chunk_idx,
                        f'validation_error_event_{idx}',
                        {'event': event, 'validation_errors': e.errors()},
                        error=e
                    )
                    continue
            
            if valid_events:
                logger.info(f"Successfully extracted {len(valid_events)} events from chunk {chunk_idx}")
                return valid_events
            else:
                logger.warning(f"No valid events found in chunk {chunk_idx}")
                return []
            
        except Exception as e:
            logger.error(f"Unexpected error processing chunk {chunk_idx}: {e}")
            self._save_debug_info(chunk_idx, 'unexpected_error', response.text, error=e)
            return []

    def _chunk_html(self, html: str) -> List[str]:
        """Split HTML into manageable chunks for Gemini processing."""
        soup = BeautifulSoup(html, 'html.parser')
        rows = soup.find_all('div', class_='calendarRow')
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        for row in rows:
            row_html = str(row)
            row_size = len(row_html)
            
            if current_size + row_size > self.current_chunk_size:
                # Create a new chunk with proper HTML structure
                chunk_html = f'<div class="calendar-content">{"".join(current_chunk)}</div>'
                chunks.append(chunk_html)
                current_chunk = [row_html]
                current_size = row_size
            else:
                current_chunk.append(row_html)
                current_size += row_size
        
        # Add the final chunk
        if current_chunk:
            chunk_html = f'<div class="calendar-content">{"".join(current_chunk)}</div>'
            chunks.append(chunk_html)
        
        logger.info(f"Split HTML into {len(chunks)} chunks (current chunk size: {self.current_chunk_size})")
        return chunks

    def _create_prompt(self, chunk: str) -> str:
        """Create a prompt for Gemini models."""
        return f"""
        Extract endurance ride events from this AERC calendar HTML.
        Return ONLY a JSON array of events with the following fields:
        - rideName (required): string, name of the ride
        - date (required): string, YYYY-MM-DD format
        - region (required): string, AERC region
        - location (required): string, location of the event
        - distances: array of objects with distance (string) and date (YYYY-MM-DD)
        - rideManager: string, name of the ride manager
        - rideManagerContact: object with name, email, and phone fields
        - controlJudges: array of objects with role and name fields
        - mapLink: string, Google Maps link
        - hasIntroRide: boolean

        Calendar HTML:
        {chunk}
        """

    def _split_chunk(self, chunk: str) -> str:
        """Split a chunk into a smaller piece for retry."""
        soup = BeautifulSoup(chunk, 'html.parser')
        rows = soup.find_all('div', class_='calendarRow')
        
        if len(rows) <= 1:
            return chunk  # Can't split further
            
        # Take first half of the rows
        half = len(rows) // 2
        new_chunk = []
        for i in range(half):
            new_chunk.append(str(rows[i]))
        
        return f'<div class="calendar-content">{"".join(new_chunk)}</div>'

    def parse_gemini_output(self, text: str) -> List[Dict[str, Any]]:
        """Parse Gemini output to extract JSON data."""
        try:
            # Remove any non-JSON content before and after the array
            text = text.strip()
            start_idx = text.find('[')
            end_idx = text.rfind(']')
            
            if start_idx == -1 or end_idx == -1:
                logger.error("No JSON array found in Gemini output")
                return []
            
            json_str = text[start_idx:end_idx + 1]
            
            # Clean up common JSON formatting issues
            json_str = re.sub(r',\s*}', '}', json_str)  # Remove trailing commas in objects
            json_str = re.sub(r',\s*]', ']', json_str)  # Remove trailing commas in arrays
            
            data = json.loads(json_str)
            
            # Validate the extracted data
            if isinstance(data, list) and len(data) > 0:
                valid_data = self.validate_events(data)
                logger.info(f"Successfully extracted {len(valid_data)} events")
                return valid_data
            
            return []
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from Gemini output: {e}")
            logger.debug(f"Problematic JSON: {text[:200]}...")  # Log start of problematic text
            return []

    def validate_events(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate extracted events data and fill in defaults for required fields."""
        self.metrics.events_found = len(events)
        valid_events = []
        seen_events = set()  # Track unique event identifiers
        
        for event in events:
            try:
                # Generate a stable event identifier for deduplication
                event_key = f"{event.get('rideName', '')}-{event.get('date', '')}-{event.get('location', '')}"
                if event_key in seen_events:
                    self.metrics.events_duplicate += 1
                    logger.debug(f"Skipping duplicate event: {event_key}")
                    continue
                seen_events.add(event_key)
                
                # Fill in defaults for required fields if missing
                event['rideName'] = event.get('rideName', 'Untitled AERC Event').strip()
                event['region'] = event.get('region', 'Unknown Region').strip()
                event['date'] = event.get('date')
                
                if not event['date']:
                    self.metrics.validation_errors += 1
                    logger.warning(f"Skipping event with no date: {event['rideName']}")
                    continue
                
                # Clean and validate location
                event['location'] = event.get('location', 'Location TBA').strip()
                if event['location'].lower() in ['tba', 'to be announced']:
                    event['location'] = 'Location TBA'
                
                # Ensure distances is a list and clean distance data
                if not event.get('distances'):
                    event['distances'] = [{"distance": "Unknown", "date": event['date']}]
                else:
                    cleaned_distances = []
                    for distance in event['distances']:
                        if isinstance(distance, dict):
                            # Clean distance string and ensure required fields
                            dist_str = str(distance.get('distance', '')).strip()
                            if dist_str and distance.get('date'):
                                cleaned_distances.append({
                                    "distance": dist_str,
                                    "date": distance['date'],
                                    "startTime": distance.get('startTime', '').strip()
                                })
                    if cleaned_distances:
                        event['distances'] = cleaned_distances
                    else:
                        event['distances'] = [{"distance": "Unknown", "date": event['date']}]
                
                # Clean and validate contact information
                if event.get('rideManagerContact'):
                    contact = event['rideManagerContact']
                    # Clean email
                    if contact.get('email'):
                        email = contact['email'].strip().lower()
                        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                            logger.warning(f"Invalid email format for {event['rideName']}: {email}")
                            contact['email'] = None
                            self.metrics.validation_errors += 1
                    # Clean phone
                    if contact.get('phone'):
                        phone = re.sub(r'[^\d+]', '', contact['phone'])
                        if not re.match(r'^\+?\d{10,}$', phone):
                            logger.warning(f"Invalid phone format for {event['rideName']}: {contact['phone']}")
                            contact['phone'] = None
                            self.metrics.validation_errors += 1
                    # Clean name
                    if contact.get('name'):
                        contact['name'] = contact['name'].strip()
                
                # Clean and validate control judges
                if event.get('controlJudges'):
                    cleaned_judges = []
                    for judge in event['controlJudges']:
                        if isinstance(judge, dict) and judge.get('name'):
                            cleaned_judges.append({
                                "role": judge.get('role', 'Judge').strip(),
                                "name": judge['name'].strip()
                            })
                    event['controlJudges'] = cleaned_judges
                
                # Generate a stable external ID if missing
                if not event.get('tag'):
                    event['tag'] = int(hashlib.md5(
                        f"{event['rideName']}-{event['date']}-{event['location']}".encode()
                    ).hexdigest()[:8], 16)
                
                valid_events.append(event)
                logger.debug(f"Validated event: {event['rideName']}")
            
            except Exception as e:
                self.metrics.validation_errors += 1
                logger.error(f"Error validating event: {e}")
                logger.debug(f"Problematic event data: {event}")
                continue
        
        logger.info(f"Validated {len(valid_events)} out of {len(events)} events")
        self.metrics.events_valid = len(valid_events)
        self.metrics.events_duplicate = len(events) - len(valid_events) - self.metrics.validation_errors
        return valid_events
    
    def fallback_extraction(self, html: str) -> List[Dict[str, Any]]:
        """Fallback to regex-based extraction when Gemini fails."""
        try:
            events = []
            soup = BeautifulSoup(html, 'html.parser')
            
            for row in soup.find_all('div', class_='calendarRow'):
                try:
                    event = {}
                    
                    # Extract region and ride name
                    for span in row.find_all('span'):
                        if 'region' in span.get('class', []):
                            event['region'] = span.text.strip()
                        elif 'rideName' in span.get('class', []):
                            event['rideName'] = span.text.strip()
                    
                    # Extract date
                    date_elem = row.find('div', class_='bold')
                    if date_elem:
                        date_str = date_elem.text.strip()
                        date_match = re.search(r'\b(\d{1,2}/\d{1,2}/\d{4})\b', date_str)
                        if date_match:
                            try:
                                date_str = date_match.group(1)
                                date_obj = datetime.strptime(date_str, '%m/%d/%Y')
                                event['date'] = date_obj.strftime('%Y-%m-%d')
                            except ValueError as e:
                                logger.warning(f"Failed to parse date {date_str}: {e}")
                                continue
                    
                    # Extract location
                    location_elem = row.find('a', href=lambda href: href and 'maps.google.com' in href)
                    if location_elem:
                        event['location'] = location_elem.text.strip()
                        event['mapLink'] = location_elem['href']
                    
                    # Extract distances
                    distances = []
                    distance_table = row.find('table')
                    if distance_table:
                        for tr in distance_table.find_all('tr'):
                            cells = tr.find_all('td')
                            if len(cells) >= 2:
                                distance_text = cells[0].text.strip()
                                if re.search(r'\d+', distance_text):  # Only add if contains numbers
                                    distances.append({
                                        "distance": distance_text,
                                        "date": event.get('date', ''),
                                        "startTime": cells[1].text.strip() if len(cells) > 1 else ""
                                    })
                    event['distances'] = distances
                    
                    # Extract ride manager
                    contact_info = {}
                    manager_section = row.find(string=lambda s: isinstance(s, str) and 'Ride Manager' in s)
                    if manager_section:
                        container = manager_section.find_parent('div')
                        if container:
                            contact_div = container.find_next_sibling('div')
                            if contact_div:
                                contact_text = contact_div.text.strip()
                                event['rideManager'] = contact_text
                                
                                # Extract email
                                email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', contact_text)
                                if email_match:
                                    contact_info['email'] = email_match.group(0)
                                
                                # Extract phone
                                phone_match = re.search(r'(?:\+1[- ]?)?\(?\d{3}\)?[- ]?\d{3}[- ]?\d{4}', contact_text)
                                if phone_match:
                                    contact_info['phone'] = phone_match.group(0)
                                
                                # Set name as remaining text after removing email and phone
                                name_text = contact_text
                                if contact_info.get('email'):
                                    name_text = name_text.replace(contact_info['email'], '')
                                if contact_info.get('phone'):
                                    name_text = name_text.replace(contact_info['phone'], '')
                                contact_info['name'] = re.sub(r'\s+', ' ', name_text).strip()
                    
                    event['rideManagerContact'] = contact_info
                    
                    # Extract control judges
                    judges = []
                    judge_section = row.find(string=lambda s: isinstance(s, str) and 'Control Judge' in s)
                    if judge_section:
                        container = judge_section.find_parent('div')
                        if container:
                            judge_div = container.find_next_sibling('div')
                            if judge_div:
                                judges.append({
                                    "role": "Head Control Judge",
                                    "name": judge_div.text.strip()
                                })
                    event['controlJudges'] = judges
                    
                    # Set required fields and validate
                    if event.get('rideName') and event.get('date') and len(event.get('distances', [])) > 0:
                        event['hasIntroRide'] = bool(re.search(r'intro|introductory', str(row), re.I))
                        event['tag'] = int(hashlib.md5(
                            f"{event['rideName']}-{event['date']}".encode()
                        ).hexdigest()[:8], 16)
                        events.append(event)
                        logger.debug(f"Extracted event: {event['rideName']} on {event['date']}")
                
                except Exception as e:
                    logger.error(f"Error processing row in fallback extraction: {e}")
                    continue
            
            logger.info(f"Fallback extraction found {len(events)} events")
            return events
        
        except Exception as e:
            logger.exception(f"Fallback extraction failed: {e}")
            return []
    
    def convert_to_db_events(self, events: List[Dict[str, Any]]) -> List[EventCreate]:
        """Convert extracted events to database event schema."""
        db_events = []
        
        for event in events:
            try:
                # Format distances list for DB schema
                distances = []
                if event.get('distances'):
                    distances = [d.get('distance') for d in event['distances'] if d.get('distance')]
                
                # Get event start and end date
                date_start = datetime.strptime(event.get('date'), "%Y-%m-%d") if event.get('date') else None
                date_end = date_start
                
                # If multiple days, find the latest date
                if event.get('distances'):
                    for distance in event['distances']:
                        if distance.get('date'):
                            try:
                                distance_date = datetime.strptime(distance['date'], "%Y-%m-%d")
                                if distance_date > date_end:
                                    date_end = distance_date
                            except ValueError:
                                continue
                
                # Create contact info string
                contact_info = []
                if event.get('rideManager'):
                    contact_info.append(f"Ride Manager: {event['rideManager']}")
                if event.get('rideManagerContact'):
                    contact = event['rideManagerContact']
                    if contact.get('phone'):
                        contact_info.append(f"Phone: {contact['phone']}")
                    if contact.get('email'):
                        contact_info.append(f"Email: {contact['email']}")
                
                # Format control judges
                judges = []
                if event.get('controlJudges'):
                    for judge in event['controlJudges']:
                        if judge.get('name'):
                            role = judge.get('role', 'Judge')
                            judges.append(f"{role}: {judge['name']}")
                
                # Create event object
                db_event = EventCreate(
                    name=event['rideName'],
                    date_start=date_start,
                    date_end=date_end,
                    location=event['location'],
                    region=event.get('region', 'Unknown'),
                    event_type='endurance',
                    description="\n".join(contact_info) if contact_info else None,
                    additional_info="\n".join(judges) if judges else None,
                    distances=distances,
                    map_url=event.get('mapLink'),
                    has_intro_ride=event.get('hasIntroRide', False),
                    external_id=str(event.get('tag')) if event.get('tag') else None,
                    source='AERC'
                )
                
                db_events.append(db_event)
                
            except Exception as e:
                logger.error(f"Error converting event to DB schema: {e}")
                continue
        
        return db_events
    
    async def store_events(self, db_events: List[EventCreate], db: AsyncSession) -> Dict[str, int]:
        """Store events in the database."""
        added_count = 0
        updated_count = 0
        skipped_count = 0
        
        for event in db_events:
            try:
                # Check if event exists (by name and date)
                existing_events = await get_events(
                    db,
                    date_from=event.date_start.isoformat() if event.date_start else None,
                    date_to=event.date_start.isoformat() if event.date_start else None
                )
                
                exists = False
                for existing in existing_events:
                    if existing.name == event.name and existing.location == event.location:
                        exists = True
                        break
                
                if not exists:
                    await create_event(db, event)
                    added_count += 1
                    logger.info(f"Created new event: {event.name}")
                else:
                    updated_count += 1
                    logger.info(f"Event already exists: {event.name}")
            except Exception as e:
                skipped_count += 1
                logger.error(f"Error storing event in database: {e}")
        
        self.metrics.events_added = added_count
        self.metrics.events_updated = updated_count
        self.metrics.events_skipped = skipped_count
        return {
            "added": added_count, 
            "updated": updated_count,
            "skipped": skipped_count
        }
    
    async def run(self, db: AsyncSession) -> Dict[str, Any]:
        """Run the AERC scraper end-to-end."""
        try:
            result = await self._run_scraper(db)
            
            # Complete and save metrics
            self.metrics.end_time = datetime.now()
            self.metrics.log_summary()
            self.metrics.save_to_file()
            
            return result
            
        except Exception as e:
            logger.exception(f"Error running AERC scraper: {e}")
            self.metrics.end_time = datetime.now()
            self.metrics.log_summary()
            self.metrics.save_to_file()
            return {"status": "error", "message": str(e)}

    async def _run_scraper(self, db: AsyncSession) -> Dict[str, Any]:
        """Internal method to run the scraper logic."""
        # 1. Extract season IDs
        logger.info("Extracting season IDs")
        season_ids = await self.extract_season_ids()
        if not season_ids:
            logger.error("Failed to extract season IDs")
            return {"status": "error", "message": "Failed to extract season IDs"}
        
        # 2. Fetch calendar HTML
        logger.info("Fetching calendar HTML")
        html = await self.fetch_calendar_html(season_ids)
        if not html:
            logger.error("Failed to fetch calendar HTML")
            return {"status": "error", "message": "Failed to fetch calendar HTML"}
        
        # 3. Clean HTML
        logger.info("Cleaning HTML")
        cleaned_html = self.clean_html(html)
        if not cleaned_html:
            logger.error("Failed to clean HTML")
            return {"status": "error", "message": "Failed to clean HTML"}
        
        # 4. Extract structured data
        logger.info("Extracting structured data")
        events_data = await self.extract_structured_data(cleaned_html)
        if not events_data:
            logger.error("Failed to extract structured data")
            return {"status": "error", "message": "Failed to extract structured data"}
        
        # 5. Convert to database schema
        logger.info("Converting to database schema")
        db_events = self.convert_to_db_events(events_data)
        
        # 6. Store in database
        logger.info("Storing events in database")
        result = await self.store_events(db_events, db)
        
        return {
            "status": "success",
            "scraper": "aerc_calendar",
            "events_found": self.metrics.events_found,
            "events_valid": self.metrics.events_valid,
            "events_added": self.metrics.events_added,
            "events_updated": self.metrics.events_updated,
            "events_skipped": self.metrics.events_skipped,
            "validation_errors": self.metrics.validation_errors,
            "success_rate": (self.metrics.events_valid / self.metrics.events_found * 100) if self.metrics.events_found > 0 else 0
        }

    async def _run_in_terminal(self, command: str) -> str:
        """Run a command in terminal and return output."""
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            logger.error(f"Command failed with exit code {process.returncode}")
            logger.error(f"stderr: {stderr.decode()}")
            raise RuntimeError(f"Command failed: {stderr.decode()}")
            
        return stdout.decode()

async def run_aerc_scraper(db: AsyncSession) -> Dict[str, Any]:
    """Run the AERC scraper."""
    scraper = AERCScraper()
    return await scraper.run(db)

if __name__ == "__main__":
    print("AERC Scraper must be run through the main scraping system")
