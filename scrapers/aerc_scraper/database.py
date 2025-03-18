"""
Database operations handler for storing and updating events.
"""

import logging
from typing import Dict, List, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.event import EventCreate
from app.crud.event import create_event, get_events, update_event
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
        """
        Store events in the database with improved error handling and verification.
        
        Args:
            db_events: List of events to store
            db: Database session
            
        Returns:
            Dictionary with metrics (added, updated, skipped, errors)
        """
        try:
            logger.info(f"Starting to store {len(db_events)} events in database")
            
            # Process events in smaller batches for better transaction management
            batch_size = 20
            total_batches = (len(db_events) + batch_size - 1) // batch_size  # Ceiling division
            
            for batch_index in range(total_batches):
                start_idx = batch_index * batch_size
                end_idx = min(start_idx + batch_size, len(db_events))
                current_batch = db_events[start_idx:end_idx]
                
                logger.info(f"Processing batch {batch_index+1}/{total_batches} with {len(current_batch)} events")
                
                # Events successfully processed in this batch
                batch_success_ids = []
                batch_metrics = {'added': 0, 'updated': 0, 'skipped': 0, 'errors': 0}
                
                # Process each event in the batch
                for event in current_batch:
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
                                batch_metrics['skipped'] += 1
                            else:
                                # Update the existing event
                                from app.schemas.event import EventUpdate
                                event_data = event.dict()
                                event_update = EventUpdate(**event_data)
                                
                                # Don't perform geocoding during scraper updates
                                updated_event = await update_event(db, existing_id, event_update, perform_geocoding=False)
                                
                                if updated_event:
                                    logger.info(f"Updated existing event: {event.name} (ID: {existing_id})")
                                    batch_metrics['updated'] += 1
                                    batch_success_ids.append(existing_id)
                                else:
                                    logger.error(f"Failed to update event: {event.name} (ID: {existing_id})")
                                    batch_metrics['errors'] += 1
                        else:
                            # Create the new event (without automatic geocoding)
                            new_event = await create_event(db, event, perform_geocoding=False)
                            
                            if new_event and new_event.id:
                                logger.info(f"Added new event: {event.name} (ID: {new_event.id})")
                                batch_metrics['added'] += 1
                                batch_success_ids.append(new_event.id)
                            else:
                                logger.error(f"Failed to add new event: {event.name}")
                                batch_metrics['errors'] += 1
                        
                    except Exception as e:
                        logger.error(f"Error processing event {event.name}: {str(e)}")
                        batch_metrics['errors'] += 1
                
                # Commit the batch
                await db.commit()
                
                # Verify batch results
                if batch_metrics['added'] > 0 or batch_metrics['updated'] > 0:
                    try:
                        # Verify that the events are actually in the database
                        verified_count = 0
                        for event_id in batch_success_ids:
                            from app.models import Event as EventModel
                            result = await db.execute(f"SELECT COUNT(*) FROM events WHERE id = {event_id}")
                            count = result.scalar()
                            if count == 1:
                                verified_count += 1
                            else:
                                logger.warning(f"Event ID {event_id} not found in database after insertion/update")
                        
                        # Log verification results
                        verification_pct = (verified_count / len(batch_success_ids)) * 100 if batch_success_ids else 0
                        logger.info(f"Batch {batch_index+1} verification: {verified_count}/{len(batch_success_ids)} events confirmed ({verification_pct:.1f}%)")
                        
                        if verified_count < len(batch_success_ids):
                            logger.warning(f"Some events in batch {batch_index+1} could not be verified in the database")
                    
                    except Exception as e:
                        logger.error(f"Error verifying batch {batch_index+1}: {str(e)}")
                
                # Update overall metrics
                self.metrics['added'] += batch_metrics['added']
                self.metrics['updated'] += batch_metrics['updated']
                self.metrics['skipped'] += batch_metrics['skipped'] 
                self.metrics['errors'] += batch_metrics['errors']
                
                # Log batch metrics
                logger.info(f"Batch {batch_index+1} metrics: added={batch_metrics['added']}, updated={batch_metrics['updated']}, " +
                           f"skipped={batch_metrics['skipped']}, errors={batch_metrics['errors']}")
            
            # Log final metrics
            logger.info("Database storage complete. Final metrics:")
            logger.info(f"  Added: {self.metrics['added']}")
            logger.info(f"  Updated: {self.metrics['updated']}")
            logger.info(f"  Skipped: {self.metrics['skipped']}")
            logger.info(f"  Errors: {self.metrics['errors']}")
            logger.info(f"  Total success rate: {((self.metrics['added'] + self.metrics['updated']) / len(db_events)) * 100:.1f}%")
            
            return self.metrics
            
        except Exception as e:
            logger.error(f"Database operation failed: {str(e)}")
            raise DatabaseError(f"Database operation failed: {str(e)}")
    
    def get_metrics(self) -> Dict[str, int]:
        """Get database operation metrics."""
        return self.metrics.copy()