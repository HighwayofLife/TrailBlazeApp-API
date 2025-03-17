#!/usr/bin/env python
"""
Script to enrich events with website/flyer content.

This script fetches website content for events and extracts
detailed information using AI to populate the event_details field.

Usage:
    docker-compose run --rm api python -m scripts.enrich_website_flyer
"""

import asyncio
import logging
import sys
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

import sqlalchemy as sa
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models import Event
from app.services.enrichment import WebsiteFlyerEnrichmentService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("enrich_website_flyer")

async def get_events_needing_enrichment(session: AsyncSession, batch_size: int = 50, limit: Optional[int] = None) -> List[Event]:
    """
    Get events that need website/flyer enrichment.
    
    Args:
        session: Database session
        batch_size: Number of events to fetch
        limit: Optional limit on total number of events to process
        
    Returns:
        List of Event objects needing enrichment
    """
    now = datetime.now()
    three_months_from_now = now.date() + timedelta(days=90)
    one_day_ago = now - timedelta(days=1)
    seven_days_ago = now - timedelta(days=7)
    
    # Tiered query based on date proximity and last check time
    # Query structure:
    # 1. Events with website_url but no event_details or never checked
    # 2. Near-term events (within 3 months) not checked in the last day
    # 3. Future events (beyond 3 months) not checked in the last week
    query = (
        select(Event)
        .where(
            # Must have a website URL to enrich
            Event.website_url.is_not(None),
            
            # And match one of these conditions
            sa.or_(
                # No event_details or empty event_details
                sa.or_(
                    Event.event_details.is_(None),
                    Event.event_details == sa.cast({}, sa.JSON)
                ),
                
                # Never checked
                Event.last_website_check_at.is_(None),
                
                # Near-term events (within 3 months) not checked in the last day
                sa.and_(
                    Event.date <= three_months_from_now,
                    sa.or_(
                        Event.last_website_check_at.is_(None),
                        Event.last_website_check_at < one_day_ago
                    )
                ),
                
                # Future events (beyond 3 months) not checked in the last week
                sa.and_(
                    Event.date > three_months_from_now,
                    sa.or_(
                        Event.last_website_check_at.is_(None),
                        Event.last_website_check_at < seven_days_ago
                    )
                )
            )
        )
        .order_by(Event.date)
        .limit(limit if limit is not None else batch_size)
    )
    
    result = await session.execute(query)
    return list(result.scalars().all())
    
async def enrich_website_flyer(batch_size: int = 50, limit: Optional[int] = None) -> Dict[str, Any]:
    """
    Process events that need website/flyer enrichment.
    
    Args:
        batch_size: Number of events to process in each batch
        limit: Optional limit on total number of events to process
        
    Returns:
        Dictionary with statistics about the enrichment process
    """
    service = WebsiteFlyerEnrichmentService()
    total_processed = 0
    total_enriched = 0
    
    try:
        async with async_session() as session:
            # Get total count of events with website URLs
            query = select(sa.func.count()).select_from(Event).where(
                Event.website_url.is_not(None)
            )
            result = await session.execute(query)
            total_events_with_url = result.scalar_one()
            
            if total_events_with_url == 0:
                logger.info("No events found with website URLs.")
                return {
                    "total_processed": 0,
                    "total_enriched": 0,
                    "success_rate": 0
                }
            
            logger.info(f"Found {total_events_with_url} events with website URLs.")
            
            # Apply limit if specified
            remaining = limit if limit is not None else total_events_with_url
            
            while remaining > 0:
                current_batch_size = min(batch_size, remaining)
                
                # Get events needing enrichment
                events = await get_events_needing_enrichment(session, current_batch_size)
                
                if not events:
                    logger.info("No more events found that need enrichment.")
                    break
                    
                logger.info(f"Processing batch of {len(events)} events")
                
                # Process each event in the batch
                for event in events:
                    success = await service.enrich_event(event)
                    total_processed += 1
                    
                    if success:
                        total_enriched += 1
                
                # Commit the batch
                await session.commit()
                logger.info(f"Committed batch of {len(events)} events")
                
                # Update remaining count
                if limit is not None:
                    remaining -= len(events)
                    
        # Close aiohttp session
        await service.close()
        
        # Print summary
        result = {
            "total_processed": total_processed,
            "total_enriched": total_enriched,
            "success_rate": (total_enriched / total_processed * 100) if total_processed > 0 else 0
        }
        
        logger.info(f"Enrichment complete. Processed {total_processed} events, successfully enriched {total_enriched}.")
        if total_processed > 0:
            logger.info(f"Success rate: {result['success_rate']:.2f}% ({total_enriched}/{total_processed})")
            
        return result
        
    except Exception as e:
        logger.exception(f"Error during website/flyer enrichment: {str(e)}")
        # Try to close aiohttp session on error
        await service.close()
        raise

async def main():
    """Entry point for the script."""
    logger.info("Starting event website/flyer enrichment process")
    
    try:
        await enrich_website_flyer()
        logger.info("Event website/flyer enrichment completed successfully")
    except Exception as e:
        logger.exception(f"Error during website/flyer enrichment: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 