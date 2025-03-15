#!/usr/bin/env python
"""
Script to run data scrapers manually.
"""
import asyncio
import sys
import os
from typing import List

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.ext.asyncio import AsyncSession
from app.database import async_session
from app.services.scraper_service import run_scraper
from app.logging_config import get_logger, configure_logging
import logging.config

# Configure logging
logging.config.dictConfig(configure_logging())
logger = get_logger("scrapers.run")


async def run_all_scrapers() -> None:
    """Run all available scrapers."""
    scraper_ids = ["pner", "aerc", "facebook"]
    
    async with async_session() as db:
        for scraper_id in scraper_ids:
            logger.info(f"Running scraper: {scraper_id}")
            result = await run_scraper(scraper_id, db)
            logger.info(f"Scraper result: {result}")


async def run_specific_scrapers(scraper_ids: List[str]) -> None:
    """Run specific scrapers by ID."""
    async with async_session() as db:
        for scraper_id in scraper_ids:
            logger.info(f"Running scraper: {scraper_id}")
            result = await run_scraper(scraper_id, db)
            logger.info(f"Scraper result: {result}")


async def main() -> None:
    """Main entry point."""
    args = sys.argv[1:]
    
    if not args:
        # No arguments, run all scrapers
        await run_all_scrapers()
    else:
        # Run specified scrapers
        await run_specific_scrapers(args)


if __name__ == "__main__":
    logger.info("Starting scrapers...")
    asyncio.run(main())
    logger.info("Scrapers completed")
