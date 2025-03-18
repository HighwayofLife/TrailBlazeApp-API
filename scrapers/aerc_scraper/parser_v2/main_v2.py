#!/usr/bin/env python
"""
AERC scraper main module with improved chunk-by-chunk processing.
This version processes and stores data after each chunk is processed,
providing better visibility and error isolation.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.event import EventCreate
from scrapers.config import ScraperSettings
from scrapers.database import DatabaseHandler
from scrapers.metrics import MetricsCollector
from scrapers.exceptions import ScraperError

from scrapers.aerc_scraper.network import NetworkHandler
from scrapers.aerc_scraper.html_cleaner import HtmlCleaner
from scrapers.aerc_scraper.chunking import HtmlChunker
from scrapers.aerc_scraper.data_handler import DataHandler
from scrapers.aerc_scraper.parser_v2.html_parser import HTMLParser
from scrapers.aerc_scraper.gemini_api import GeminiAPI

logger = logging.getLogger(__name__)

class AERCScraperV2:
    """Improved AERC ride calendar scraper implementation with per-chunk processing."""
    
    def __init__(
        self,
        settings: ScraperSettings,
        session: AsyncSession,
        metrics_dir: Optional[str] = None
    ):
        """Initialize improved AERC scraper."""
        self.settings = settings
        self.session = session
        self.debug_mode = settings.debug_mode
        
        # Initialize components
        self.db = DatabaseHandler()
        self.metrics = MetricsCollector(
            source="AERC",
            metrics_dir=metrics_dir or "logs/metrics"
        )
        
        self.network = NetworkHandler(settings)
        self.cleaner = HtmlCleaner()
        self.chunker = HtmlChunker(settings)
        
        # Initialize the HTML parser
        self.html_parser = HTMLParser(debug_mode=settings.debug_mode)
        
        # Optionally initialize Gemini as fallback
        self.use_gemini_fallback = settings.use_ai_extraction
        if self.use_gemini_fallback:
            self.gemini = GeminiAPI(settings.gemini_api_key)
        else:
            self.gemini = None
        
        # Tracking metrics
        self.process_metrics = {
            'total_chunks': 0,
            'chunks_processed': 0,
            'total_events': 0,
            'events_processed': 0,
            'events_validated': 0,
            'events_stored': 0,
            'chunk_errors': 0,
            'validation_errors': 0,
            'storage_errors': 0,
            'html_parser_used': 0,
            'gemini_fallback_used': 0,
        }
    
    async def scrape(self) -> Dict[str, Any]:
        """Run the scraper with per-chunk processing and return results."""
        try:
            # Fetch and preprocess calendar page
            html = await self.network.fetch_calendar()
            cleaned_html = self.cleaner.clean(html)
            
            # Split into manageable chunks
            chunks = self.chunker.create_chunks(cleaned_html)
            self.process_metrics['total_chunks'] = len(chunks)
            
            logger.info(f"Processing {len(chunks)} HTML chunks")
            
            # Process each chunk individually
            for i, chunk in enumerate(chunks):
                try:
                    logger.info(f"Processing chunk {i+1}/{len(chunks)}")
                    
                    # Process this chunk
                    await self._process_chunk(chunk, chunk_index=i)
                    
                    self.process_metrics['chunks_processed'] += 1
                    
                    # Log progress
                    progress = (i + 1) / len(chunks) * 100
                    logger.info(f"Progress: {progress:.1f}% ({i+1}/{len(chunks)} chunks)")
                    logger.info(f"Events found so far: {self.process_metrics['events_processed']}")
                    logger.info(f"Events stored so far: {self.process_metrics['events_stored']}")
                    
                except Exception as e:
                    self.process_metrics['chunk_errors'] += 1
                    logger.error(f"Error processing chunk {i+1}: {str(e)}")
                    continue
            
            # Log final summary
            self._log_final_summary()
            
            # Return results
            return {
                'events_processed': self.process_metrics['events_processed'],
                'events_stored': self.process_metrics['events_stored'],
                'chunks_processed': self.process_metrics['chunks_processed'],
                'success_rate': self._calculate_success_rate(),
            }
            
        except Exception as e:
            logger.error(f"Failed to run scraper: {str(e)}")
            raise ScraperError(f"Scraper failed: {str(e)}")
    
    async def _process_chunk(self, chunk: str, chunk_index: int) -> None:
        """Process a single HTML chunk: extract, validate, and store events."""
        try:
            # Extract events from HTML using direct parser
            raw_events = self.html_parser.parse_html(chunk)
            self.process_metrics['html_parser_used'] += 1
            
            # If no events found and Gemini fallback is enabled, try Gemini
            if not raw_events and self.use_gemini_fallback and self.gemini:
                logger.info(f"No events found with HTML parser in chunk {chunk_index+1}, trying Gemini fallback")
                try:
                    raw_events = await self.gemini.extract_events(chunk)
                    self.process_metrics['gemini_fallback_used'] += 1
                except Exception as e:
                    logger.error(f"Gemini fallback failed for chunk {chunk_index+1}: {str(e)}")
            
            if not raw_events:
                logger.warning(f"No events extracted from chunk {chunk_index+1}")
                return
            
            # Track events found
            chunk_event_count = len(raw_events)
            self.process_metrics['events_processed'] += chunk_event_count
            
            logger.info(f"Extracted {chunk_event_count} events from chunk {chunk_index+1}")
            
            # Validate and transform events from this chunk
            valid_events = []
            for raw_event in raw_events:
                try:
                    # First transform to AERCEvent model
                    aerc_event = DataHandler.transform_and_validate(raw_event)
                    
                    # Then convert to EventCreate format for storage
                    event_create = DataHandler.to_event_create(aerc_event)
                    
                    valid_events.append(event_create)
                    self.process_metrics['events_validated'] += 1
                except Exception as e:
                    self.process_metrics['validation_errors'] += 1
                    logger.warning(f"Event validation failed in chunk {chunk_index+1}: {str(e)}")
            
            if len(valid_events) < chunk_event_count:
                logger.warning(f"{chunk_event_count - len(valid_events)} events failed validation in chunk {chunk_index+1}")
            
            if not valid_events:
                logger.warning(f"No valid events in chunk {chunk_index+1}")
                return
            
            # When debugging, log some details about the events
            if self.debug_mode:
                self._log_event_details(valid_events)
            
            # Store events in database
            try:
                storage_result = await self.db.store_events(valid_events)
                
                events_stored = storage_result.get('added', 0)
                events_updated = storage_result.get('updated', 0)
                
                # Count both added and updated as "stored" for metrics
                self.process_metrics['events_stored'] += (events_stored + events_updated)
                
                events_failed = storage_result.get('skipped', 0)
                
                logger.info(f"Chunk {chunk_index+1} storage results: {events_stored} inserted, {events_updated} updated, {events_failed} failed")
                
                if events_failed:
                    self.process_metrics['storage_errors'] += events_failed
                    
            except Exception as e:
                self.process_metrics['storage_errors'] += len(valid_events)
                logger.error(f"Failed to store events from chunk {chunk_index+1}: {str(e)}")
        except Exception as e:
            self.process_metrics['chunk_errors'] += 1
            logger.error(f"Error processing chunk {chunk_index+1}: {str(e)}")
    
    def _log_event_details(self, events: List[EventCreate]) -> None:
        """Log details about events for debugging."""
        for i, event in enumerate(events[:5]):  # Log first 5 events only
            logger.debug(f"Event {i+1} details:")
            logger.debug(f"  - Name: {event.name}")
            logger.debug(f"  - Date: {event.date_start}")
            logger.debug(f"  - Location: {event.location}")
            
            # Use the correct attribute names for AERCEvent objects
            website = getattr(event, 'website_url', getattr(event, 'website', None))
            flyer = getattr(event, 'registration_url', getattr(event, 'flyer_url', None))
            
            logger.debug(f"  - Website: {website}")
            logger.debug(f"  - Flyer: {flyer}")
            logger.debug(f"  - Map: {getattr(event, 'map_link', None)}")
    
    def _log_final_summary(self) -> None:
        """Log the final summary of the scraping process."""
        logger.info("AERC Calendar Scraping Summary:")
        logger.info(f"Chunks: {self.process_metrics['chunks_processed']}/{self.process_metrics['total_chunks']} processed")
        logger.info(f"Events: {self.process_metrics['events_processed']} found, {self.process_metrics['events_validated']} validated, {self.process_metrics['events_stored']} stored")
        logger.info(f"Success rate: {self._calculate_success_rate():.1f}%")
        logger.info(f"Errors: {self.process_metrics['chunk_errors']} chunk errors, {self.process_metrics['validation_errors']} validation errors, {self.process_metrics['storage_errors']} storage errors")
        
        if self.use_gemini_fallback:
            logger.info(f"Parser usage: {self.process_metrics['html_parser_used']} HTML parser, {self.process_metrics['gemini_fallback_used']} Gemini fallback")
    
    def _calculate_success_rate(self) -> float:
        """Calculate the success rate of the scraping process."""
        if self.process_metrics['events_processed'] == 0:
            return 0.0
        
        return (self.process_metrics['events_stored'] / self.process_metrics['events_processed']) * 100

async def run_scraper(settings: ScraperSettings, session: AsyncSession) -> Dict[str, Any]:
    """Run the AERC scraper."""
    scraper = AERCScraperV2(settings, session)
    return await scraper.scrape()

if __name__ == "__main__":
    # This allows running the scraper directly for testing
    import sys
    from scrapers.aerc_scraper.config import get_settings
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    
    async def main():
        """Run the scraper as a standalone script."""
        # Get settings
        settings = get_settings()
        
        # Create test database session
        engine = create_async_engine(settings.database_url)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as session:
            # Run scraper
            scraper = AERCScraperV2(settings, session)
            results = await scraper.scrape()
            
            print(f"\nResults: {results}")
    
    # Run the main function
    asyncio.run(main()) 