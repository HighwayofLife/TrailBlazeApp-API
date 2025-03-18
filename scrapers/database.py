"""Shared database operations module."""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncEngine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import AsyncAdaptedQueuePool
from sqlalchemy import select, update, insert, and_
from sqlalchemy.sql import text

from app.models.event import Event
from .exceptions import DatabaseError
from app.config import get_settings

logger = logging.getLogger(__name__)

class DatabaseHandler:
    """Handles database operations with connection pooling."""
    
    _engine: Optional[AsyncEngine] = None
    _session_factory = None
    
    def __init__(self, db_url: Optional[str] = None):
        """Initialize database handler."""
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
                'inserts': 0,
                'updates': 0,
                'errors': 0
            }
            
            logger.info("Database handler initialized")
            
        except Exception as e:
            raise DatabaseError(f"Failed to initialize database: {str(e)}")
    
    @classmethod
    def initialize(cls, database_url: str) -> None:
        """Initialize database engine and session factory."""
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
    
    async def store_events(self, events: List[Any]) -> Dict[str, int]:
        """Store events in the database.
        
        Args:
            events: List of event data objects or dictionaries
            
        Returns:
            Dict with counts of events added, updated, and skipped
        """
        session = self.get_session()  # Get a session but don't use async with
        added = 0
        updated = 0
        skipped = 0
        
        try:
            async with session as s:  # Now use the async context manager correctly
                for event_data in events:
                    try:
                        # Check if event already exists
                        existing_event = await self._get_existing_event(s, event_data)
                        
                        if existing_event:
                            # Update existing event
                            await self._update_event(s, existing_event.id, event_data)
                            updated += 1
                            continue
                        
                        # Create new event
                        await self._create_event(s, event_data)
                        added += 1
                        
                    except Exception as e:
                        logger.error(f"Error storing event: {str(e)}")
                        skipped += 1
                
                # Commit changes
                await s.commit()
        except Exception as e:
            logger.error(f"Database session error: {str(e)}")
            skipped += len(events)
        
        self._metrics['inserts'] += added
        self._metrics['updates'] += updated
        self._metrics['errors'] += skipped
        
        return {'added': added, 'updated': updated, 'skipped': skipped}
    
    async def _create_event(self, session: AsyncSession, data: Any) -> None:
        """Create a new event record."""
        try:
            # Create event based on data passed
            if hasattr(data, 'model_dump'):  # Pydantic v2 model
                data_dict = data.model_dump(exclude_unset=True)
            elif hasattr(data, 'dict'):      # Pydantic v1 model
                data_dict = data.dict(exclude_unset=True)
            else:                           # Assuming it's a dict
                data_dict = data
            
            # Create event based on whether we have a dictionary or an object
            if isinstance(data_dict, dict):
                event = Event(
                    name=data_dict.get('name'),
                    source=data_dict.get('source'),
                    event_type=data_dict.get('event_type'),
                    date_start=data_dict.get('date_start'),
                    date_end=data_dict.get('date_end'),
                    location=data_dict.get('location'),
                    region=data_dict.get('region'),
                    description=data_dict.get('description'),
                    website=data_dict.get('website'),
                    flyer_url=data_dict.get('flyer_url'),
                    map_link=data_dict.get('map_link'),
                    is_canceled=data_dict.get('is_canceled', False),
                    external_id=data_dict.get('external_id'),
                    ride_manager=data_dict.get('ride_manager'),
                    manager_email=data_dict.get('manager_email'),
                    manager_phone=data_dict.get('manager_phone'),
                    distances=data_dict.get('distances'),
                    latitude=data_dict.get('latitude'),
                    longitude=data_dict.get('longitude'),
                    event_details=data_dict.get('event_details'),
                    updated_at=datetime.now()
                )
            else:
                # For EventCreate or other objects with direct attribute access
                event = Event(
                    name=getattr(data, 'name', None),
                    source=getattr(data, 'source', None),
                    event_type=getattr(data, 'event_type', None),
                    date_start=getattr(data, 'date_start', None),
                    date_end=getattr(data, 'date_end', None),
                    location=getattr(data, 'location', None),
                    region=getattr(data, 'region', None),
                    description=getattr(data, 'description', None),
                    website=getattr(data, 'website', None),
                    flyer_url=getattr(data, 'flyer_url', None),
                    map_link=getattr(data, 'map_link', None),
                    is_canceled=getattr(data, 'is_canceled', False),
                    external_id=getattr(data, 'external_id', None),
                    ride_manager=getattr(data, 'ride_manager', None),
                    manager_email=getattr(data, 'manager_email', None),
                    manager_phone=getattr(data, 'manager_phone', None),
                    distances=getattr(data, 'distances', None),
                    latitude=getattr(data, 'latitude', None),
                    longitude=getattr(data, 'longitude', None),
                    event_details=getattr(data, 'event_details', None),
                    updated_at=datetime.now()
                )
            
            session.add(event)
            logger.debug(f"Created event: {event.name}")
            
        except Exception as e:
            raise DatabaseError(f"Failed to create event: {str(e)}")
    
    async def _update_event(self, session: AsyncSession, event_id: int, data: Any) -> None:
        """Update an existing event record."""
        try:
            # Get the event
            event = await session.get(Event, event_id)
            if not event:
                raise DatabaseError(f"Event with ID {event_id} not found")
            
            # Convert data to dictionary if it's a Pydantic model
            if hasattr(data, 'model_dump'):  # Pydantic v2 model
                data_dict = data.model_dump(exclude_unset=True)
            elif hasattr(data, 'dict'):      # Pydantic v1 model
                data_dict = data.dict(exclude_unset=True)
            else:                           # Assuming it's a dict
                data_dict = data
            
            # Update the fields
            if isinstance(data_dict, dict):
                # Handle dictionary data
                if 'name' in data_dict:
                    event.name = data_dict['name']
                if 'source' in data_dict:
                    event.source = data_dict['source']
                if 'event_type' in data_dict:
                    event.event_type = data_dict['event_type']
                if 'date_start' in data_dict:
                    event.date_start = data_dict['date_start']
                if 'date_end' in data_dict:
                    event.date_end = data_dict['date_end']
                if 'location' in data_dict:
                    event.location = data_dict['location']
                if 'region' in data_dict:
                    event.region = data_dict['region']
                if 'description' in data_dict:
                    event.description = data_dict['description']
                if 'website' in data_dict:
                    event.website = data_dict['website']
                if 'flyer_url' in data_dict:
                    event.flyer_url = data_dict['flyer_url']
                if 'map_link' in data_dict:
                    event.map_link = data_dict['map_link']
                if 'is_canceled' in data_dict:
                    event.is_canceled = data_dict['is_canceled']
                if 'external_id' in data_dict:
                    event.external_id = data_dict['external_id']
                if 'ride_manager' in data_dict:
                    event.ride_manager = data_dict['ride_manager']
                if 'manager_email' in data_dict:
                    event.manager_email = data_dict['manager_email']
                if 'manager_phone' in data_dict:
                    event.manager_phone = data_dict['manager_phone']
                if 'distances' in data_dict:
                    event.distances = data_dict['distances']
                if 'latitude' in data_dict:
                    event.latitude = data_dict['latitude']
                if 'longitude' in data_dict:
                    event.longitude = data_dict['longitude']
                if 'event_details' in data_dict:
                    event.event_details = data_dict['event_details']
            else:
                # Handle object with attributes
                if hasattr(data, 'name'):
                    event.name = data.name
                if hasattr(data, 'source'):
                    event.source = data.source
                if hasattr(data, 'event_type'):
                    event.event_type = data.event_type
                if hasattr(data, 'date_start'):
                    event.date_start = data.date_start
                if hasattr(data, 'date_end'):
                    event.date_end = data.date_end
                if hasattr(data, 'location'):
                    event.location = data.location
                if hasattr(data, 'region'):
                    event.region = data.region
                if hasattr(data, 'description'):
                    event.description = data.description
                if hasattr(data, 'website'):
                    event.website = data.website
                if hasattr(data, 'flyer_url'):
                    event.flyer_url = data.flyer_url
                if hasattr(data, 'map_link'):
                    event.map_link = data.map_link
                if hasattr(data, 'is_canceled'):
                    event.is_canceled = data.is_canceled
                if hasattr(data, 'external_id'):
                    event.external_id = data.external_id
                if hasattr(data, 'ride_manager'):
                    event.ride_manager = data.ride_manager
                if hasattr(data, 'manager_email'):
                    event.manager_email = data.manager_email
                if hasattr(data, 'manager_phone'):
                    event.manager_phone = data.manager_phone
                if hasattr(data, 'distances'):
                    event.distances = data.distances
                if hasattr(data, 'latitude'):
                    event.latitude = data.latitude
                if hasattr(data, 'longitude'):
                    event.longitude = data.longitude
                if hasattr(data, 'event_details'):
                    event.event_details = data.event_details
            
            event.updated_at = datetime.now()
            logger.debug(f"Updated event: {event.name}")
            
        except Exception as e:
            raise DatabaseError(f"Failed to update event: {str(e)}")
    
    async def _get_or_create_location(
        self,
        session: AsyncSession,
        data: Dict[str, Any]
    ) -> None:
        """Deprecated: Locations are now handled differently."""
        logger.debug("_get_or_create_location is deprecated - locations are now stored as text")
        return None
    
    async def _add_distances(
        self,
        session: AsyncSession,
        event_id: int,
        distances: List[Dict[str, Any]]
    ) -> None:
        """Deprecated: Distances are now stored in the events table directly."""
        # This method is kept for backwards compatibility but doesn't do anything
        logger.debug("_add_distances is deprecated - distances are stored directly in Event table")
        pass
    
    async def _add_contacts(
        self,
        session: AsyncSession,
        event_id: int,
        contacts: List[Dict[str, Any]]
    ) -> None:
        """Deprecated: Contacts are now stored in the events table directly."""
        # This method is kept for backwards compatibility but doesn't do anything
        logger.debug("_add_contacts is deprecated - contacts are stored directly in Event table")
        pass
    
    async def _get_existing_event(
        self,
        session: AsyncSession,
        event_data: Any
    ) -> Optional[Event]:
        """Get an existing event by name and date."""
        try:
            # Extract event name and date_start from either a dict or an object
            if isinstance(event_data, dict):
                name = event_data.get('name')
                date_start = event_data.get('date_start')
                source = event_data.get('source', None)
                external_id = event_data.get('external_id', None)
            else:
                name = getattr(event_data, 'name', None)
                date_start = getattr(event_data, 'date_start', None)
                source = getattr(event_data, 'source', None)
                external_id = getattr(event_data, 'external_id', None)

            if not name or not date_start:
                logger.warning("Missing name or date_start in event data")
                return None

            # Try to find by external_id first if available
            if external_id and source:
                stmt = select(Event).where(
                    and_(
                        Event.external_id == external_id,
                        Event.source == source
                    )
                )
                result = await session.execute(stmt)
                event = result.scalars().first()
                if event:
                    return event

            # Otherwise find by name and date
            stmt = select(Event).where(
                and_(
                    Event.name == name,
                    Event.date_start == date_start
                )
            )
            result = await session.execute(stmt)
            return result.scalars().first()
            
        except Exception as e:
            logger.error(f"Error getting existing event: {str(e)}")
            return None
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get database operation metrics."""
        metrics = self._metrics.copy()
        return metrics

    def get_session(self) -> AsyncSession:
        """Get a database session.
        
        Returns:
            An AsyncSession instance that can be used as a context manager
        """
        return self._session_factory()