"""
Database operations handler for storing and updating events.
"""

import logging
from typing import Dict, List, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.event import EventCreate
from app.crud.event import create_event, get_events
from .exceptions import DatabaseError
from app.logging_config import get_logger

# Use the properly configured logger from app.logging_config
logger = get_logger("scrapers.aerc_scraper.database")

class DatabaseHandler:
    """Handles database operations for events."""
    
    def __init__(self):
        self.metrics = {
            'added': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0
        }
    
    async def store_events(self, db_events: List[EventCreate], db: AsyncSession) -> Dict[str, int]:
        """Store events in the database."""
        try:
            for event in db_events:
                try:
                    # Check if event exists (by name and date)
                    existing_events = await get_events(
                        db,
                        date_from=event.date_start.isoformat() if event.date_start else None,
                        date_to=event.date_start.isoformat() if event.date_start else None
                    )
                    
                    exists = False
                    existing_id = None
                    existing_is_canceled = None
                    
                    for existing in existing_events:
                        if existing.name == event.name and existing.location == event.location:
                            exists = True
                            existing_id = existing.id
                            existing_is_canceled = existing.is_canceled
                            break
                    
                    if not exists:
                        # Create new event
                        await create_event(db, event)
                        self.metrics['added'] += 1
                        logger.info(f"Created new event: {event.name}")
                    else:
                        # Check if we need to update the is_canceled status
                        from app.crud.event import update_event
                        from app.schemas.event import EventUpdate
                        
                        # Only update if the is_canceled status is different
                        if hasattr(event, 'is_canceled') and event.is_canceled != existing_is_canceled:
                            update_data = EventUpdate(is_canceled=event.is_canceled)
                            await update_event(db, existing_id, update_data)
                            logger.info(f"Updated event canceled status: {event.name} (is_canceled={event.is_canceled})")
                            self.metrics['updated'] += 1
                        else:
                            # Event exists and no update needed
                            self.metrics['skipped'] += 1
                            logger.info(f"Event already exists (skipped): {event.name}")
                        
                except Exception as e:
                    self.metrics['errors'] += 1
                    logger.error(f"Error storing event in database: {e}")
                    continue
            
            logger.info(
                f"Database operation completed: {self.metrics['added']} added, "
                f"{self.metrics['updated']} updated, {self.metrics['skipped']} skipped, "
                f"{self.metrics['errors']} errors"
            )
            
            return self.get_metrics()
            
        except Exception as e:
            raise DatabaseError(f"Database operation failed: {str(e)}")
    
    def get_metrics(self) -> Dict[str, int]:
        """Get database operation metrics."""
        return self.metrics.copy()