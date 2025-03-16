"""
Database operations handler for storing and updating events.
"""

import logging
from typing import Dict, List, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.event import EventCreate
from app.crud.event import create_event, get_events
from .exceptions import DatabaseError

logger = logging.getLogger(__name__)

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
                    for existing in existing_events:
                        if existing.name == event.name and existing.location == event.location:
                            exists = True
                            break
                    
                    if not exists:
                        await create_event(db, event)
                        self.metrics['added'] += 1
                        logger.info(f"Created new event: {event.name}")
                    else:
                        self.metrics['updated'] += 1
                        logger.info(f"Event already exists: {event.name}")
                        
                except Exception as e:
                    self.metrics['errors'] += 1
                    logger.error(f"Error storing event in database: {e}")
                    continue
            
            logger.info(
                f"Database operation completed: {self.metrics['added']} added, "
                f"{self.metrics['updated']} updated, {self.metrics['errors']} errors"
            )
            
            return self.get_metrics()
            
        except Exception as e:
            raise DatabaseError(f"Database operation failed: {str(e)}")
    
    def get_metrics(self) -> Dict[str, int]:
        """Get database operation metrics."""
        return self.metrics.copy()