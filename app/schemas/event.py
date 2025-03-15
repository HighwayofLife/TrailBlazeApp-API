from pydantic import BaseModel, Field, HttpUrl, EmailStr, validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, date

# Announcement schemas
class AnnouncementBase(BaseModel):
    title: str
    content: str
    is_important: bool = False
    source: Optional[str] = None

class AnnouncementCreate(AnnouncementBase):
    pass

class Announcement(AnnouncementBase):
    id: int
    event_id: int
    published_at: datetime
    
    class Config:
        orm_mode = True

# Event schemas
class EventBase(BaseModel):
    """Base Event Schema."""
    name: str
    description: Optional[str] = None
    location: str
    date_start: datetime
    date_end: Optional[datetime] = None
    organizer: Optional[str] = None
    website: Optional[str] = None
    flyer_url: Optional[str] = None
    region: Optional[str] = None
    distances: Optional[List[str]] = None

class EventCreate(EventBase):
    """Schema for creating an event."""
    pass

class EventUpdate(BaseModel):
    """Schema for updating an event."""
    name: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    date_start: Optional[datetime] = None
    date_end: Optional[datetime] = None
    organizer: Optional[str] = None
    website: Optional[str] = None
    flyer_url: Optional[str] = None
    region: Optional[str] = None
    distances: Optional[List[str]] = None

class EventResponse(EventBase):
    """Schema for event response."""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True

class EventDetail(EventResponse):
    announcements: List[Announcement] = []

# Response models
class EventListResponse(BaseModel):
    items: List[EventResponse]
    total: int
    page: int
    size: int
    pages: int
