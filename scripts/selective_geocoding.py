#!/usr/bin/env python
"""
Selective Geocoding Script

This script queries the database for events that don't have coordinates
and attempts to geocode them based on the location field. It sets the
geocoding_attempted flag to track which events have been processed.
"""

import argparse
import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.event import Event
from app.services.geocoding import geocode_location
from app.logging_config import get_logger

# Setup logging
logger = get_logger("scripts.selective_geocoding")

async def find_events_needing_geocoding(db: AsyncSession, limit: Optional[int] = None) -> List[Event]:
    """
    Find events that need geocoding (have no coordinates and geocoding hasn't been attempted).
    
    Args:
        db: Database session
        limit: Optional limit on number of events to process
        
    Returns:
        List of Event objects
    """
    query = (
        select(Event)
        .where(
            (Event.latitude == None) & 
            (Event.longitude == None) & 
            (Event.geocoding_attempted == False)
        )
        .order_by(Event.date_start.desc())
    )
    
    if limit:
        query = query.limit(limit)
        
    result = await db.execute(query)
    events = result.scalars().all()
    
    logger.info(f"Found {len(events)} events that need geocoding")
    return events

async def geocode_event(event: Event) -> Tuple[bool, Optional[float], Optional[float]]:
    """
    Attempt to geocode an event based on its location.
    
    Args:
        event: Event to geocode
        
    Returns:
        Tuple of (success, latitude, longitude)
    """
    logger.info(f"Geocoding event: {event.name} ({event.id}) - Location: {event.location}")
    
    # Extract location from event_details if available
    location = event.location
    location_details = None
    
    if event.event_details and "location_details" in event.event_details:
        location_details = event.event_details["location_details"]
        
    # Build a more precise location string if we have details
    if location_details:
        city = location_details.get("city")
        state = location_details.get("state")
        country = location_details.get("country", "USA")
        
        if city and state:
            location = f"{city}, {state}, {country}"
        elif city:
            location = f"{city}, {country}"
            
    # Check if coordinates are already in event_details
    if event.event_details and "coordinates" in event.event_details:
        coords = event.event_details["coordinates"]
        if "latitude" in coords and "longitude" in coords:
            lat = coords["latitude"]
            lng = coords["longitude"]
            if lat and lng:
                logger.info(f"Using coordinates from event_details: {lat}, {lng}")
                return True, lat, lng
    
    # Attempt geocoding
    try:
        coords = await geocode_location(location)
        if coords:
            lat, lng = coords
            logger.info(f"Successfully geocoded to: {lat}, {lng}")
            return True, lat, lng
        else:
            logger.warning(f"Geocoding failed for: {location}")
            return False, None, None
    except Exception as e:
        logger.error(f"Error during geocoding: {str(e)}")
        return False, None, None

async def update_event_coordinates(db: AsyncSession, event: Event, 
                                  lat: Optional[float], lng: Optional[float],
                                  geocoding_attempted: bool = True) -> bool:
    """
    Update event with geocoding results.
    
    Args:
        db: Database session
        event: Event to update
        lat: Latitude (or None if geocoding failed)
        lng: Longitude (or None if geocoding failed)
        geocoding_attempted: Flag to indicate geocoding was attempted
        
    Returns:
        True if update was successful
    """
    try:
        # Update coordinates
        event.latitude = lat
        event.longitude = lng
        event.geocoding_attempted = geocoding_attempted
        
        # Update event_details if they exist
        if event.event_details is None:
            event.event_details = {}
            
        # Add or update coordinates in event_details
        if lat is not None and lng is not None:
            event.event_details["coordinates"] = {
                "latitude": lat,
                "longitude": lng
            }
            
        # Set geocoding_attempted in event_details too for consistency
        event.event_details["geocoding_attempted"] = geocoding_attempted
        
        # Mark for update
        event.updated_at = datetime.now()
        
        # Commit changes
        await db.commit()
        
        logger.info(f"Updated event {event.id} with geocoding results")
        return True
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating event {event.id}: {str(e)}")
        return False

async def process_events(limit: Optional[int] = None, 
                        batch_size: int = 10,
                        sleep_between_batches: int = 2) -> Dict[str, int]:
    """
    Process events that need geocoding.
    
    Args:
        limit: Maximum number of events to process
        batch_size: Number of events to process in each batch
        sleep_between_batches: Seconds to sleep between batches
        
    Returns:
        Dictionary with metrics
    """
    metrics = {
        "processed": 0,
        "successful": 0,
        "failed": 0,
        "error": 0
    }
    
    # Connect to DB
    db_gen = get_db()
    db = await anext(db_gen)
    
    try:
        # Get events that need geocoding
        events = await find_events_needing_geocoding(db, limit)
        total_events = len(events)
        metrics["total"] = total_events
        
        if total_events == 0:
            logger.info("No events found that need geocoding")
            return metrics
            
        # Process in batches to avoid overwhelming geocoding service
        for i in range(0, total_events, batch_size):
            batch = events[i:i+batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}/{(total_events+batch_size-1)//batch_size}")
            
            for event in batch:
                try:
                    # Attempt geocoding
                    success, lat, lng = await geocode_event(event)
                    
                    # Update the event
                    update_success = await update_event_coordinates(db, event, lat, lng, True)
                    
                    if update_success:
                        metrics["processed"] += 1
                        if success:
                            metrics["successful"] += 1
                        else:
                            metrics["failed"] += 1
                    else:
                        metrics["error"] += 1
                        
                except Exception as e:
                    metrics["error"] += 1
                    logger.error(f"Error processing event {event.id}: {str(e)}")
            
            # Sleep between batches to avoid rate limits
            if i + batch_size < total_events and sleep_between_batches > 0:
                logger.info(f"Sleeping for {sleep_between_batches} seconds before next batch")
                await asyncio.sleep(sleep_between_batches)
                
        return metrics
    
    finally:
        await db.close()

async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Selectively geocode events that don't have coordinates")
    parser.add_argument("--limit", type=int, help="Maximum number of events to process")
    parser.add_argument("--batch-size", type=int, default=10, help="Number of events to process in each batch")
    parser.add_argument("--sleep", type=int, default=2, help="Seconds to sleep between batches")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Set logging level based on verbosity
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Process events
    logger.info("Starting selective geocoding process")
    metrics = await process_events(args.limit, args.batch_size, args.sleep)
    
    # Print summary
    logger.info(f"Geocoding process complete. Summary:")
    logger.info(f"  Total events: {metrics.get('total', 0)}")
    logger.info(f"  Processed: {metrics.get('processed', 0)}")
    logger.info(f"  Successfully geocoded: {metrics.get('successful', 0)}")
    logger.info(f"  Failed geocoding: {metrics.get('failed', 0)}")
    logger.info(f"  Errors: {metrics.get('error', 0)}")

if __name__ == "__main__":
    asyncio.run(main()) 