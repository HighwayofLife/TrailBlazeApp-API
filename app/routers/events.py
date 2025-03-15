from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_, and_
from typing import List, Optional
from datetime import date
import math

from ..database import get_db
from ..models.event import Event as EventModel, Announcement as AnnouncementModel
from ..schemas.event import Event, EventDetail, EventCreate, EventUpdate, Announcement, EventListResponse

router = APIRouter()

@router.get("/events", response_model=EventListResponse)
async def list_events(
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    start_date: Optional[date] = Query(None, description="Filter by start date (inclusive)"),
    end_date: Optional[date] = Query(None, description="Filter by end date (inclusive)"),
    organization: Optional[str] = Query(None, description="Filter by organization (e.g., PNER, AERC)"),
    state: Optional[str] = Query(None, description="Filter by state"),
    is_verified: Optional[bool] = Query(None, description="Filter by verification status"),
):
    """
    List events with optional filtering and pagination.
    """
    # Build the query with filters
    query = select(EventModel)
    
    # Apply filters
    filters = []
    if start_date:
        filters.append(EventModel.start_date >= start_date)
    if end_date:
        filters.append(EventModel.end_date <= end_date)
    if organization:
        filters.append(EventModel.organization == organization)
    if state:
        filters.append(EventModel.state == state)
    if is_verified is not None:
        filters.append(EventModel.is_verified == is_verified)
    
    # Apply all filters to query
    if filters:
        query = query.where(and_(*filters))
    
    # Add ordering
    query = query.order_by(EventModel.start_date)
    
    # Count total items
    count_query = select(EventModel)
    if filters:
        count_query = count_query.where(and_(*filters))
    
    count_result = await db.execute(count_query)
    total = len(count_result.scalars().all())
    
    # Apply pagination
    query = query.offset((page - 1) * size).limit(size)
    
    # Execute query
    result = await db.execute(query)
    events = result.scalars().all()
    
    # Calculate total pages
    total_pages = math.ceil(total / size) if total > 0 else 1
    
    return EventListResponse(
        items=events,
        total=total,
        page=page,
        size=size,
        pages=total_pages
    )

@router.get("/events/{event_id}", response_model=EventDetail)
async def get_event(
    event_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed information for a specific event by ID.
    """
    query = select(EventModel).where(EventModel.id == event_id)
    result = await db.execute(query)
    event = result.scalars().first()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    return event

@router.get("/events/{event_id}/announcements", response_model=List[Announcement])
async def get_event_announcements(
    event_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all announcements for a specific event.
    """
    # First verify the event exists
    event_query = select(EventModel).where(EventModel.id == event_id)
    event_result = await db.execute(event_query)
    event = event_result.scalars().first()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Get announcements
    query = select(AnnouncementModel).where(AnnouncementModel.event_id == event_id).order_by(AnnouncementModel.published_at.desc())
    result = await db.execute(query)
    announcements = result.scalars().all()
    
    return announcements

@router.get("/events/search", response_model=List[Event])
async def search_events(
    query: str = Query(..., min_length=3, description="Search query string"),
    db: AsyncSession = Depends(get_db)
):
    """
    Search events by name, description, or location.
    """
    search_term = f"%{query}%"
    
    db_query = select(EventModel).where(
        or_(
            EventModel.name.ilike(search_term),
            EventModel.description.ilike(search_term),
            EventModel.location_name.ilike(search_term),
            EventModel.city.ilike(search_term),
            EventModel.state.ilike(search_term)
        )
    ).order_by(EventModel.start_date)
    
    result = await db.execute(db_query)
    events = result.scalars().all()
    
    return events

@router.get("/events/test", description="Test endpoint to verify database connection")
async def test_database_connection(db: AsyncSession = Depends(get_db)):
    try:
        # Try to fetch all events
        query = select(EventModel)
        result = await db.execute(query)
        events = result.scalars().all()
        
        # Convert events to dict for response
        events_list = [
            {
                "id": event.id,
                "name": event.name,
                "description": event.description,
                "location_name": event.location_name,
                "start_date": event.start_date.isoformat() if event.start_date else None,
                "end_date": event.end_date.isoformat() if event.end_date else None,
                "is_verified": event.is_verified,
                "created_at": event.created_at.isoformat() if event.created_at else None
            }
            for event in events
        ]
        
        return {
            "status": "success",
            "message": "Database connection successful",
            "count": len(events_list),
            "events": events_list
        }
    
    except Exception as e:
        import logging
        logging.error(f"Database test error: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Database connection test failed: {str(e)}"
        )
