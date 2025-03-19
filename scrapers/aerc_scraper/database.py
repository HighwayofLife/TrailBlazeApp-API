"""
Database operations handler for AERC scraper.

This module provides AERC-specific database operations for storing and
retrieving event data. It uses the application's CRUD functions to ensure
data consistency and schema validation.
"""

import logging
from typing import Dict, List, Any, Tuple, Optional, Union

# Try to import AsyncSession, fallback to a type annotation string for linting
try:
    from sqlalchemy.ext.asyncio import AsyncSession
except ImportError:
    AsyncSession = 'AsyncSession'

from app.schemas.event import EventCreate, AERCEvent
from app.crud.event import create_event, get_events, update_event
from app.logging_config import get_logger
from .exceptions import DatabaseError

# Use the properly configured logger from app.logging_config
logger = get_logger("scrapers.aerc_scraper.database")

class DatabaseHandler:
    """
    Handler for AERC-specific database operations.

    This handler is responsible for storing and retrieving AERC event data
    using the application's CRUD operations.
    """

    def __init__(self):
        """Initialize a new DatabaseHandler with empty metrics."""
        self.metrics = {
            "added": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 0
        }

    async def store_events(self, events: List[Union[EventCreate, AERCEvent, Dict[str, Any]]], db: AsyncSession) -> Dict[str, int]:
        """
        Store a list of AERC events in the database.

        Events are checked against existing entries to avoid duplicates.

        Args:
            events: List of event objects or dictionaries to store
            db: Database session

        Returns:
            Dictionary with operation metrics (added, updated, skipped, errors)
        """
        if not events:
            logger.info("No events to store.")
            return self.metrics

        logger.info(f"Storing {len(events)} AERC events in database...")

        # Reset batch metrics
        batch_metrics = {
            "added": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 0
        }

        # Process each event
        for event_data in events:
            try:
                # Convert dict to EventCreate if needed
                if isinstance(event_data, dict):
                    # Use the appropriate schema for AERC events
                    event = AERCEvent.model_validate(event_data)
                else:
                    event = event_data

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
                event_name = getattr(event_data, 'name', str(event_data))
                logger.error(f"Error processing event {event_name}: {str(e)}")
                batch_metrics["errors"] += 1

        # Update overall metrics
        self.metrics["added"] += batch_metrics["added"]
        self.metrics["updated"] += batch_metrics["updated"]
        self.metrics["skipped"] += batch_metrics["skipped"]
        self.metrics["errors"] += batch_metrics["errors"]

        logger.info(f"Batch results: {batch_metrics}")
        return batch_metrics

    def get_metrics(self) -> Dict[str, int]:
        """
        Get database operation metrics.

        Returns:
            Dictionary with counts of database operations
        """
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
            # Search by exact name and date - most reliable for identifying duplicates
            existing_events_cursor = await get_events(
                db=db,
                limit=10,
                skip=0,
                search=event.name,  # Use search parameter for partial matches
                date_from=event.date_start.date().isoformat() if event.date_start else None,
                date_to=event.date_start.date().isoformat() if event.date_start else None,
                source="AERC"  # Only look at AERC events
            )

            # Convert results to a list if needed
            existing_events = []
            if hasattr(existing_events_cursor, 'all'):
                existing_events = await existing_events_cursor.all()
            elif isinstance(existing_events_cursor, list):
                existing_events = existing_events_cursor
            else:
                logger.warning(f"Unexpected result type from get_events: {type(existing_events_cursor)}")
                return False, None

            if not existing_events:
                logger.debug(f"No existing AERC events found for {event.name}")
                return False, None

            # Check each event for a match - prioritize exact name match
            for existing_event in existing_events:
                # If ride_id exists and matches, that's the best identifier
                if hasattr(event, 'ride_id') and event.ride_id and hasattr(existing_event, 'ride_id') and existing_event.ride_id == event.ride_id:
                    logger.debug(f"Found existing event by ride_id: {existing_event.name} (ID: {existing_event.id})")
                    return True, existing_event.id

                # Otherwise check for name and date match
                if existing_event.name == event.name:
                    date_match = False
                    if hasattr(existing_event, 'date_start') and hasattr(event, 'date_start'):
                        if existing_event.date_start.date() == event.date_start.date():
                            date_match = True

                    if date_match:
                        logger.debug(f"Found existing event by name and date: {existing_event.name} (ID: {existing_event.id})")
                        return True, existing_event.id

            # No match found
            return False, None

        except Exception as e:
            logger.error(f"Error checking for existing event: {e}", exc_info=True)
            return False, None
