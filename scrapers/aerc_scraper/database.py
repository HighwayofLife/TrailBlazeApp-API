"""
Database operations handler for storing and updating events.
"""

import logging
from typing import Dict, List, Any, Tuple, Optional

# Try to import AsyncSession, fallback to a type annotation string for linting
try:
    from sqlalchemy.ext.asyncio import AsyncSession
except ImportError:
    AsyncSession = 'AsyncSession'

from app.schemas.event import EventCreate
from app.crud.event import create_event, get_events, update_event
from .exceptions import DatabaseError
from app.logging_config import get_logger

# Use the properly configured logger from app.logging_config
logger = get_logger("scrapers.aerc_scraper.database")

class DatabaseHandler:
    """Handler for database operations."""

    def __init__(self):
        """Initialize a new DatabaseHandler."""
        self.metrics = {
            "added": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 0
        }

    async def store_events(self, events: List[EventCreate], db: AsyncSession) -> Dict[str, int]:
        """
        Store a list of events in the database.

        Events are checked against existing entries to avoid duplicates.

        Args:
            events: List of EventCreate objects to store
            db: Database session

        Returns:
            Dictionary with operation metrics
        """
        if not events:
            logger.info("No events to store.")
            return self.metrics

        logger.info(f"Storing {len(events)} events in database...")

        # Reset metrics
        batch_metrics = {
            "added": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 0
        }

        # Process each event
        for event in events:
            try:
                # Check if event already exists
                exists, event_id = await self.check_for_existing_event(event, db)

                if exists and event_id:
                    # Update existing event
                    logger.debug(f"Updating existing event: {event.name}")
                    await update_event(
                        db=db,
                        event_id=event_id,
                        event=event,
                        perform_geocoding=False  # We'll handle geocoding separately
                    )
                    batch_metrics["updated"] += 1
                else:
                    # Create new event
                    logger.debug(f"Creating new event: {event.name}")
                    await create_event(
                        db=db,
                        event=event,
                        perform_geocoding=False  # We'll handle geocoding separately
                    )
                    batch_metrics["added"] += 1

            except Exception as e:
                logger.error(f"Error processing event {event.name}: {str(e)}")
                batch_metrics["errors"] += 1

        # Update overall metrics
        self.metrics["added"] += batch_metrics["added"]
        self.metrics["updated"] += batch_metrics["updated"]
        self.metrics["skipped"] += batch_metrics["skipped"]
        self.metrics["errors"] += batch_metrics["errors"]

        logger.info(f"Batch results: {batch_metrics}")
        return batch_metrics

    def get_metrics(self) -> Dict[str, int]:
        """Get database operation metrics."""
        return self.metrics.copy()

    async def check_for_existing_event(self, event: EventCreate, db: AsyncSession) -> Tuple[bool, Optional[int]]:
        """
        Check if an event already exists in the database.

        Args:
            event: Event to check
            db: Database session

        Returns:
            Tuple of (exists, event_id)
        """
        logger.debug(f"Checking if event already exists: {event.name}")
        
        try:
            # Search for events with the same name and date_start
            # Use the API as defined in get_events function (without filters dict)
            existing_events_result = await get_events(
                db=db, 
                limit=10,
                location=event.name,  # Use the name as part of location search
                date_from=event.date_start.isoformat() if event.date_start else None,
                date_to=event.date_start.isoformat() if event.date_start else None
            )
            
            # Ensure we have a list to work with
            existing_events = []
            if hasattr(existing_events_result, 'all'):
                # If it's a SQLAlchemy result that needs to be converted to a list
                existing_events = await existing_events_result.all()
            elif isinstance(existing_events_result, list):
                # If it's already a list (like in a test mock)
                existing_events = existing_events_result
            else:
                # Handle unexpected return type
                logger.warning(f"Unexpected result type from get_events: {type(existing_events_result)}")
                return False, None
            
            if not existing_events:
                logger.debug(f"No existing events found for {event.name}")
                return False, None
            
            # Check each existing event for a match
            for existing_event in existing_events:
                if existing_event.name == event.name:
                    # Found a match
                    logger.debug(f"Found existing event: {existing_event.name} (ID: {existing_event.id})")
                    return True, existing_event.id
            
            # No match found
            return False, None
            
        except Exception as e:
            logger.error(f"Error checking for existing event: {e}")
            return False, None