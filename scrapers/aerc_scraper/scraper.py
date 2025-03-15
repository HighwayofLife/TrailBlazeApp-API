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

class AERCScraper:
    """Scraper for the AERC calendar website."""
    
    BASE_URL = "https://aerc.org/wp-admin/admin-ajax.php"
    CALENDAR_URL = "https://aerc.org/calendar"
    CACHE_DIR = "cache"
    MAX_RETRIES = 3
    RETRY_DELAY = 5  # seconds
    REQUEST_TIMEOUT = 30  # seconds
    
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
        # Initialize metrics
        self.metrics = ScraperMetrics(start_time=datetime.now())
    
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
            
            # Debug: Check what elements are actually in the HTML
            logger.info(f"HTML structure - tags found: {[tag.name for tag in soup.find_all()][:20]}")
            
            # Remove unnecessary elements
            for tag in ['script', 'style', 'header', 'footer', 'nav']:
                for element in soup.find_all(tag):
                    element.decompose()
            
            # Debug: Check for any div elements with class attributes
            div_classes = set()
            for div in soup.find_all('div'):
                if div.has_attr('class'):
                    div_classes.update(div['class'])
            logger.info(f"Div classes found: {list(div_classes)[:20]}")
            
            # Focus on calendar rows
            calendar_rows = soup.find_all('div', class_='calendarRow')
            logger.info(f"Found {len(calendar_rows)} calendar rows")
            
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
        # Prepare the prompt for Gemini
        prompt = f"""
        Analyze this AERC endurance ride calendar HTML and extract structured data following these rules:
        
        Return valid JSON matching this schema:
        ```json
        {AERC_EVENT_SCHEMA}
        ```
        
        Return the extracted JSON array with no explanations, only the valid JSON.

        HTML to process:
        {html[:60000]}  # Truncated to stay within token limits
        """
        
        try:
            # First attempt with gemini-2.0-flash-lite
            response = await asyncio.to_thread(
                lambda: self.model.generate_content(prompt).text
            )
            
            # Try to parse the JSON
            data = self.parse_gemini_output(response)
            if data:
                self._save_cache(cache_key, data)
                return data
            
            # If failed, retry with gemini-2.0-flash
            logger.info("Retrying with gemini-2.0-flash model")
            self.metrics.gemini_calls += 1
            backup_model = genai.GenerativeModel('gemini-2.0-flash', generation_config={"temperature": 0.3})
            response = await asyncio.to_thread(
                lambda: backup_model.generate_content(prompt).text
            )
            
            data = self.parse_gemini_output(response)
            if data:
                self._save_cache(cache_key, data)
                return data
            
            # If still failed, use fallback regex parsing
            logger.warning("Gemini extraction failed, falling back to regex parsing")
            self.metrics.gemini_errors += 2  # Count both attempts
            self.metrics.fallback_used = True
            return self.fallback_extraction(html)
            
        except Exception as e:
            logger.exception(f"Error extracting structured data: {e}")
            self.metrics.gemini_errors += 1
            self.metrics.fallback_used = True
            return self.fallback_extraction(html)
    
    def parse_gemini_output(self, text: str) -> List[Dict[str, Any]]:
        """Parse Gemini output to extract JSON data."""
        try:
            # Look for JSON array in the text
            json_match = re.search(r'\[\s*{[\s\S]*}\s*\]', text)
            if json_match:
                json_str = json_match.group(0)
                data = json.loads(json_str)
                
                # Validate the extracted data
                if isinstance(data, list) and len(data) > 0:
                    valid_data = self.validate_events(data)
                    logger.info(f"Successfully extracted {len(valid_data)} events")
                    return valid_data
            
            return []
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from Gemini output: {e}")
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
                    
                    # Extract region
                    region_elem = row.find('div', class_='region')
                    if region_elem:
                        event['region'] = region_elem.text.strip()
                    
                    # Extract ride name
                    ride_name_elem = row.find('span', class_='rideName')
                    if ride_name_elem:
                        event['rideName'] = ride_name_elem.text.strip()
                    
                    # Extract date
                    date_elem = row.find('div', class_='bold')
                    if date_elem:
                        date_str = date_elem.text.strip()
                        date_match = re.search(r'\b(\d{2}/\d{2}/\d{4})\b', date_str)
                        if date_match:
                            date_str = date_match.group(1)
                            date_obj = datetime.strptime(date_str, '%m/%d/%Y')
                            event['date'] = date_obj.strftime('%Y-%m-%d')
                    
                    # Extract location
                    location_elem = row.find('a', href=lambda href: href and 'maps.google.com' in href)
                    if location_elem:
                        event['location'] = location_elem.text.strip()
                        event['mapLink'] = location_elem['href']
                        
                        # Extract coordinates from Google Maps link
                        coords_match = re.search(r'destination=([-\d.]+),([-\d.]+)', location_elem['href'])
                        if coords_match:
                            event['coordinates'] = {
                                'lat': float(coords_match.group(1)),
                                'lng': float(coords_match.group(2))
                            }
                    
                    # Extract distances (simplified)
                    distances = []
                    distance_table = row.find('table')
                    if distance_table:
                        for row in distance_table.find_all('tr'):
                            cells = row.find_all('td')
                            if len(cells) >= 2:
                                distance = cells[0].text.strip()
                                if distance.isdigit() or re.match(r'^(\d+)\s*', distance):
                                    distances.append({
                                        "distance": distance,
                                        "date": event.get('date', ''),
                                        "startTime": cells[1].text.strip() if len(cells) > 1 else ""
                                    })
                    
                    event['distances'] = distances
                    
                    # Extract ride manager
                    manager_section = row.find('div', string=lambda s: s and 'Ride Manager' in s)
                    if manager_section and manager_section.find_next_sibling('div'):
                        manager_info = manager_section.find_next_sibling('div').text.strip()
                        event['rideManager'] = manager_info
                        event['rideManagerContact'] = {"name": manager_info}
                        
                        # Try to extract email
                        email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', manager_info)
                        if email_match:
                            event['rideManagerContact']['email'] = email_match.group(0)
                        
                        # Try to extract phone
                        phone_match = re.search(r'(\(\d{3}\)\s*\d{3}-\d{4}|\d{3}-\d{3}-\d{4})', manager_info)
                        if phone_match:
                            event['rideManagerContact']['phone'] = phone_match.group(0)
                    
                    # Extract control judges
                    event['controlJudges'] = []
                    judge_section = row.find('div', string=lambda s: s and 'Control Judge' in s)
                    if judge_section and judge_section.find_next_sibling('div'):
                        judge_info = judge_section.find_next_sibling('div').text.strip()
                        event['controlJudges'].append({
                            "role": "Head Control Judge",
                            "name": judge_info
                        })
                    
                    # Set defaults for required fields
                    event['hasIntroRide'] = 'Intro' in str(row) or 'Intro Ride' in str(row)
                    event['tag'] = hash(event.get('rideName', '') + event.get('date', '')) % 10000
                    
                    if event.get('rideName') and event.get('date') and event.get('distances'):
                        events.append(event)
                
                except Exception as e:
                    logger.error(f"Error processing row in fallback extraction: {e}")
            
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
        
        for event in db_events:
            try:
                # Check if event exists (by name and date)
                existing_events = await get_events(
                    db,
                    date_from=event.date_start.isoformat() if event.date_start else None,  # Updated to date_start
                    date_to=event.date_start.isoformat() if event.date_start else None     # Updated to date_start
                )
                
                exists = False
                for existing in existing_events:
                    if existing.name == event.name and existing.location == event.location:
                        exists = True
                        break
                
                if not exists:
                    await create_event(db, event)
                    added_count += 1
                else:
                    updated_count += 1
                    logger.info(f"Event already exists: {event.name}")
            
            except Exception as e:
                logger.error(f"Error storing event in database: {e}")
        
        self.metrics.events_added = added_count
        self.metrics.events_updated = updated_count
        return {"added": added_count, "updated": updated_count}
    
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
            "events_found": self.metrics.events_found,
            "events_valid": self.metrics.events_valid,
            "events_added": self.metrics.events_added,
            "events_updated": self.metrics.events_updated,
            "success_rate": (self.metrics.events_valid / self.metrics.events_found * 100) if self.metrics.events_found > 0 else 0
        }

async def run_aerc_scraper(db: AsyncSession) -> Dict[str, Any]:
    """Run the AERC scraper."""
    scraper = AERCScraper()
    return await scraper.run(db)

if __name__ == "__main__":
    print("AERC Scraper must be run through the main scraping system")
