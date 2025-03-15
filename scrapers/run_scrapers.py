#!/usr/bin/env python
"""
Script to run data scrapers manually.
"""
import asyncio
import sys
import os
from typing import List, Dict, Any
from datetime import datetime, timedelta

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import async_session
from app.services.scraper_service import run_scraper
from app.logging_config import get_logger, configure_logging
import logging.config

# Configure logging
logging.config.dictConfig(configure_logging())
logger = get_logger("scrapers.run")

async def validate_database_connection(db: AsyncSession) -> bool:
    """Validate database connection and schema."""
    try:
        # Test database connection
        await db.execute(text("SELECT 1"))
        
        # Check if events table exists and has the expected columns
        result = await db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'events'
        """))
        columns = [row[0] for row in result]
        
        required_columns = [
            'name', 'location', 'date_start', 'date_end', 
            'organizer', 'event_type', 'source'
        ]
        
        missing_columns = [col for col in required_columns if col not in columns]
        if missing_columns:
            logger.error(f"Missing required columns in events table: {missing_columns}")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"Database validation failed: {e}")
        return False

async def get_scraping_stats(db: AsyncSession, days: int = 7) -> Dict[str, Any]:
    """Get statistics about recent scraping activity."""
    try:
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Get event counts by source
        result = await db.execute(text("""
            SELECT source, COUNT(*) as count
            FROM events
            WHERE created_at >= :cutoff_date
            GROUP BY source
        """), {"cutoff_date": cutoff_date})
        
        stats = {
            "period_days": days,
            "events_by_source": dict(result.fetchall()),
            "total_events": sum(dict(result.fetchall()).values())
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get scraping stats: {e}")
        return {}

async def run_all_scrapers() -> None:
    """Run all available scrapers."""
    scraper_ids = ["aerc_calendar"]  # Add more scrapers as they're implemented
    
    async with async_session() as db:
        # Validate database first
        if not await validate_database_connection(db):
            logger.error("Database validation failed. Aborting scraper run.")
            return
            
        # Get initial stats
        initial_stats = await get_scraping_stats(db, days=1)
        
        # Run scrapers
        results = []
        for scraper_id in scraper_ids:
            try:
                logger.info(f"Running scraper: {scraper_id}")
                result = await run_scraper(scraper_id, db)
                results.append({"scraper": scraper_id, "result": result})
                logger.info(f"Scraper result: {result}")
            except Exception as e:
                logger.error(f"Error running scraper {scraper_id}: {e}")
                results.append({
                    "scraper": scraper_id,
                    "result": {"status": "error", "message": str(e)}
                })
        
        # Get final stats
        final_stats = await get_scraping_stats(db, days=1)
        
        # Calculate and log summary
        logger.info("=== Scraping Run Summary ===")
        logger.info(f"Scrapers run: {len(scraper_ids)}")
        logger.info(f"Successful runs: {sum(1 for r in results if r['result'].get('status') == 'success')}")
        logger.info(f"Failed runs: {sum(1 for r in results if r['result'].get('status') == 'error')}")
        logger.info("Event counts:")
        for scraper_id in scraper_ids:
            new_count = final_stats.get('events_by_source', {}).get(scraper_id, 0) - \
                       initial_stats.get('events_by_source', {}).get(scraper_id, 0)
            logger.info(f"  {scraper_id}: {new_count} new events")

async def run_specific_scrapers(scraper_ids: List[str]) -> None:
    """Run specific scrapers by ID."""
    async with async_session() as db:
        # Validate database first
        if not await validate_database_connection(db):
            logger.error("Database validation failed. Aborting scraper run.")
            return
            
        initial_stats = await get_scraping_stats(db, days=1)
        
        for scraper_id in scraper_ids:
            try:
                logger.info(f"Running scraper: {scraper_id}")
                result = await run_scraper(scraper_id, db)
                logger.info(f"Scraper result: {result}")
            except Exception as e:
                logger.error(f"Error running scraper {scraper_id}: {e}")
        
        final_stats = await get_scraping_stats(db, days=1)
        
        # Log summary for specific scrapers
        logger.info("=== Scraping Run Summary ===")
        for scraper_id in scraper_ids:
            new_count = final_stats.get('events_by_source', {}).get(scraper_id, 0) - \
                       initial_stats.get('events_by_source', {}).get(scraper_id, 0)
            logger.info(f"{scraper_id}: {new_count} new events")

async def main() -> None:
    """Main entry point."""
    try:
        args = sys.argv[1:]
        
        if not args:
            # No arguments, run all scrapers
            await run_all_scrapers()
        else:
            # Run specified scrapers
            await run_specific_scrapers(args)
            
    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error in main: {e}")
        sys.exit(1)

if __name__ == "__main__":
    logger.info("Starting scrapers...")
    asyncio.run(main())
    logger.info("Scrapers completed")
