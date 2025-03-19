"""
Shared database operations module for scrapers.

This module provides database operations for all scrapers in a consistent way.
It works as a wrapper around the application's CRUD operations to ensure data 
consistency and proper validation against the shared event schema.

Rather than implementing direct database operations, this handler delegates to
the application's CRUD functions to maintain a single source of truth for
database interactions.
"""

import logging
from typing import Dict, List, Any, Tuple, Optional, Union

# Import SQLAlchemy components
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncEngine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import AsyncAdaptedQueuePool

# Import application components
from app.schemas.event import EventBase, EventCreate
from app.crud.event import create_event, get_events, update_event
from .exceptions import DatabaseError
from app.config import get_settings

logger = logging.getLogger(__name__)

class DatabaseHandler:
    """
    Handles database operations for scrapers with connection pooling.
    
    This class provides a consistent interface for all scrapers to store
    and retrieve event data while maintaining proper validation against
    the central event schema.
    """

    _engine: Optional[AsyncEngine] = None
    _session_factory = None

    def __init__(self, db_url: Optional[str] = None):
        """
        Initialize database handler with connection pooling.
        
        Args:
            db_url: Optional database URL. If not provided, it will be
                   retrieved from application settings.
        
        Raises:
            ValueError: If database URL is not provided and not found in settings
            DatabaseError: If database initialization fails
        """
        settings = get_settings()
        self._db_url = db_url or settings.DATABASE_URL
        if not self._db_url:
            raise ValueError("Database URL not provided or found in config")

        # Initialize engine
        try:
            self._engine = create_async_engine(
                self._db_url,
                echo=False,
                future=True,
                poolclass=AsyncAdaptedQueuePool,
                pool_size=10,
                max_overflow=20
            )

            # Create async session factory
            self._session_factory = sessionmaker(
                self._engine,
                class_=AsyncSession,
                expire_on_commit=False
            )

            # Init metrics
            self._metrics = {
                'added': 0,
                'updated': 0,
                'skipped': 0,
                'errors': 0
            }

            logger.info("Database handler initialized")

        except Exception as e:
            raise DatabaseError(f"Failed to initialize database: {str(e)}")

    @classmethod
    def initialize(cls, database_url: str) -> None:
        """
        Initialize shared database engine and session factory.
        
        Args:
            database_url: Database connection string
            
        Raises:
            DatabaseError: If initialization fails
        """
        if not cls._engine:
            try:
                cls._engine = create_async_engine(
                    database_url,
                    poolclass=AsyncAdaptedQueuePool,
                    pool_pre_ping=True,
                    pool_size=5,
                    max_overflow=10,
                    echo=False
                )
                cls._session_factory = sessionmaker(
                    cls._engine,
                    class_=AsyncSession,
                    expire_on_commit=False
                )
                logger.info("Database connection pool initialized")
            except Exception as e:
                raise DatabaseError(f"Failed to initialize database: {str(e)}")

    async def store_events(self, events: List[Union[EventCreate, dict]]) -> Dict[str, int]:
        """
        Store events in the database using the application's CRUD operations.
        
        This method handles both new events and updates to existing events,
        checking for duplicates based on event name and date.
        
        Args:
            events: List of event data objects as EventCreate or dictionaries
        
        Returns:
            Dict with counts of events added, updated, skipped, and errors
        """
        batch_metrics = {
            'added': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0
        }

        if not events:
            logger.info("No events to store")
            return batch_metrics

        logger.info(f"Storing {len(events)} events in database")
        session = self.get_session()

        try:
            async with session as s:
                for event_data in events:
                    try:
                        # Ensure event_data is an EventCreate object
                        if isinstance(event_data, dict):
                            # Convert dict to EventCreate
                            event = EventCreate.model_validate(event_data)
                        else:
                            event = event_data
                            
                        # Check if event already exists
                        exists, event_id = await self._check_for_existing_event(s, event)
                        
                        if exists and event_id:
                            # Update existing event using app CRUD operation
                            logger.debug(f"Updating existing event: {event.name}")
                            await update_event(
                                db=s,
                                event_id=event_id,
                                event=event,
                                perform_geocoding=False  # Handle geocoding separately
                            )
                            batch_metrics['updated'] += 1
                        else:
                            # Create new event using app CRUD operation
                            logger.debug(f"Creating new event: {event.name}")
                            await create_event(
                                db=s,
                                event=event,
                                perform_geocoding=False  # Handle geocoding separately
                            )
                            batch_metrics['added'] += 1
                            
                    except Exception as e:
                        event_name = getattr(event_data, 'name', str(event_data))
                        logger.error(f"Error storing event {event_name}: {str(e)}")
                        batch_metrics['errors'] += 1
                        
                # Commit changes
                await s.commit()
        except Exception as e:
            logger.error(f"Database session error: {str(e)}")
            batch_metrics['errors'] += len(events)

        # Update overall metrics
        self._metrics['added'] += batch_metrics['added']
        self._metrics['updated'] += batch_metrics['updated']
        self._metrics['skipped'] += batch_metrics['skipped']
        self._metrics['errors'] += batch_metrics['errors']
        
        logger.info(f"Batch results: {batch_metrics}")
        return batch_metrics

    async def _check_for_existing_event(
        self, 
        session: AsyncSession, 
        event: EventCreate
    ) -> Tuple[bool, Optional[int]]:
        """
        Check if an event already exists in the database.
        
        Args:
            session: Database session
            event: Event to check
            
        Returns:
            Tuple of (exists, event_id)
        """
        logger.debug(f"Checking if event already exists: {event.name}")
        
        try:
            # Search for events with the same name and date_start
            existing_events_result = await get_events(
                db=session, 
                limit=10,
                name=event.name,
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
            
            # Check for match by name and date
            for existing_event in existing_events:
                if existing_event.name == event.name:
                    # For better matching, also check the date if available
                    if existing_event.date_start.date() == event.date_start.date():
                        logger.debug(f"Found existing event: {existing_event.name} (ID: {existing_event.id})")
                        return True, existing_event.id
            
            # No match found
            return False, None
            
        except Exception as e:
            logger.error(f"Error checking for existing event: {e}")
            return False, None

    def get_metrics(self) -> Dict[str, int]:
        """
        Get database operation metrics.
        
        Returns:
            Dictionary with counts of database operations
        """
        return self._metrics.copy()

    def get_session(self) -> AsyncSession:
        """
        Get a database session.
        
        Returns:
            An AsyncSession instance that can be used as a context manager
        """
        return self._session_factory()