#!/usr/bin/env python
"""
Script to update existing event records to match the new structured data format.

This script:
1. Updates all existing events to ensure consistent data structure
2. Migrates data from event_details to the new direct fields like ride_id and has_intro_ride
3. Ensures structured data like distances and control_judges follow the expected format

Usage:
    python -m scripts.update_event_structure
"""

import os
import sys
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import async_session
from app.models.event import Event
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def get_all_events(session: AsyncSession) -> List[Event]:
    """Get all events from the database."""
    result = await session.execute(select(Event))
    events = result.scalars().all()
    logger.info(f"Retrieved {len(events)} events from database")
    return events

async def update_event_structure(event: Event, session: AsyncSession) -> None:
    """Update an event to match the new data structure."""
    changes = {}
    event_details = event.event_details or {}
    
    # Extract ride_id from event_details if available
    if "ride_id" in event_details and not event.ride_id:
        changes["ride_id"] = event_details["ride_id"]
    
    # Extract has_intro_ride from event_details if available 
    if "has_intro_ride" in event_details and event.has_intro_ride is None:
        changes["has_intro_ride"] = event_details["has_intro_ride"]
    
    # Ensure distances are in the correct format in event_details
    if "distances" in event_details and isinstance(event_details["distances"], list):
        structured_distances = []
        for dist in event_details["distances"]:
            if isinstance(dist, str):
                # Convert simple string to structured format
                structured_distances.append({
                    "distance": dist,
                    "date": event.date_start.strftime("%b %d, %Y") if event.date_start else None,
                    "start_time": None
                })
            elif isinstance(dist, dict) and "distance" in dist:
                # Already in structured format
                structured_distances.append(dist)
        
        if structured_distances:
            event_details["distances"] = structured_distances
            changes["event_details"] = event_details
    
    # Ensure control_judges are in the correct format
    if "control_judges" in event_details and isinstance(event_details["control_judges"], list):
        control_judges = []
        for judge in event_details["control_judges"]:
            if isinstance(judge, str):
                # Convert simple string to structured format
                control_judges.append({
                    "name": judge,
                    "role": "Control Judge"
                })
            elif isinstance(judge, dict) and "name" in judge:
                # Already in structured format
                control_judges.append(judge)
        
        if control_judges:
            event_details["control_judges"] = control_judges
            changes["event_details"] = event_details
    
    # Update the event if changes are needed
    if changes:
        await session.execute(
            update(Event)
            .where(Event.id == event.id)
            .values(**changes)
        )
        logger.info(f"Updated event {event.id}: {event.name} with {list(changes.keys())}")

async def main():
    """Main function to update all events."""
    logger.info("Starting event structure update")
    
    async with async_session() as session:
        try:
            events = await get_all_events(session)
            
            for event in events:
                await update_event_structure(event, session)
            
            await session.commit()
            logger.info("All events updated successfully")
        
        except Exception as e:
            await session.rollback()
            logger.error(f"Error updating events: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(main()) 