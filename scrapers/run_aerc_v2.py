#!/usr/bin/env python
"""
Run the improved AERC scraper (v2) with direct HTML parsing and per-chunk processing.
"""

import os
import logging
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from scrapers.aerc_scraper.config import get_settings
from scrapers.aerc_scraper.parser_v2.main_v2 import AERCScraperV2

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger("aerc_v2_runner")

async def main():
    """Run the improved AERC scraper."""
    logger.info("Starting improved AERC scraper (v2)")
    
    # Get settings
    settings = get_settings()
    
    # Set debug mode from environment variable
    debug_mode = os.environ.get("SCRAPER_DEBUG", "false").lower() == "true"
    if debug_mode:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled")
    
    # Create database engine and session
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            # Create and run the scraper
            scraper = AERCScraperV2(settings, session)
            results = await scraper.scrape()
            
            # Print summary
            logger.info("Scraper completed successfully")
            logger.info(f"Events processed: {results['events_processed']}")
            logger.info(f"Events stored: {results['events_stored']}")
            logger.info(f"Success rate: {results['success_rate']:.1f}%")
            
        except Exception as e:
            logger.error(f"Scraper failed: {str(e)}")
            raise

if __name__ == "__main__":
    asyncio.run(main()) 