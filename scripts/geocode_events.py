#!/usr/bin/env python
"""
Script to geocode existing events in the database.

This script adds latitude and longitude coordinates to events 
that don't have them by using the geocoding enrichment service.

Usage:
    docker-compose run --rm api python -m scripts.geocode_events
"""

import asyncio
import logging
import sys
from typing import List, Optional

import sqlalchemy as sa
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models import Event
from app.services.enrichment import GeocodingEnrichmentService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("geocode_events")

async def geocode_events(batch_size: int = 50, limit: Optional[int] = None) -> None:
    """
    Process all events that don't have coordinates and geocode them.
    
    Args:
        batch_size: Number of events to process in each batch
        limit: Optional limit on total number of events to process
    """
    service = GeocodingEnrichmentService()
    total_processed = 0
    total_geocoded = 0
    
    async with async_session() as session:
        # Get total count of events without coordinates
        query = select(sa.func.count()).select_from(Event).where(
            (Event.latitude.is_(None)) | (Event.longitude.is_(None))
        )
        result = await session.execute(query)
        total_events = result.scalar_one()
        
        if total_events == 0:
            logger.info("No events found that need geocoding.")
            return
        
        logger.info(f"Found {total_events} events without coordinates.")
        
        # Apply limit if specified
        if limit is not None:
            total_events = min(total_events, limit)
            logger.info(f"Will process up to {total_events} events due to limit.")
        
        # Process events in batches
        offset = 0
        while offset < total_events:
            # Determine batch size
            current_batch_size = min(batch_size, total_events - offset)
            
            # Query events without coordinates
            query = select(Event).where(
                (Event.latitude.is_(None)) | (Event.longitude.is_(None))
            ).offset(offset).limit(current_batch_size)
            
            result = await session.execute(query)
            events = result.scalars().all()
            
            if not events:
                break
                
            logger.info(f"Processing batch of {len(events)} events (offset: {offset})")
            
            # Process each event in the batch
            for event in events:
                success = await service.enrich_event(event)
                total_processed += 1
                
                if success:
                    total_geocoded += 1
            
            # Commit the batch
            await session.commit()
            logger.info(f"Committed batch of {len(events)} events")
            
            # Update offset for next batch
            offset += current_batch_size
    
    # Print summary
    logger.info(f"Geocoding complete. Processed {total_processed} events, successfully geocoded {total_geocoded}.")
    if total_processed > 0:
        logger.info(f"Success rate: {total_geocoded / total_processed * 100:.2f}% ({total_geocoded}/{total_processed})")

async def main():
    """Entry point for the script."""
    logger.info("Starting event geocoding process")
    
    try:
        await geocode_events()
        logger.info("Event geocoding completed successfully")
    except Exception as e:
        logger.exception(f"Error during geocoding: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 