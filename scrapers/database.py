"""Shared database operations module."""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncEngine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import AsyncAdaptedQueuePool
from sqlalchemy import select, update, insert
from sqlalchemy.sql import text

from app.models.events import Event, EventDistance, EventContact
from app.models.locations import Location
from .exceptions import DatabaseError

logger = logging.getLogger(__name__)

class DatabaseHandler:
    """Handles database operations with connection pooling."""
    
    _engine: Optional[AsyncEngine] = None
    _session_factory = None
    
    def __init__(self, database_url: Optional[str] = None):
        """Initialize database handler."""
        self.metrics = {
            'inserts': 0,
            'updates': 0,
            'errors': 0,
            'operation_time': 0.0,
            'batch_sizes': []
        }
        
        if database_url:
            self.initialize(database_url)
    
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
    
    async def store_events(
        self,
        events: List[Dict[str, Any]],
        session: AsyncSession
    ) -> Dict[str, Any]:
        """Store events in database."""
        if not events:
            logger.warning("No events to store")
            return {'added': 0, 'updated': 0, 'skipped': 0}
        
        start_time = datetime.now()
        self.metrics['batch_sizes'].append(len(events))
        
        added = updated = skipped = 0
        
        try:
            for event_data in events:
                try:
                    # Check if event already exists
                    external_id = event_data.get('external_id')
                    if external_id:
                        existing = await session.execute(
                            select(Event).where(Event.external_id == external_id)
                        )
                        existing_event = existing.scalar_one_or_none()
                        
                        if existing_event:
                            # Update existing event
                            await self._update_event(session, existing_event, event_data)
                            updated += 1
                            continue
                    
                    # Create new event
                    await self._create_event(session, event_data)
                    added += 1
                    
                except Exception as e:
                    logger.error(f"Error storing event {event_data.get('name', 'Unknown')}: {str(e)}")
                    self.metrics['errors'] += 1
                    skipped += 1
            
            # Commit all changes
            await session.commit()
            
        except Exception as e:
            await session.rollback()
            raise DatabaseError(f"Database operation failed: {str(e)}")
        
        finally:
            self.metrics['operation_time'] = (datetime.now() - start_time).total_seconds()
            self.metrics['inserts'] = added
            self.metrics['updates'] = updated
        
        logger.info(f"Stored {added} new events, updated {updated}, skipped {skipped}")
        return {'added': added, 'updated': updated, 'skipped': skipped}
    
    async def _create_event(self, session: AsyncSession, data: Dict[str, Any]) -> None:
        """Create a new event record."""
        try:
            # Create or get location
            location_data = data.pop('location')
            location = await self._get_or_create_location(session, location_data)
            
            # Create event
            event = Event(
                name=data['name'],
                source=data['source'],
                event_type=data['event_type'],
                date_start=data['date_start'],
                date_end=data.get('date_end'),
                location_id=location.id,
                region=data.get('region'),
                description=data.get('description'),
                website_url=data.get('website_url'),
                registration_url=data.get('registration_url'),
                has_intro_ride=data.get('has_intro_ride', False),
                is_cancelled=data.get('is_cancelled', False),
                external_id=data.get('external_id'),
                last_updated=data.get('last_updated', datetime.now())
            )
            session.add(event)
            await session.flush()  # Get ID before adding relations
            
            # Add distances
            if 'distances' in data:
                await self._add_distances(session, event.id, data['distances'])
            
            # Add contacts
            if 'contacts' in data:
                await self._add_contacts(session, event.id, data['contacts'])
            
        except Exception as e:
            raise DatabaseError(f"Failed to create event: {str(e)}")
    
    async def _update_event(
        self,
        session: AsyncSession,
        event: Event,
        data: Dict[str, Any]
    ) -> None:
        """Update an existing event record."""
        try:
            # Update location if changed
            if 'location' in data:
                location = await self._get_or_create_location(session, data.pop('location'))
                event.location_id = location.id
            
            # Update event fields
            for key, value in data.items():
                if hasattr(event, key) and key not in ('id', 'created_at'):
                    setattr(event, key, value)
            
            event.last_updated = datetime.now()
            
            # Update distances
            if 'distances' in data:
                await session.execute(
                    text('DELETE FROM event_distances WHERE event_id = :event_id'),
                    {'event_id': event.id}
                )
                await self._add_distances(session, event.id, data['distances'])
            
            # Update contacts
            if 'contacts' in data:
                await session.execute(
                    text('DELETE FROM event_contacts WHERE event_id = :event_id'),
                    {'event_id': event.id}
                )
                await self._add_contacts(session, event.id, data['contacts'])
            
        except Exception as e:
            raise DatabaseError(f"Failed to update event: {str(e)}")
    
    async def _get_or_create_location(
        self,
        session: AsyncSession,
        data: Dict[str, Any]
    ) -> Location:
        """Get existing location or create new one."""
        try:
            # Try to find existing location
            query = select(Location).where(
                Location.name == data['name'],
                Location.city == data.get('city'),
                Location.state == data.get('state')
            )
            result = await session.execute(query)
            location = result.scalar_one_or_none()
            
            if location:
                return location
            
            # Create new location
            location = Location(
                name=data['name'],
                address=data.get('address'),
                city=data.get('city'),
                state=data.get('state'),
                zip_code=data.get('zip_code'),
                country=data.get('country', 'USA'),
                latitude=data.get('coordinates', (None, None))[0],
                longitude=data.get('coordinates', (None, None))[1],
                map_url=data.get('map_url')
            )
            session.add(location)
            await session.flush()
            return location
            
        except Exception as e:
            raise DatabaseError(f"Failed to process location: {str(e)}")
    
    async def _add_distances(
        self,
        session: AsyncSession,
        event_id: int,
        distances: List[Dict[str, Any]]
    ) -> None:
        """Add distance records for an event."""
        try:
            for distance_data in distances:
                distance = EventDistance(
                    event_id=event_id,
                    distance=distance_data['distance'],
                    date=distance_data['date'],
                    start_time=distance_data.get('start_time'),
                    max_riders=distance_data.get('max_riders'),
                    entry_fee=distance_data.get('entry_fee')
                )
                session.add(distance)
                
        except Exception as e:
            raise DatabaseError(f"Failed to add distances: {str(e)}")
    
    async def _add_contacts(
        self,
        session: AsyncSession,
        event_id: int,
        contacts: List[Dict[str, Any]]
    ) -> None:
        """Add contact records for an event."""
        try:
            for contact_data in contacts:
                contact = EventContact(
                    event_id=event_id,
                    name=contact_data['name'],
                    email=contact_data.get('email'),
                    phone=contact_data.get('phone'),
                    role=contact_data.get('role')
                )
                session.add(contact)
                
        except Exception as e:
            raise DatabaseError(f"Failed to add contacts: {str(e)}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get database operation metrics."""
        metrics = self.metrics.copy()
        if self.metrics['batch_sizes']:
            metrics['avg_batch_size'] = sum(self.metrics['batch_sizes']) / len(self.metrics['batch_sizes'])
        return metrics