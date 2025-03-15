from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.database import get_db
from app.models.event import Event
from app.schemas.event import EventResponse, EventCreate, EventUpdate
from app.crud.event import (
    create_event,
    get_event,
    get_events,
    update_event,
    delete_event,
)
from app.logging_config import get_logger

router = APIRouter()
logger = get_logger("api.events")


@router.get("/", response_model=List[EventResponse])
async def read_events(
    skip: int = 0,
    limit: int = 100,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    region: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve events with optional filtering.
    """
    try:
        events = await get_events(db, skip=skip, limit=limit, 
                                  date_from=date_from, date_to=date_to, region=region)
        return events
    except Exception as e:
        logger.error(f"Error retrieving events: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/", response_model=EventResponse, status_code=201)
async def create_new_event(
    event: EventCreate, db: AsyncSession = Depends(get_db)
):
    """
    Create a new event.
    """
    try:
        return await create_event(db=db, event=event)
    except Exception as e:
        logger.error(f"Error creating event: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{event_id}", response_model=EventResponse)
async def read_event(event_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get a specific event by ID.
    """
    try:
        event = await get_event(db, event_id=event_id)
        if event is None:
            raise HTTPException(status_code=404, detail="Event not found")
        return event
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving event {event_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{event_id}", response_model=EventResponse)
async def update_event_details(
    event_id: int, event: EventUpdate, db: AsyncSession = Depends(get_db)
):
    """
    Update an event.
    """
    try:
        db_event = await get_event(db, event_id=event_id)
        if db_event is None:
            raise HTTPException(status_code=404, detail="Event not found")
        return await update_event(db=db, event_id=event_id, event=event)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating event {event_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{event_id}", status_code=204)
async def delete_event_by_id(event_id: int, db: AsyncSession = Depends(get_db)):
    """
    Delete an event.
    """
    try:
        db_event = await get_event(db, event_id=event_id)
        if db_event is None:
            raise HTTPException(status_code=404, detail="Event not found")
        await delete_event(db=db, event_id=event_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting event {event_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
