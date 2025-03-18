from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.schemas.event import EventCreate, EventUpdate
from app.services.geocoding import GeocodingService
from app.logging_config import get_logger

logger = get_logger("crud.event")


async def get_event(db: AsyncSession, event_id: int) -> Optional[Event]:
    """
    Get a specific event by ID.
    
    Args:
        db: Database session
        event_id: ID of the event to retrieve
        
    Returns:
        Event or None if not found
    """
    result = await db.execute(select(Event).where(Event.id == event_id))
    return result.scalars().first()


async def get_events(
    db: AsyncSession, 
    skip: int = 0, 
    limit: int = 100,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    region: Optional[str] = None,
    location: Optional[str] = None,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    radius: Optional[float] = None,
) -> List[Event]:
    """
    Get a list of events with optional filtering.
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        date_from: Optional start date filter (ISO format)
        date_to: Optional end date filter (ISO format)
        region: Optional region filter
        location: Optional location filter (text search)
        lat: Optional latitude for geographic search
        lng: Optional longitude for geographic search
        radius: Optional radius in miles for geographic search
        
    Returns:
        List of events
    """
    query = select(Event).offset(skip).limit(limit)
    
    # Apply filters if provided
    if date_from:
        try:
            date_from_obj = datetime.fromisoformat(date_from)
            query = query.where(Event.date_start >= date_from_obj)
        except ValueError:
            logger.warning(f"Invalid date_from format: {date_from}")
    
    if date_to:
        try:
            date_to_obj = datetime.fromisoformat(date_to)
            query = query.where(Event.date_start <= date_to_obj)
        except ValueError:
            logger.warning(f"Invalid date_to format: {date_to}")
    
    if region:
        query = query.where(Event.region == region)
    
    if location:
        # Simple text search on location field
        query = query.where(Event.location.ilike(f"%{location}%"))
    
    # Geographic search if coordinates and radius are provided
    if lat is not None and lng is not None and radius is not None:
        # Using Haversine formula directly in SQL to calculate distance in miles
        # This is a simplified approach for proximity search
        # For a more accurate implementation, consider using PostGIS
        # 3959 is the radius of the Earth in miles
        # Note: This requires PostgreSQL's ability to execute mathematical functions
        distance_formula = f"""
            (3959 * acos(
                cos(radians({lat})) * cos(radians(latitude)) * 
                cos(radians(longitude) - radians({lng})) + 
                sin(radians({lat})) * sin(radians(latitude))
            ))
        """
        # We need to ensure both latitude and longitude are not null
        query = query.where(Event.latitude.is_not(None))
        query = query.where(Event.longitude.is_not(None))
        # Using SQL expression to filter by distance
        # This requires raw SQL execution which may vary by database backend
        # For simplicity, we're using a text-based approach here
        query = query.filter(f"({distance_formula}) <= {radius}")
    
    # Sort by date
    query = query.order_by(Event.date_start)
    
    result = await db.execute(query)
    return result.scalars().all()


async def create_event(db: AsyncSession, event: EventCreate, perform_geocoding: bool = False) -> Event:
    """
    Create a new event.
    
    Args:
        db: Database session
        event: Event data
        perform_geocoding: Whether to automatically geocode the event (default: False)
        
    Returns:
        Created event
    """
    # Creating dictionary with field mappings from schema to model
    db_event = Event(
        name=event.name,
        description=event.description,
        location=event.location,
        date_start=event.date_start,
        date_end=event.date_end,
        organizer=event.organizer,
        website=event.website,
        flyer_url=event.flyer_url,
        region=event.region,
        distances=event.distances,
        latitude=event.latitude,
        longitude=event.longitude,
        ride_manager=event.ride_manager,
        manager_contact=event.manager_contact,
        event_type=event.event_type,
        event_details=event.event_details,
        notes=event.notes,
        external_id=event.external_id,
        source=getattr(event, 'source', None),
        map_link=event.map_link,
        manager_email=event.manager_email,
        manager_phone=event.manager_phone,
        judges=event.judges,
        directions=event.directions,
        is_canceled=event.is_canceled,
    )
    
    # Add to session
    db.add(db_event)
    await db.commit()
    await db.refresh(db_event)
    
    # Geocode the event if coordinates are not provided and geocoding is enabled
    if perform_geocoding and (db_event.latitude is None or db_event.longitude is None):
        geocoding_service = GeocodingService()
        success = await geocoding_service.geocode_event(db_event)
        
        if success:
            await db.commit()
            await db.refresh(db_event)
            logger.info(f"Geocoded event {db_event.id} to coordinates: ({db_event.latitude}, {db_event.longitude})")
        else:
            logger.warning(f"Failed to geocode event {db_event.id} at location: {db_event.location}")
    
    logger.info(f"Created new event: {db_event.id} - {db_event.name}")
    return db_event


async def update_event(db: AsyncSession, event_id: int, event: EventUpdate, perform_geocoding: bool = False) -> Optional[Event]:
    """
    Update an existing event.
    
    Args:
        db: Database session
        event_id: ID of the event to update
        event: Updated event data
        perform_geocoding: Whether to automatically geocode the event if location changed (default: False)
        
    Returns:
        Updated event or None if not found
    """
    # Get the current event
    db_event = await get_event(db, event_id)
    if not db_event:
        return None
    
    # Create a dictionary with only the fields that are not None
    update_data = {k: v for k, v in event.dict().items() if v is not None}
    
    # Flag to determine if we need to geocode after update
    need_geocoding = False
    
    # If the location is being updated and coordinates are not provided, we'll need to geocode
    if perform_geocoding and 'location' in update_data and ('latitude' not in update_data or 'longitude' not in update_data):
        need_geocoding = True
    
    if update_data:
        # Update the event
        query = (
            update(Event)
            .where(Event.id == event_id)
            .values(**update_data)
            .returning(Event)
        )
        result = await db.execute(query)
        await db.commit()
        
        logger.info(f"Updated event: {event_id}")
    
    # Get the updated event
    db_event = await get_event(db, event_id)
    
    # Geocode if needed
    if perform_geocoding and (need_geocoding or (db_event.latitude is None or db_event.longitude is None)):
        geocoding_service = GeocodingService()
        success = await geocoding_service.geocode_event(db_event)
        
        if success:
            await db.commit()
            logger.info(f"Geocoded event {event_id} to coordinates: ({db_event.latitude}, {db_event.longitude})")
        else:
            logger.warning(f"Failed to geocode event {event_id} at location: {db_event.location}")
    
    # Return the updated event
    return db_event


async def delete_event(db: AsyncSession, event_id: int) -> bool:
    """
    Delete an event.
    
    Args:
        db: Database session
        event_id: ID of the event to delete
        
    Returns:
        True if the event was deleted, False otherwise
    """
    query = delete(Event).where(Event.id == event_id)
    result = await db.execute(query)
    await db.commit()
    
    if result.rowcount > 0:
        logger.info(f"Deleted event: {event_id}")
        return True
    
    logger.warning(f"Attempted to delete non-existent event: {event_id}")
    return False
