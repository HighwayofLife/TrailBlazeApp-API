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
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    ride_manager: Optional[str] = None
    manager_email: Optional[str] = None
    manager_phone: Optional[str] = None
    judges: Optional[List[str]] = None
    directions: Optional[str] = None
    map_link: Optional[str] = None
    external_id: Optional[str] = None
    manager_contact: Optional[str] = None
    event_type: Optional[str] = None 
    event_details: Optional[Dict[str, Any]] = None  # For semi-structured data
    notes: Optional[str] = None
    is_canceled: Optional[bool] = False  # Added is_canceled field with default False
    source: str  # Required field to identify the data source

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
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    ride_manager: Optional[str] = None
    manager_email: Optional[str] = None
    manager_phone: Optional[str] = None
    judges: Optional[List[str]] = None
    directions: Optional[str] = None
    map_link: Optional[str] = None
    external_id: Optional[str] = None
    manager_contact: Optional[str] = None
    event_type: Optional[str] = None
    event_details: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    is_canceled: Optional[bool] = None  # Added to allow updating canceled status

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
