from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.schemas.event import EventCreate, EventUpdate
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
    
    # Sort by date
    query = query.order_by(Event.date_start)
    
    result = await db.execute(query)
    return result.scalars().all()


async def create_event(db: AsyncSession, event: EventCreate) -> Event:
    """
    Create a new event.
    
    Args:
        db: Database session
        event: Event data
        
    Returns:
        Created event
    """
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
    )
    
    db.add(db_event)
    await db.commit()
    await db.refresh(db_event)
    
    logger.info(f"Created new event: {db_event.id} - {db_event.name}")
    return db_event


async def update_event(db: AsyncSession, event_id: int, event: EventUpdate) -> Optional[Event]:
    """
    Update an existing event.
    
    Args:
        db: Database session
        event_id: ID of the event to update
        event: Updated event data
        
    Returns:
        Updated event or None if not found
    """
    # Get the current event
    db_event = await get_event(db, event_id)
    if not db_event:
        return None
    
    # Create a dictionary with only the fields that are not None
    update_data = {k: v for k, v in event.dict().items() if v is not None}
    
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
        
    # Return the updated event
    return await get_event(db, event_id)


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
