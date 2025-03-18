"""Shared schema validation module."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, EmailStr, HttpUrl, validator

class EventSourceEnum(str, Enum):
    """Supported event data sources."""
    AERC = "AERC"
    SERA = "SERA"
    UMECRA = "UMECRA"

class EventTypeEnum(str, Enum):
    """Supported event types."""
    ENDURANCE = "endurance"
    CTR = "competitive_trail"
    INTRO = "intro_ride"
    CLINIC = "clinic"

class ContactInfo(BaseModel):
    """Contact information schema."""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, pattern=r'^\+?[\d\(\)\-\.\s]{10,}$')
    role: Optional[str] = None

class Distance(BaseModel):
    """Event distance schema."""
    distance: str
    date: datetime = Field(..., description="Date of this distance")
    start_time: Optional[str] = None
    max_riders: Optional[int] = None
    entry_fee: Optional[float] = None
    unit: str = Field(default="miles", description="Unit of distance measurement")

class Location(BaseModel):
    """Event location schema."""
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: str = Field(default="USA")
    coordinates: Optional[Dict[str, float]] = None
    map_url: Optional[HttpUrl] = None

    @validator('coordinates')
    def validate_coordinates(cls, v):
        """Validate latitude and longitude."""
        if v:
            # Validate coordinates in dictionary format
            lat = v.get('latitude')
            lon = v.get('longitude')
            if lat is None or lon is None:
                raise ValueError("Coordinates must include latitude and longitude")
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                raise ValueError("Invalid coordinates")
        return v

class EventBase(BaseModel):
    """Base event schema shared by all sources."""
    name: str
    source: EventSourceEnum
    event_type: EventTypeEnum
    date_start: datetime
    date_end: Optional[datetime] = None
    location: Location
    region: Optional[str] = None
    description: Optional[str] = None
    distances: List[Distance] = Field(default_factory=list)
    contacts: List[ContactInfo] = Field(default_factory=list)
    website_url: Optional[HttpUrl] = None
    registration_url: Optional[HttpUrl] = None
    has_intro_ride: bool = False
    is_canceled: bool = False
    external_id: Optional[str] = None
    last_updated: datetime = Field(default_factory=datetime.now)
    event_details: Optional[Dict[str, Any]] = None

    @validator('date_end')
    def set_date_end(cls, v, values):
        """Set date_end to date_start if not provided."""
        if not v and 'date_start' in values:
            return values['date_start']
        return v

    @validator('distances')
    def validate_distances(cls, v, values):
        """Validate distance dates fall within event dates."""
        if v and 'date_start' in values:
            date_start = values['date_start']
            date_end = values.get('date_end') or date_start
            
            for distance in v:
                if not (date_start <= distance.date <= date_end):
                    raise ValueError(
                        f"Distance date {distance.date} outside event range "
                        f"{date_start} - {date_end}"
                    )
        return v

class AERCEvent(EventBase):
    """AERC-specific event schema."""
    sanctioning_status: Optional[str] = None
    control_judges: List[ContactInfo] = Field(default_factory=list)
    treatment_vets: List[ContactInfo] = Field(default_factory=list)
    has_drug_testing: bool = False

class SERAEvent(EventBase):
    """SERA-specific event schema."""
    membership_required: bool = True
    junior_discount: bool = False

class UMECRAEvent(EventBase):
    """UMECRA-specific event schema."""
    division: Optional[str] = None
    meal_included: bool = False

# Mapping of source to schema
SOURCE_SCHEMAS = {
    EventSourceEnum.AERC: AERCEvent,
    EventSourceEnum.SERA: SERAEvent,
    EventSourceEnum.UMECRA: UMECRAEvent
}

def validate_event(data: dict, source: EventSourceEnum) -> BaseModel:
    """Validate event data against appropriate schema."""
    schema = SOURCE_SCHEMAS.get(source)
    if not schema:
        raise ValueError(f"Unsupported event source: {source}")
    return schema.model_validate(data)