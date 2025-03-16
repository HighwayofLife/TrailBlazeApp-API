#!/usr/bin/env python
"""
AERC Calendar Scraper

This module extracts event data from the AERC calendar and processes it using
the Gemini API for structured data extraction.
"""

import os
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import re
import hashlib

import aiohttp
from bs4 import BeautifulSoup
import google.generativeai as genai
from pydantic import BaseModel, Field
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
    MAX_CHUNK_SIZE = 30000  # characters for Gemini input
    
    def __init__(self):
        """Initialize the AERC scraper."""
        self.model = genai.GenerativeModel(
            'gemini-2.0-flash-lite',
            generation_config={"temperature": 0.3}
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
        """Extract structured data from HTML using Gemini."""
        if not html:
            logger.error("No HTML provided for extraction")
            return []

        cache_key = f"structured_data_{hashlib.md5(html.encode()).hexdigest()}"
        cached_data = self._load_cache(cache_key)
        if cached_data:
            logger.info("Loaded structured data from cache")
            return cached_data
        
        self.metrics.gemini_calls += 1
        chunks = self._chunk_html(html)
        all_events = []
        
        for chunk_idx, chunk in enumerate(chunks):
            logger.info(f"Processing chunk {chunk_idx + 1} of {len(chunks)}")
            
            prompt = f"""
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
            
            try:
                # First attempt with primary model
                response = await asyncio.to_thread(
                    lambda: self.model.generate_content(
                        prompt,
                        generation_config={
                            "temperature": 0.1,
                            "candidate_count": 1,
                            "max_output_tokens": 8192,
                        }
                    )
                )
                
                try:
                    # Clean the response text to ensure it's valid JSON
                    text = response.text.strip()
                    text = re.sub(r'```(?:json)?\s*(.*?)\s*```', r'\1', text, flags=re.DOTALL)  # Remove code blocks
                    text = text.replace('\n', ' ').strip()  # Remove newlines
                    start_idx = text.find('[')
                    end_idx = text.rfind(']')
                    if start_idx != -1 and end_idx != -1:
                        json_str = text[start_idx:end_idx + 1]
                        # Clean up common JSON issues
                        json_str = re.sub(r',\s*]', ']', json_str)
                        json_str = re.sub(r',\s*}', '}', json_str)
                        events_json = json.loads(json_str)
                        chunk_events = [AERCEvent.model_validate(event).model_dump() for event in events_json]
                        all_events.extend(chunk_events)
                        logger.info(f"Successfully extracted {len(chunk_events)} events from chunk {chunk_idx + 1}")
                        continue
                    else:
                        logger.warning(f"No JSON array found in response for chunk {chunk_idx + 1}")
                except Exception as e:
                    logger.warning(f"Failed to validate events from model: {e}")
                
                # If extraction fails, use fallback
                logger.warning(f"Gemini extraction failed for chunk {chunk_idx + 1}, using fallback")
                self.metrics.gemini_errors += 1
                fallback_events = self.fallback_extraction(chunk)
                all_events.extend(fallback_events)
                
            except Exception as e:
                logger.exception(f"Error in chunk {chunk_idx + 1}: {e}")
                self.metrics.gemini_errors += 1
                fallback_events = self.fallback_extraction(chunk)
                all_events.extend(fallback_events)
        
        if all_events:
            self._save_cache(cache_key, all_events)
            logger.info(f"Total events extracted: {len(all_events)}")
            return all_events
        else:
            logger.error("No events extracted from any method")
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
            
            if current_size + row_size > self.MAX_CHUNK_SIZE:
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
        
        logger.info(f"Split HTML into {len(chunks)} chunks")
        return chunks
    
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
        
        for event in events:
            try:
                # Fill in defaults for required fields if missing
                event['rideName'] = event.get('rideName', 'Untitled AERC Event')
                event['region'] = event.get('region', 'Unknown Region')
                event['date'] = event.get('date')
                
                if not event['date']:
                    self.metrics.validation_errors += 1
                    logger.warning(f"Skipping event with no date: {event['rideName']}")
                    continue
                
                # Ensure distances is a list
                if not event.get('distances'):
                    event['distances'] = [{"distance": "Unknown", "date": event['date']}]
                    logger.warning(f"Added default distance for event: {event['rideName']}")
                
                # Validate email format if present
                if event.get('rideManagerContact') and event['rideManagerContact'].get('email'):
                    email = event['rideManagerContact']['email']
                    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                        logger.warning(f"Invalid email format for {event['rideName']}: {email}")
                        event['rideManagerContact']['email'] = None
                        self.metrics.validation_errors += 1
                
                # Ensure location is set
                event['location'] = event.get('location', 'Location TBA')
                
                # Generate a stable external ID if missing
                if not event.get('tag'):
                    event['tag'] = int(hashlib.md5(
                        f"{event['rideName']}-{event['date']}".encode()
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
                                pass
                
                # Extract judges to a list of strings
                judges = []
                if event.get('controlJudges'):
                    judges = [f"{judge.get('role', '')}: {judge.get('name', '')}" for judge in event['controlJudges']]
                
                # Extract manager contact details
                manager_email = None
                manager_phone = None
                if event.get('rideManagerContact'):
                    manager_email = event['rideManagerContact'].get('email')
                    manager_phone = event['rideManagerContact'].get('phone')
                
                # Prepare event details JSON
                event_details = {
                    "controlJudges": event.get('controlJudges', []),
                    "directions": event.get('directions'),
                    "mapLink": event.get('mapLink'),
                    "hasIntroRide": event.get('hasIntroRide', False),
                }
                
                # Prepare notes text combining relevant information
                notes_parts = []
                
                # Add manager contact details to notes
                if event.get('rideManagerContact'):
                    contact = event['rideManagerContact']
                    manager_contact = []
                    if contact.get('name'):
                        manager_contact.append(contact['name'])
                    if contact.get('email'):
                        manager_contact.append(contact['email'])
                    if contact.get('phone'):
                        manager_contact.append(contact['phone'])
                    
                    if manager_contact:
                        notes_parts.append(f"Manager contact: {', '.join(manager_contact)}")
                
                # Add control judges to notes
                if event.get('controlJudges'):
                    judge_notes = []
                    for judge in event['controlJudges']:
                        judge_notes.append(f"{judge.get('role', 'Judge')}: {judge.get('name', '')}")
                    if judge_notes:
                        notes_parts.append("Control judges: " + "; ".join(judge_notes))
                
                # Add directions to notes if available
                if event.get('directions'):
                    notes_parts.append(f"Directions: {event['directions']}")
                
                # Add any description to notes
                if event.get('description'):
                    notes_parts.append(event['description'])
                
                # Create event - USING CORRECT FIELD NAMES FROM DATABASE SCHEMA
                db_event = EventCreate(
                    name=event.get('rideName', "Unknown Event"),
                    description=event.get('description', ""),
                    location=event.get('location', ""),
                    date_start=date_start,  # Using date_start to match schema
                    date_end=date_end,      # Using date_end to match schema
                    organizer="AERC",
                    website=event.get('website', ""),
                    flyer_url="",  # AERC doesn't provide flyers in the calendar
                    region=f"AERC {event.get('region', '')}",
                    distances=distances,
                    source="aerc_scraper",
                    
                    # New fields
                    ride_manager=event.get('rideManager'),
                    manager_contact=event.get('rideManagerContact', {}).get('email', '') or 
                                   event.get('rideManagerContact', {}).get('phone', ''),
                    event_type="AERC Endurance",
                    event_details=event_details,
                    notes="\n\n".join(notes_parts) if notes_parts else None,
                    external_id=str(event.get('tag')) if event.get('tag') else None,
                )
                
                db_events.append(db_event)
            
            except Exception as e:
                logger.error(f"Error converting event to DB schema: {e}")
        
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

async def run_aerc_scraper(db: AsyncSession) -> Dict[str, Any]:
    """Run the AERC scraper."""
    scraper = AERCScraper()
    return await scraper.run(db)

if __name__ == "__main__":
    print("AERC Scraper must be run through the main scraping system")
