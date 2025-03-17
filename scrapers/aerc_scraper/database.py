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
            logger.info(f"Starting to store {len(db_events)} events in database")
            
            for event in db_events:
                try:
                    # Log event details before processing
                    logger.debug(f"Processing event: {event.name} ({event.date_start})")
                    
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
                            logger.debug(f"Found existing event: ID={existing_id}, Canceled={existing_is_canceled}")
                            break
                    
                    if exists:
                        if existing_is_canceled:
                            logger.info(f"Skipping canceled event: {event.name}")
                            self.metrics['skipped'] += 1
                        else:
                            logger.info(f"Updating existing event: {event.name}")
                            self.metrics['updated'] += 1
                    else:
                        logger.info(f"Adding new event: {event.name}")
                        self.metrics['added'] += 1
                    
                except Exception as e:
                    logger.error(f"Error processing event {event.name}: {str(e)}")
                    self.metrics['errors'] += 1
            
            # Log final metrics
            logger.info("Database storage metrics:")
            logger.info(f"  Added: {self.metrics['added']}")
            logger.info(f"  Updated: {self.metrics['updated']}")
            logger.info(f"  Skipped: {self.metrics['skipped']}")
            logger.info(f"  Errors: {self.metrics['errors']}")
            
            return self.metrics
            
        except Exception as e:
            logger.error(f"Database operation failed: {str(e)}")
            raise DatabaseError(f"Database operation failed: {str(e)}")
    
    def get_metrics(self) -> Dict[str, int]:
        """Get database operation metrics."""
        return self.metrics.copy()