#!/usr/bin/env python
"""
AERC Ride Calendar Scraper

This module provides a robust scraper for AERC (American Endurance Ride Conference)
ride calendar events. It extracts event information from the AERC website and
stores it in the application database.

Key features:
- HTML parsing with fallback options
- Progressive data processing with error isolation
- Comprehensive error handling and metrics tracking
- Optional chunking for processing large HTML pages
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Tuple
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
from scrapers.aerc_scraper.schema import validate_aerc_event

logger = logging.getLogger(__name__)

class AERCScraperV2:
    """
    AERC ride calendar scraper with progressive processing and robust error handling.

    This class implements a scraper for the AERC ride calendar that extracts event
    data using HTML parsing. It processes data in manageable chunks to maintain
    memory efficiency and provide better error isolation.
    """

    def __init__(
        self,
        settings: ScraperSettings,
        session: AsyncSession,
        metrics_dir: Optional[str] = None,
        use_chunking: bool = True,
    ):
        """
        Initialize the AERC scraper.

        Args:
            settings: Configuration settings for the scraper
            session: Database session for storing data
            metrics_dir: Directory for storing metrics data
            use_chunking: Whether to process HTML in chunks or all at once
        """
        self.settings = settings
        self.session = session
        self.debug_mode = settings.debug_mode
        self.use_chunking = use_chunking

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
        }

    async def scrape(self) -> Dict[str, Any]:
        """
        Run the AERC scraper and return results.

        This method fetches HTML from the AERC website, processes it either in
        chunks or as a whole, extracts event data, validates it against the schema,
        and stores it in the database.

        Returns:
            Dict with scraping results and metrics

        Raises:
            ScraperError: If the scraping process fails
        """
        try:
            # Fetch and preprocess calendar page
            html = await self.network.fetch_calendar()
            cleaned_html = self.cleaner.clean(html)

            if self.use_chunking:
                # Process with chunking
                return await self._process_with_chunking(cleaned_html)

            # Process entire HTML at once
            return await self._process_without_chunking(cleaned_html)

        except Exception as e:
            logger.error(f"Failed to run scraper: {str(e)}")
            raise ScraperError(f"Scraper failed: {str(e)}")

    async def _process_with_chunking(self, cleaned_html: str) -> Dict[str, Any]:
        """
        Process HTML content in chunks for better memory management and error isolation.

        Args:
            cleaned_html: Preprocessed HTML content

        Returns:
            Dict with scraping results and metrics
        """
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

    async def _process_without_chunking(self, cleaned_html: str) -> Dict[str, Any]:
        """
        Process the entire HTML content at once.

        Args:
            cleaned_html: Preprocessed HTML content

        Returns:
            Dict with scraping results and metrics
        """
        try:
            # Set metrics for single chunk processing
            self.process_metrics['total_chunks'] = 1

            # Extract events from HTML using direct parser
            raw_events = self.html_parser.parse_html(cleaned_html)
            self.process_metrics['html_parser_used'] += 1
            self.process_metrics['chunks_processed'] = 1

            if not raw_events:
                logger.warning("No events extracted from HTML")
                self._log_final_summary()
                return {
                    'events_processed': 0,
                    'events_stored': 0,
                    'chunks_processed': 1,
                    'success_rate': 0.0,
                }

            # Track events found
            self.process_metrics['events_processed'] = len(raw_events)
            logger.info(f"Extracted {len(raw_events)} events from HTML")

            # Validate and transform events
            valid_events, _ = await self._validate_events(raw_events)

            # After validation
            self.process_metrics['events_validated'] += len(valid_events)
            self.process_metrics['validation_errors'] += len(raw_events) - len(valid_events)

            # Store events in database
            storage_result = await self.db.store_events(valid_events)

            # After storage
            events_stored = storage_result.get('added', 0)
            events_updated = storage_result.get('updated', 0)
            events_failed = storage_result.get('skipped', 0) + storage_result.get('errors', 0)

            # Count both added and updated as "stored" for metrics
            self.process_metrics['events_stored'] += (events_stored + events_updated)

            if events_failed:
                self.process_metrics['storage_errors'] += events_failed

            # Log results
            logger.info(f"Validation results: {len(valid_events)} valid, {len(raw_events) - len(valid_events)} invalid")
            logger.info(f"Storage results: {events_stored} inserted, {events_updated} updated, {events_failed} failed")

            # Log final summary
            self._log_final_summary()

            # Return results
            return {
                'events_processed': self.process_metrics['events_processed'],
                'events_stored': self.process_metrics['events_stored'],
                'chunks_processed': 1,
                'success_rate': self._calculate_success_rate(),
            }

        except Exception as e:
            self.process_metrics['chunk_errors'] += 1
            logger.error(f"Error processing HTML: {str(e)}")
            raise

    async def _process_chunk(self, chunk: str, chunk_index: int) -> None:
        """
        Process a single HTML chunk: extract, validate, and store events.

        Args:
            chunk: HTML chunk to process
            chunk_index: Index of the chunk for logging
        """
        try:
            # Extract events from HTML using direct parser
            raw_events = self.html_parser.parse_html(chunk)
            self.process_metrics['html_parser_used'] += 1

            if not raw_events:
                logger.warning(f"No events extracted from chunk {chunk_index+1}")
                return

            # Track events found
            chunk_event_count = len(raw_events)
            self.process_metrics['events_processed'] += chunk_event_count

            logger.info(f"Extracted {chunk_event_count} events from chunk {chunk_index+1}")

            # Validate and transform events from this chunk
            valid_events, _ = await self._validate_events(raw_events)

            if len(valid_events) < chunk_event_count:
                logger.warning(f"{chunk_event_count - len(valid_events)} events failed validation in chunk {chunk_index+1}")

            if not valid_events:
                logger.warning(f"No valid events in chunk {chunk_index+1}")
                return

            # When debugging, log some details about the events
            if self.debug_mode:
                self._log_event_details(valid_events)

            # Store events in database
            await self._store_events(valid_events)

        except Exception as e:
            self.process_metrics['chunk_errors'] += 1
            logger.error(f"Error processing chunk {chunk_index+1}: {str(e)}")

    async def _validate_events(self, raw_events: List[Dict[str, Any]]) -> Tuple[List[EventCreate], Dict[str, int]]:
        """
        Validate and transform raw event data to EventCreate objects.

        Args:
            raw_events: List of raw event data dictionaries

        Returns:
            Tuple of (valid_events, validation_results)
        """
        valid_events = []
        validation_results = {
            'total': len(raw_events),
            'valid': 0,
            'invalid': 0
        }

        for raw_event in raw_events:
            try:
                # First validate against AERC schema
                aerc_event = validate_aerc_event(raw_event)

                # Then convert to EventCreate format for storage
                event_create = DataHandler.to_event_create(aerc_event)

                valid_events.append(event_create)
                self.process_metrics['events_validated'] += 1
                validation_results['valid'] += 1
            except Exception as e:
                self.process_metrics['validation_errors'] += 1
                validation_results['invalid'] += 1

                event_name = raw_event.get('rideName', 'Unknown event')
                logger.warning(f"Event validation failed for '{event_name}': {str(e)}")

        return valid_events, validation_results

    async def _store_events(self, valid_events: List[EventCreate]) -> Dict[str, int]:
        """
        Store validated events in the database.

        Args:
            valid_events: List of validated EventCreate objects

        Returns:
            Dict with storage results
        """
        try:
            # Store events in database
            storage_result = await self.db.store_events(valid_events)

            events_stored = storage_result.get('added', 0)
            events_updated = storage_result.get('updated', 0)

            # Count both added and updated as "stored" for metrics
            self.process_metrics['events_stored'] += (events_stored + events_updated)

            events_failed = storage_result.get('skipped', 0) + storage_result.get('errors', 0)

            logger.info(f"Storage results: {events_stored} inserted, {events_updated} updated, {events_failed} failed")

            if events_failed:
                self.process_metrics['storage_errors'] += events_failed

            return storage_result

        except Exception as e:
            self.process_metrics['storage_errors'] += len(valid_events)
            logger.error(f"Failed to store events: {str(e)}")
            raise

    def _log_event_details(self, events: List[EventCreate]) -> None:
        """
        Log details about events for debugging.

        Args:
            events: List of event objects to log
        """
        for i, event in enumerate(events[:5]):  # Log first 5 events only
            logger.debug(f"Event {i+1} details:")
            logger.debug(f"  - Name: {event.name}")
            logger.debug(f"  - Date: {event.date_start}")
            logger.debug(f"  - Location: {event.location}")
            logger.debug(f"  - Website: {getattr(event, 'website', None)}")
            logger.debug(f"  - Flyer: {getattr(event, 'flyer_url', None)}")
            logger.debug(f"  - Map: {getattr(event, 'map_link', None)}")
            logger.debug(f"  - Ride ID: {getattr(event, 'ride_id', None)}")

    def _log_final_summary(self) -> None:
        """Log the final summary of the scraping process."""
        logger.info("AERC Calendar Scraping Summary:")

        if self.use_chunking:
            logger.info(f"Chunks: {self.process_metrics['chunks_processed']}/{self.process_metrics['total_chunks']} processed")

        logger.info(f"Events: {self.process_metrics['events_processed']} found, {self.process_metrics['events_validated']} validated, {self.process_metrics['events_stored']} stored")
        logger.info(f"Success rate: {self._calculate_success_rate():.1f}%")
        logger.info(f"Errors: {self.process_metrics['chunk_errors']} chunk errors, {self.process_metrics['validation_errors']} validation errors, {self.process_metrics['storage_errors']} storage errors")

    def _calculate_success_rate(self) -> float:
        """
        Calculate the success rate of the scraping process.

        Returns:
            Percentage of events successfully stored
        """
        if self.process_metrics['events_processed'] == 0:
            return 0.0

        return (self.process_metrics['events_stored'] / self.process_metrics['events_processed']) * 100

async def run_scraper(
    settings: ScraperSettings,
    session: AsyncSession,
    use_chunking: bool = True
) -> Dict[str, Any]:
    """
    Run the AERC scraper with the specified settings.

    Args:
        settings: Scraper configuration settings
        session: Database session
        use_chunking: Whether to process HTML in chunks

    Returns:
        Dict with scraping results
    """
    scraper = AERCScraperV2(settings, session, use_chunking=use_chunking)
    return await scraper.scrape()

if __name__ == "__main__":
    # This allows running the scraper directly for testing
    import sys
    from scrapers.aerc_scraper.config import get_settings
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    import argparse

    # Configure argument parser
    parser = argparse.ArgumentParser(description="AERC Ride Calendar Scraper")
    parser.add_argument("--no-chunks", action="store_true", help="Process HTML without chunking")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

    async def main():
        """Run the scraper as a standalone script."""
        # Get settings
        settings = get_settings()
        if args.debug:
            settings.debug_mode = True

        # Create test database session
        engine = create_async_engine(settings.database_url)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as session:
            # Run scraper
            scraper = AERCScraperV2(
                settings,
                session,
                use_chunking=not args.no_chunks
            )
            results = await scraper.scrape()

            print(f"\nResults: {results}")

    # Run the main function
    asyncio.run(main())
