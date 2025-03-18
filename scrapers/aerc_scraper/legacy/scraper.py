#!/usr/bin/env python
"""
AERC Calendar Scraper with modular architecture and enhanced error handling.
"""

import logging
import asyncio
import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from ..base_scraper import BaseScraper
from .config import ScraperSettings, get_settings
from .network import NetworkHandler
from .html_cleaner import HtmlCleaner
from .gemini_client import GeminiClient
from .validator import DataValidator
from .converter import DataConverter
from .database import DatabaseHandler
from .cache import Cache
from .metrics import ScraperMetrics
from .exceptions import ScraperError
from app.logging_config import get_logger

# Use the properly configured logger from app.logging_config
logger = get_logger("scrapers.aerc_scraper")

class AERCScraper(BaseScraper):
    """Enhanced AERC calendar scraper with modular architecture."""
    
    def __init__(
        self,
        settings: Optional[ScraperSettings] = None,
        network_handler: Optional[NetworkHandler] = None,
        html_cleaner: Optional[HtmlCleaner] = None,
        gemini_client: Optional[GeminiClient] = None,
        data_validator: Optional[DataValidator] = None,
        data_converter: Optional[DataConverter] = None,
        db_handler: Optional[DatabaseHandler] = None,
        cache: Optional[Cache] = None,
        metrics: Optional[ScraperMetrics] = None,
        logger: Optional[logging.Logger] = None
    ):
        """Initialize scraper with dependencies."""
        super().__init__("AERC Calendar", logger or logging.getLogger(__name__))
        
        self.settings = settings or get_settings()
        self.network = network_handler or NetworkHandler(self.settings)
        self.html_cleaner = html_cleaner or HtmlCleaner()
        self.gemini_client = gemini_client or GeminiClient(self.settings)
        self.validator = data_validator or DataValidator()
        self.converter = data_converter or DataConverter()
        self.db_handler = db_handler or DatabaseHandler()
        self.cache = cache or Cache(self.settings)
        self.metrics = metrics or ScraperMetrics(start_time=datetime.now())
    
    def clean_data(self, raw_data: str) -> str:
        """Clean and preprocess raw data."""
        return self.html_cleaner.clean(raw_data)
    
    def validate_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate extracted data."""
        return self.validator.validate_events(data)
    
    def convert_to_db_schema(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert validated data to database schema."""
        return self.converter.convert_to_db_events(data)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get combined metrics from all components."""
        metrics = {
            **self.network.get_metrics(),
            **self.html_cleaner.get_metrics(),
            **self.gemini_client.get_metrics(),
            **self.validator.get_metrics(),
            **self.cache.get_metrics()
        }
        self.metrics.update(metrics)
        return self.metrics.to_dict()

    async def extract_season_ids(self) -> List[str]:
        """Extract season IDs from calendar page."""
        try:
            response_text = await self.network.make_request(self.settings.calendar_url)
            
            if not response_text:
                raise ScraperError("Failed to get calendar page")
            
            # Search for season inputs
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response_text, 'lxml')
            season_inputs = soup.select('input[name="season[]"]')
            season_ids = []
            
            for input_tag in season_inputs:
                season_id = input_tag.get('value')
                if season_id:
                    season_ids.append(season_id)
            
            return season_ids[:2]  # Get current and next year IDs
            
        except Exception as e:
            logger.exception(f"Error extracting season IDs: {e}")
            raise ScraperError(f"Failed to extract season IDs: {str(e)}")
    
    async def fetch_calendar_html(self, season_ids: List[str]) -> str:
        """Fetch calendar HTML using season IDs."""
        if not season_ids:
            raise ScraperError("No season IDs provided")

        cache_key = f"calendar_html_{'_'.join(season_ids)}"
        cached_html = self.cache.get(cache_key)
        if cached_html:
            logger.info("Using cached calendar HTML")
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

        response_text = await self.network.make_request(
            self.settings.base_url, 
            method="POST",
            data=data
        )
        
        if not response_text:
            raise ScraperError("Failed to fetch calendar HTML")
            
        try:
            import json
            json_data = json.loads(response_text)
            if 'html' in json_data:
                html_content = json_data['html']
                self.cache.set(cache_key, html_content)
                return html_content
            else:
                raise ScraperError("JSON response missing 'html' field")
        except json.JSONDecodeError:
            # If not JSON, might be direct HTML
            self.cache.set(cache_key, response_text)
            return response_text
    
    async def run(self, db: AsyncSession) -> Dict[str, Any]:
        """Run the scraper end-to-end."""
        try:
            # 1. Extract season IDs
            logger.info("Extracting season IDs")
            season_ids = await self.extract_season_ids()
            if not season_ids:
                raise ScraperError("Failed to extract season IDs")
            
            # 2. Fetch calendar HTML
            logger.info("Fetching calendar HTML")
            html = await self.fetch_calendar_html(season_ids)
            if not html:
                raise ScraperError("Failed to fetch calendar HTML")
            
            # 3. Clean HTML
            logger.info("Cleaning HTML")
            cleaned_html = self.clean_data(html)
            if not cleaned_html:
                raise ScraperError("Failed to clean HTML")
            
            # 4. Extract structured data using Gemini
            logger.info("Extracting structured data")
            chunks = self._chunk_html(cleaned_html)
            
            # Count approximate events in the HTML
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(cleaned_html, 'lxml')
            event_count = self.gemini_client._count_event_elements(soup)
            self.gemini_client.metrics['events_found'] = event_count
            
            # Log chunk information prominently
            logger.info("")
            logger.info("="*80)
            logger.info("                          SCRAPER PROCESSING STATS                       ")
            logger.info("="*80)
            logger.info(f"🔎 TOTAL EVENTS DETECTED IN HTML:        {event_count}")
            logger.info(f"📦 HTML SPLIT INTO CHUNKS:               {len(chunks)}")
            logger.info(f"📊 AVERAGE EVENTS PER CHUNK:             {event_count / len(chunks) if len(chunks) > 0 else 0:.1f}")
            logger.info("-"*80)
            logger.info("")
            
            all_events = []
            
            for idx, chunk in enumerate(chunks):
                logger.info(f"Processing chunk {idx+1}/{len(chunks)} (size: {len(chunk)} bytes)")
                events = await self.gemini_client.extract_data(chunk, idx)
                if events:
                    all_events.extend(events)
                    logger.info(f"✅ Chunk {idx+1}: Extracted {len(events)} events")
                else:
                    logger.warning(f"⚠️ Chunk {idx+1}: No events extracted!")
            
            if not all_events:
                raise ScraperError("Failed to extract structured data")
            
            # 5. Validate events
            logger.info(f"Validating {len(all_events)} events")
            valid_events = self.validate_data(all_events)
            if not valid_events:
                raise ScraperError("No valid events found")
            
            # Check for validation failures
            validation_failures = len(all_events) - len(valid_events)
            if validation_failures > 0:
                logger.warning(f"{validation_failures} events failed validation")
                
                # If we have a significant number of failures, log details for debugging
                if validation_failures > 5:
                    # Try to identify patterns in failed events
                    self._analyze_validation_failures(all_events, valid_events)
            
            # 6. Convert to database schema
            logger.info(f"Converting {len(valid_events)} events to database schema")
            db_events = self.convert_to_db_schema(valid_events)
            if not db_events:
                raise ScraperError("Failed to convert events to database schema")
            
            # 7. Store in database
            logger.info(f"Storing {len(db_events)} events in database")
            db_metrics = await self.db_handler.store_events(db_events, db)
            
            # 8. Verify event counts
            await self._verify_event_counts(db, all_events, valid_events, db_events, db_metrics)
            
            # Update metrics
            self.metrics.end_time = datetime.now()
            metrics_update = {
                **self.network.get_metrics(),
                **self.html_cleaner.get_metrics(),
                **self.gemini_client.get_metrics(),
                **self.validator.get_metrics(),
                **self.cache.get_metrics(),
                **db_metrics,
                'events_found': self.gemini_client.metrics['events_found'],
                'events_extracted': self.gemini_client.metrics['events_extracted'],
                'events_processed': self.gemini_client.metrics['events_processed'],
                'events_valid': len(valid_events),
                'events_added': db_metrics.get('added', 0),
                'events_updated': db_metrics.get('updated', 0),
                'events_skipped': db_metrics.get('skipped', 0),
                'events_with_issues_count': len(self.gemini_client.metrics['events_with_issues']),
                'validation_failures': validation_failures,
            }
            self.metrics.update(metrics_update)
            
            # Log metrics summary
            self.metrics.log_summary()
            self.metrics.save_to_file()
            
            return {
                "status": "success",
                "scraper": "aerc_calendar",
                "events_found": self.gemini_client.metrics['events_found'],
                "events_extracted": self.gemini_client.metrics['events_extracted'],
                "events_valid": len(valid_events),
                "events_added": db_metrics.get('added', 0),
                "events_updated": db_metrics.get('updated', 0),
                "events_skipped": db_metrics.get('skipped', 0),
                "validation_failures": validation_failures,
                "success_rate": (len(valid_events) / len(all_events) * 100) if len(all_events) > 0 else 0
            }
            
        except Exception as e:
            logger.exception(f"Error running AERC scraper: {e}")
            self.metrics.end_time = datetime.now()
            self.metrics.log_summary()
            self.metrics.save_to_file()
            return {"status": "error", "message": str(e)}
    
    def _chunk_html(self, html: str) -> List[str]:
        """Split HTML into manageable chunks for Gemini processing."""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html, 'lxml')
        rows = soup.find_all('div', class_='calendarRow')
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        for row in rows:
            row_html = str(row)
            row_size = len(row_html)
            
            if current_size + row_size > self.settings.initial_chunk_size:
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

    def _analyze_validation_failures(self, all_events, valid_events):
        """Analyze validation failures to identify patterns."""
        # Create sets of event identifiers for comparison
        valid_event_names = {event.get('name', '') for event in valid_events}
        
        # Find events that failed validation
        failed_events = [event for event in all_events 
                        if event.get('name', '') not in valid_event_names]
        
        logger.info(f"Analyzing {len(failed_events)} validation failures")
        
        # Check for common issues
        missing_fields = {'name': 0, 'date_start': 0, 'location': 0}
        invalid_dates = 0
        other_issues = 0
        
        for event in failed_events:
            # Check for missing required fields
            for field in ['name', 'date_start', 'location']:
                if field not in event or not event[field]:
                    missing_fields[field] += 1
            
            # Check for date format issues
            if 'date_start' in event and event['date_start']:
                try:
                    if isinstance(event['date_start'], str):
                        datetime.strptime(event['date_start'], '%Y-%m-%d')
                except ValueError:
                    invalid_dates += 1
            
            # If none of the above, count as other issue
            if all(field in event and event[field] for field in ['name', 'date_start', 'location']) and invalid_dates == 0:
                other_issues += 1
        
        # Log findings
        logger.info(f"Validation failure analysis:")
        logger.info(f"  - Missing name field: {missing_fields['name']}")
        logger.info(f"  - Missing date_start field: {missing_fields['date_start']}")
        logger.info(f"  - Missing location field: {missing_fields['location']}")
        logger.info(f"  - Invalid date formats: {invalid_dates}")
        logger.info(f"  - Other validation issues: {other_issues}")
        
        # Log sample failed events for debugging
        if failed_events:
            sample_size = min(3, len(failed_events))
            logger.debug(f"Sample of failed events:")
            for i in range(sample_size):
                logger.debug(f"Failed event {i+1}: {json.dumps(failed_events[i], indent=2, default=str)}")

    async def _verify_event_counts(self, db, all_events, valid_events, db_events, db_metrics):
        """Verify event counts against database results."""
        # Calculate expected results
        events_found = self.gemini_client.metrics['events_found']
        events_extracted = self.gemini_client.metrics['events_extracted']
        events_valid = len(valid_events)
        events_db_processed = len(db_events)
        events_added = db_metrics.get('added', 0)
        events_updated = db_metrics.get('updated', 0)
        events_skipped = db_metrics.get('skipped', 0)
        
        # Check database count for AERC events specifically
        db_count = await self._get_db_event_count(db)
        
        # Log verification results with more visibility
        logger.info("")
        logger.info("="*80)
        logger.info("                          EVENT COUNT VERIFICATION                          ")
        logger.info("="*80)
        logger.info(f"🔍 EVENTS FOUND IN HTML (ESTIMATED):      {events_found}")
        logger.info(f"📊 EVENTS EXTRACTED BY GEMINI:           {events_extracted}")
        logger.info(f"✅ EVENTS AFTER VALIDATION:              {events_valid}")
        logger.info(f"🏗️  EVENTS PREPARED FOR DATABASE:         {events_db_processed}")
        logger.info(f"➕ EVENTS ADDED TO DATABASE:             {events_added}")
        logger.info(f"🔄 EVENTS UPDATED IN DATABASE:           {events_updated}")
        logger.info(f"⏭️  EVENTS SKIPPED (DUPLICATES):          {events_skipped}")
        logger.info(f"💾 TOTAL AERC EVENTS IN DATABASE:        {db_count}")
        
        # Add cancelled events count if available
        cancelled_count = sum(1 for event in db_events if getattr(event, 'is_canceled', False))
        if cancelled_count > 0:
            logger.info(f"❌ CANCELLED EVENTS DETECTED:           {cancelled_count}")
            
        logger.info("-"*80)
        
        # Calculate discrepancies
        extraction_loss = events_found - events_extracted if events_found > 0 else 0
        validation_loss = events_extracted - events_valid
        db_processing_loss = events_valid - events_db_processed
        db_storage_discrepancy = events_db_processed - (events_added + events_updated + events_skipped)
        
        # Log any significant discrepancies
        if extraction_loss > 0 and events_found > 0:
            percent_loss = (extraction_loss / events_found) * 100
            logger.warning(f"Lost {extraction_loss} events during extraction ({percent_loss:.2f}%)")
            
            # Add more detailed analysis if loss is significant
            if percent_loss > 10:
                logger.error(f"Significant extraction loss: {percent_loss:.2f}%! Check chunking and extraction logic.")
        
        if validation_loss > 0 and events_extracted > 0:
            percent_loss = (validation_loss / events_extracted) * 100
            logger.warning(f"Lost {validation_loss} events during validation ({percent_loss:.2f}%)")
            
            # Add more detailed analysis if loss is significant
            if percent_loss > 10:
                logger.error(f"Significant validation loss: {percent_loss:.2f}%! Check validation requirements.")
        
        if db_processing_loss > 0 and events_valid > 0:
            percent_loss = (db_processing_loss / events_valid) * 100
            logger.warning(f"Lost {db_processing_loss} events during database preparation ({percent_loss:.2f}%)")
        
        if db_storage_discrepancy != 0:
            logger.warning(f"Database storage discrepancy: {db_storage_discrepancy} events unaccounted for")
        
        # If we're in development and expected extraction to match database (ignoring updates/skips)
        is_dev_env = os.environ.get('ENVIRONMENT', '').lower() == 'development'
        if is_dev_env:
            # In development, we expect all extracted events to be in the database
            expected_db_total = events_added + events_updated
            
            if db_count < expected_db_total:
                logger.error(f"Database count ({db_count}) is less than expected ({expected_db_total})")
                logger.error(f"Missing events: {expected_db_total - db_count}")
            
            if events_extracted > 0:
                percent_captured = ((events_added + events_updated) / events_extracted) * 100
                logger.info(f"Captured {percent_captured:.2f}% of extracted events in the database")
                
                if percent_captured < 90:
                    logger.warning(f"Low capture rate: {percent_captured:.2f}%. Check validation and database insertion.")
        
        # Add a summary line for metrics
        logger.info("="*80)
        # Add this info to the metrics
        self.metrics.update({
            'verification': {
                'events_found': events_found,
                'events_extracted': events_extracted,
                'events_valid': events_valid,
                'events_db_processed': events_db_processed,
                'events_added': events_added,
                'events_updated': events_updated,
                'events_skipped': events_skipped,
                'total_db_count': db_count
            }
        })

    async def _get_db_event_count(self, db: AsyncSession) -> int:
        """Get the count of AERC events in the database."""
        try:
            # Use SQLAlchemy properly with text() - count only AERC source events
            result = await db.execute(text("SELECT COUNT(*) FROM events WHERE source = 'AERC'"))
            count = result.scalar()
            return count or 0
        except Exception as e:
            logger.error(f"Error counting database events: {e}")
            return 0

async def run_aerc_scraper(db: AsyncSession) -> Dict[str, Any]:
    """Run the AERC scraper."""
    scraper = AERCScraper()
    return await scraper.run(db)
