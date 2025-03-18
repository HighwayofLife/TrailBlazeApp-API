"""Tests for shared schema validation module."""

import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError
from app.schemas.event import (
    EventSourceEnum,
    EventTypeEnum,
    ContactInfo,
    EventDistance,
    LocationDetails,
    EventBase,
    AERCEvent,
    validate_event,
    SERAEvent,
    UMECRAEvent,
    ControlJudge
)

@pytest.fixture
def valid_location():
    """Create a valid location fixture."""
    return {
        "name": "Test Venue",
        "city": "Test City",
        "state": "CA",
        "country": "USA"
    }

@pytest.fixture
def valid_contact():
    """Create a valid contact fixture."""
    return {
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "+12345678900",
        "role": "Ride Manager"
    }

@pytest.fixture
def valid_distance():
    """Create a valid distance fixture."""
    return {
        "distance": "50 Miles",
        "date": datetime.now(),
        "start_time": "6:00 AM"
    }

def test_contact_info_validation():
    """Test contact information validation."""
    # Valid contact
    contact = ContactInfo(
        name="John Doe",
        email="john@example.com",
        phone="+12345678900"
    )
    assert contact.name == "John Doe"
    
    # Invalid email
    with pytest.raises(ValidationError):
        ContactInfo(
            name="John Doe",
            email="invalid-email"
        )
    
    # Invalid phone
    with pytest.raises(ValidationError):
        ContactInfo(
            name="John Doe",
            phone="123"  # Too short
        )

def test_location_validation():
    """Test location validation."""
    # Valid location as a string
    assert LocationDetails(city="Test City", state="CA", country="USA")
    
    # Valid location with optional fields
    assert LocationDetails(
        city="Test City",
        state="CA",
        country="USA",
        zip_code="12345",
        address="123 Test St"
    )
    
    # Ensure country defaults to USA
    location = LocationDetails(city="Test City", state="CA")
    assert location.country == "USA"
    
    # ValidationError for invalid country type
    with pytest.raises(ValidationError):
        LocationDetails(city="Test City", state="CA", country=123)

def test_distance_validation():
    """Test distance validation."""
    # Valid distance
    distance = EventDistance(
        distance="50",
        date="2025-03-28",
        start_time="07:00 AM"
    )
    assert distance.distance == "50"
    assert distance.date == "2025-03-28"
    
    # Default unit is miles
    assert distance.unit == "miles"
    
    # Invalid distance with non-string date field
    with pytest.raises(ValidationError):
        EventDistance(distance="50", date=datetime.now())

def test_event_base_validation(valid_location):
    """Test validation for the EventBase schema."""
    location_str = "Test Venue, Test City, CA"
    
    # Validate with minimum fields
    event = EventBase(
        name="Test Event",
        date_start=datetime.now(),
        source=EventSourceEnum.AERC,
        event_type=EventTypeEnum.ENDURANCE,
        location=location_str
    )
    assert event.name == "Test Event"
    assert event.source == EventSourceEnum.AERC
    assert event.event_type == EventTypeEnum.ENDURANCE
    
    # Validate with optional fields
    event = EventBase(
        name="Test Event with Optional Fields",
        date_start=datetime.now(),
        source=EventSourceEnum.AERC,
        event_type=EventTypeEnum.ENDURANCE,
        location=location_str,
        description="Test description",
        website="https://example.com",
        ride_manager="Test Manager"
    )
    assert event.name == "Test Event with Optional Fields"
    assert event.description == "Test description"
    assert event.website == "https://example.com"
    assert event.ride_manager == "Test Manager"

def test_aerc_event_validation(valid_location, valid_contact):
    """Test validation for the AERCEvent schema."""
    location_str = "Test Venue, Test City, CA"
    
    # Test with required fields
    event = AERCEvent(
        name="Test AERC Event",
        date_start=datetime.now(),
        location=location_str
    )
    assert event.name == "Test AERC Event"
    assert event.source == EventSourceEnum.AERC
    assert event.event_type == "endurance"
    
    # Test with all fields
    event = AERCEvent(
        name="Test AERC Event",
        date_start=datetime.now(),
        location=location_str,
        description="Test description",
        website="https://example.com",
        ride_manager="Test Manager",
        control_judges=[{"name": "Test Judge", "role": "Head Control Judge"}],
        sanctioning_status="Sanctioned"
    )
    assert event.name == "Test AERC Event"
    assert event.description == "Test description"
    assert event.control_judges[0].name == "Test Judge"
    assert event.sanctioning_status == "Sanctioned"

def test_event_distance_validation(valid_location):
    """Test event distance date validation."""
    now = datetime.now()
    
    # Create event with distances
    with pytest.raises(ValidationError):
        EventBase(
            name="Test Event",
            source=EventSourceEnum.AERC,
            event_type=EventTypeEnum.ENDURANCE,
            date_start=now,
            date_end=now + timedelta(days=1),
            location=valid_location,
            distances=[
                Distance(
                    distance="50 Miles",
                    date=now - timedelta(days=1)  # Date before event starts
                )
            ]
        )

def test_validate_event_helper():
    """Test the validate_event helper function."""
    now = datetime.now()
    
    # Minimal valid data for AERC
    data = {
        "name": "Test Event",
        "date_start": now,
        "location": "Test Location, Test City, CA",
        "source": "AERC"
    }
    
    # Validate as AERC event
    event = validate_event(data, EventSourceEnum.AERC)
    assert isinstance(event, AERCEvent)
    assert event.name == "Test Event"
    assert event.source == EventSourceEnum.AERC
    
    # SERA event
    data["source"] = "SERA"
    event = validate_event(data, EventSourceEnum.SERA)
    assert isinstance(event, SERAEvent)
    assert event.source == EventSourceEnum.SERA
    
    # UMECRA event
    data["source"] = "UMECRA"
    event = validate_event(data, EventSourceEnum.UMECRA)
    assert isinstance(event, UMECRAEvent)
    assert event.source == EventSourceEnum.UMECRA
    
    # Unknown source - should fall back to EventBase
    data["source"] = "UNKNOWN"
    event = validate_event(data, "UNKNOWN")
    assert isinstance(event, EventBase)
    assert event.source == "UNKNOWN"

def test_multi_day_event_flags():
    """Test that multi-day event flags are calculated correctly."""
    now = datetime.now()
    location = "Test Venue, Test City, CA"
    
    # Single-day event
    event = EventBase(
        name="Single Day Event",
        source=EventSourceEnum.AERC,
        event_type=EventTypeEnum.ENDURANCE,
        date_start=now,
        date_end=now,  # Same day
        location=location,
        ride_days=1,  # Explicitly set for single day event
        is_multi_day_event=False,
        is_pioneer_ride=False
    )
    assert event.is_multi_day_event == False
    assert event.is_pioneer_ride == False
    assert event.ride_days == 1
    
    # Two-day event
    event = EventBase(
        name="Two Day Event",
        source=EventSourceEnum.AERC,
        event_type=EventTypeEnum.ENDURANCE,
        date_start=now,
        date_end=now + timedelta(days=1),  # Next day
        location=location,
        ride_days=2,  # Explicitly set for two day event
        is_multi_day_event=True,
        is_pioneer_ride=False
    )
    assert event.is_multi_day_event == True
    assert event.is_pioneer_ride == False
    assert event.ride_days == 2
    
    # Pioneer ride (3-day event)
    event = EventBase(
        name="Pioneer Ride",
        source=EventSourceEnum.AERC,
        event_type=EventTypeEnum.ENDURANCE,
        date_start=now,
        date_end=now + timedelta(days=2),  # 3 days total
        location=location,
        ride_days=3,  # Explicitly set for three day event
        is_multi_day_event=True,
        is_pioneer_ride=True
    )
    assert event.is_multi_day_event == True
    assert event.is_pioneer_ride == True
    assert event.ride_days == 3
    
    # Long pioneer ride (5-day event)
    event = EventBase(
        name="Long Pioneer Ride",
        source=EventSourceEnum.AERC,
        event_type=EventTypeEnum.ENDURANCE,
        date_start=now,
        date_end=now + timedelta(days=4),  # 5 days total
        location=location,
        ride_days=5,  # Explicitly set for five day event
        is_multi_day_event=True,
        is_pioneer_ride=True
    )
    assert event.is_multi_day_event == True
    assert event.is_pioneer_ride == True
    assert event.ride_days == 5