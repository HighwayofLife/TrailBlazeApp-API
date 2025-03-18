"""
Core event schema definitions for TrailBlazeApp API.

This is the SINGLE SOURCE OF TRUTH for all event data structures in the application.
All components should import from this module to ensure consistency.

Design principles:
1. Comprehensive: Includes all possible fields needed by any component
2. Extensible: Uses inheritance to allow specific sources to add their own fields
3. Compatible: Works with both database models and API responses
4. Typed: Uses strong typing for all fields to catch errors early
"""

from pydantic import BaseModel, Field, HttpUrl, EmailStr, validator, ConfigDict, field_validator
from typing import List, Optional, Dict, Any, Union, Literal
from datetime import datetime, date
from enum import Enum

# =====================================================================
# Enums and Constants
# =====================================================================

class EventSourceEnum(str, Enum):
    """Supported event data sources."""
    AERC = "AERC"
    SERA = "SERA"
    UMECRA = "UMECRA"
    OTHER = "OTHER"

class EventTypeEnum(str, Enum):
    """Supported event types."""
    ENDURANCE = "endurance"
    CTR = "competitive_trail"
    INTRO = "intro_ride"
    CLINIC = "clinic"
    OTHER = "other"

class RegionEnum(str, Enum):
    """AERC Regions."""
    MW = "MW"  # Midwest 
    NE = "NE"  # Northeast
    NW = "NW"  # Northwest
    SE = "SE"  # Southeast
    SW = "SW"  # Southwest
    W = "W"    # West
    PS = "PS"  # Pacific South
    MT = "MT"  # Mountain
    CT = "CT"  # Central
    OTHER = "OTHER"

# =====================================================================
# Common component schemas
# =====================================================================

class ContactInfo(BaseModel):
    """Contact information schema."""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, pattern=r'^\+?[\d\(\)\-\.\s]{10,}$')
    role: Optional[str] = None

    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "example": {
                "name": "John Doe",
                "email": "john.doe@example.com",
                "phone": "555-123-4567",
                "role": "Ride Manager"
            }
        }
    )

class EventDistance(BaseModel):
    """Detailed distance information schema."""
    distance: str
    date: Optional[str] = None
    start_time: Optional[str] = None
    max_riders: Optional[int] = None
    entry_fee: Optional[float] = None
    unit: str = Field(default="miles", description="Unit of distance measurement")

    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "example": {
                "distance": "50 miles",
                "date": "Mar 28, 2025",
                "start_time": "07:00 am"
            }
        }
    )

class ControlJudge(BaseModel):
    """Control judge information."""
    name: str
    role: str = "Control Judge"

    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "example": {
                "name": "Dr. Jane Smith",
                "role": "Head Control Judge"
            }
        }
    )

class LocationDetails(BaseModel):
    """Detailed location information."""
    city: Optional[str] = None
    state: Optional[str] = None
    country: str = "USA"
    zip_code: Optional[str] = None
    address: Optional[str] = None

    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "example": {
                "city": "Sonoita",
                "state": "AZ",
                "country": "USA"
            }
        }
    )

class Coordinates(BaseModel):
    """Geographic coordinates."""
    latitude: float
    longitude: float

    @field_validator('latitude')
    def validate_latitude(cls, v):
        if not -90 <= v <= 90:
            raise ValueError("Latitude must be between -90 and 90")
        return v

    @field_validator('longitude')
    def validate_longitude(cls, v):
        if not -180 <= v <= 180:
            raise ValueError("Longitude must be between -180 and 180")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "latitude": 31.6784,
                "longitude": -110.6255
            }
        }
    )

# =====================================================================
# Announcement schemas
# =====================================================================

class AnnouncementBase(BaseModel):
    """Base announcement schema."""
    title: str
    content: str
    is_important: bool = False
    source: Optional[str] = None

class AnnouncementCreate(AnnouncementBase):
    """Create announcement schema."""
    pass

class Announcement(AnnouncementBase):
    """Response announcement schema."""
    id: int
    event_id: int
    published_at: datetime
    
    model_config = ConfigDict(
        from_attributes=True
    )

# =====================================================================
# Core Event schemas
# =====================================================================

class EventBase(BaseModel):
    """Base Event Schema - common to all operations."""
    # Core fields
    name: str
    source: str = Field(..., description="Source system identifier (e.g., 'AERC')")
    event_type: str = Field(default="endurance", description="Type of event")
    date_start: datetime
    date_end: Optional[datetime] = None
    location: str
    
    # Additional descriptive fields
    description: Optional[str] = None
    region: Optional[str] = None
    organizer: Optional[str] = None
    
    # URLs
    website: Optional[str] = None
    flyer_url: Optional[str] = None
    map_link: Optional[str] = None
    
    # Distances - supports both simple and complex formats
    distances: Optional[Union[List[str], List[Dict[str, Any]], List[EventDistance]]] = None
    
    # Coordinates
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    geocoding_attempted: Optional[bool] = False
    
    # Contact information
    ride_manager: Optional[str] = None
    manager_email: Optional[str] = None
    manager_phone: Optional[str] = None
    manager_contact: Optional[str] = None
    
    # Judge information
    judges: Optional[Union[List[str], List[Dict[str, Any]], List[ControlJudge]]] = None
    
    # Additional fields
    directions: Optional[str] = None
    external_id: Optional[str] = None
    ride_id: Optional[str] = None
    notes: Optional[str] = None
    
    # Status flags
    is_canceled: Optional[bool] = False
    has_intro_ride: Optional[bool] = False
    
    # Structured data storage
    event_details: Optional[Dict[str, Any]] = None
    
    @field_validator('date_end')
    def set_date_end(cls, v, info):
        """Set date_end to date_start if not provided."""
        values = info.data
        if not v and 'date_start' in values:
            return values['date_start']
        return v
    
    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "example": {
                "name": "Original Old Pueblo",
                "source": "AERC",
                "event_type": "endurance",
                "date_start": "2025-03-28T00:00:00.000Z",
                "location": "Empire Ranch, Empire Ranch Rd, Sonoita, AZ",
                "region": "SW",
                "ride_manager": "Marilyn McCoy",
                "manager_phone": "520-360-9445",
                "manager_email": "marilynmccoy@hotmail.com"
            }
        }
    )

class EventCreate(EventBase):
    """Schema for creating an event."""
    pass

class EventUpdate(BaseModel):
    """Schema for updating an event."""
    # All fields are optional for updates
    name: Optional[str] = None
    source: Optional[str] = None
    event_type: Optional[str] = None
    date_start: Optional[datetime] = None
    date_end: Optional[datetime] = None
    location: Optional[str] = None
    description: Optional[str] = None
    region: Optional[str] = None
    organizer: Optional[str] = None
    website: Optional[str] = None
    flyer_url: Optional[str] = None
    map_link: Optional[str] = None
    distances: Optional[Union[List[str], List[Dict[str, Any]], List[EventDistance]]] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    geocoding_attempted: Optional[bool] = None
    ride_manager: Optional[str] = None
    manager_email: Optional[str] = None
    manager_phone: Optional[str] = None
    manager_contact: Optional[str] = None
    judges: Optional[Union[List[str], List[Dict[str, Any]], List[ControlJudge]]] = None
    directions: Optional[str] = None
    external_id: Optional[str] = None
    ride_id: Optional[str] = None
    notes: Optional[str] = None
    is_canceled: Optional[bool] = None
    has_intro_ride: Optional[bool] = None
    event_details: Optional[Dict[str, Any]] = None

class EventResponse(EventBase):
    """Schema for event response."""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(
        from_attributes=True
    )

class EventDetail(EventResponse):
    """Detailed event response with announcements."""
    announcements: List[Announcement] = []

# =====================================================================
# Source-specific Event schemas
# =====================================================================

class AERCEvent(EventBase):
    """AERC-specific event schema."""
    source: Literal[EventSourceEnum.AERC] = EventSourceEnum.AERC
    event_type: str = "endurance"
    sanctioning_status: Optional[str] = None
    control_judges: Optional[List[ControlJudge]] = None
    treatment_vets: Optional[List[ContactInfo]] = None
    has_drug_testing: bool = False
    
    # Include location details in a structured format
    location_details: Optional[LocationDetails] = None
    
    # Allow providing coordinates in a structured format
    coordinates: Optional[Coordinates] = None

class SERAEvent(EventBase):
    """SERA-specific event schema."""
    source: Literal[EventSourceEnum.SERA] = EventSourceEnum.SERA
    membership_required: bool = True
    junior_discount: bool = False

class UMECRAEvent(EventBase):
    """UMECRA-specific event schema."""
    source: Literal[EventSourceEnum.UMECRA] = EventSourceEnum.UMECRA
    division: Optional[str] = None
    meal_included: bool = False

# =====================================================================
# Response models for API
# =====================================================================

class EventListResponse(BaseModel):
    """Paginated list of events."""
    items: List[EventResponse]
    total: int
    page: int
    size: int
    pages: int

# =====================================================================
# Utility functions
# =====================================================================

# Mapping of source to schema
SOURCE_SCHEMAS = {
    EventSourceEnum.AERC: AERCEvent,
    EventSourceEnum.SERA: SERAEvent,
    EventSourceEnum.UMECRA: UMECRAEvent
}

def validate_event(data: dict, source: str) -> BaseModel:
    """Validate event data against the appropriate schema."""
    source_enum = EventSourceEnum(source)
    schema = SOURCE_SCHEMAS.get(source_enum, EventBase)
    
    if not schema:
        raise ValueError(f"Unsupported event source: {source}")
    
    return schema.model_validate(data)
