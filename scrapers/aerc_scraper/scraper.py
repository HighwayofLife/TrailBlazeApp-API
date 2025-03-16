#!/usr/bin/env python
"""
AERC Calendar Scraper with modular architecture and enhanced error handling.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

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

logger = logging.getLogger(__name__)

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
            all_events = []
            
            for idx, chunk in enumerate(chunks):
                events = await self.gemini_client.extract_data(chunk, idx)
                if events:
                    all_events.extend(events)
            
            if not all_events:
                raise ScraperError("Failed to extract structured data")
            
            # 5. Validate events
            logger.info("Validating events")
            valid_events = self.validate_data(all_events)
            if not valid_events:
                raise ScraperError("No valid events found")
            
            # 6. Convert to database schema
            logger.info("Converting to database schema")
            db_events = self.convert_to_db_schema(valid_events)
            if not db_events:
                raise ScraperError("Failed to convert events to database schema")
            
            # 7. Store in database
            logger.info("Storing events in database")
            db_metrics = await self.db_handler.store_events(db_events, db)
            
            # Update metrics
            self.metrics.end_time = datetime.now()
            self.metrics.update({
                **self.network.get_metrics(),
                **self.html_cleaner.get_metrics(),
                **self.gemini_client.get_metrics(),
                **self.validator.get_metrics(),
                **self.cache.get_metrics(),
                **db_metrics
            })
            
            # Log metrics summary
            self.metrics.log_summary()
            self.metrics.save_to_file()
            
            return {
                "status": "success",
                "scraper": "aerc_calendar",
                "events_found": self.metrics.events_found,
                "events_valid": self.metrics.events_valid,
                "events_added": db_metrics['added'],
                "events_updated": db_metrics['updated'],
                "events_skipped": db_metrics['skipped'],
                "validation_errors": self.metrics.validation_errors,
                "success_rate": (self.metrics.events_valid / self.metrics.events_found * 100) if self.metrics.events_found > 0 else 0
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

async def run_aerc_scraper(db: AsyncSession) -> Dict[str, Any]:
    """Run the AERC scraper."""
    scraper = AERCScraper()
    return await scraper.run(db)
