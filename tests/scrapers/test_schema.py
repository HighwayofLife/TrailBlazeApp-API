"""Tests for shared schema validation module."""

import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError
from scrapers.schema import (
    EventSourceEnum,
    EventTypeEnum,
    ContactInfo,
    Distance,
    Location,
    EventBase,
    AERCEvent,
    validate_event
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
    # Valid location
    location = Location(
        name="Test Venue",
        city="Test City",
        state="CA",
        coordinates=(37.7749, -122.4194)
    )
    assert location.name == "Test Venue"
    
    # Invalid coordinates
    with pytest.raises(ValidationError):
        Location(
            name="Test Venue",
            coordinates=(91, 0)  # Invalid latitude
        )

def test_distance_validation():
    """Test distance validation."""
    now = datetime.now()
    
    # Valid distance
    distance = Distance(
        distance="50 Miles",
        date=now,
        start_time="6:00 AM",
        max_riders=100
    )
    assert distance.distance == "50 Miles"
    
    # Required date field
    with pytest.raises(ValidationError):
        Distance(
            distance="50 Miles",
            start_time="6:00 AM"
        )

def test_event_base_validation(valid_location):
    """Test base event validation."""
    now = datetime.now()
    
    # Valid event
    event = EventBase(
        name="Test Event",
        source=EventSourceEnum.AERC,
        event_type=EventTypeEnum.ENDURANCE,
        date_start=now,
        location=valid_location
    )
    assert event.name == "Test Event"
    assert event.date_end == event.date_start  # Default behavior
    
    # Invalid date range
    with pytest.raises(ValidationError):
        EventBase(
            name="Test Event",
            source=EventSourceEnum.AERC,
            event_type=EventTypeEnum.ENDURANCE,
            date_start=now,
            date_end=now - timedelta(days=1),  # End before start
            location=valid_location
        )

def test_aerc_event_validation(valid_location, valid_contact):
    """Test AERC-specific event validation."""
    now = datetime.now()
    
    # Valid AERC event
    event = AERCEvent(
        name="Test AERC Event",
        source=EventSourceEnum.AERC,
        event_type=EventTypeEnum.ENDURANCE,
        date_start=now,
        location=valid_location,
        control_judges=[valid_contact]
    )
    assert event.name == "Test AERC Event"
    assert len(event.control_judges) == 1

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
    """Test validate_event helper function."""
    now = datetime.now()
    
    # Valid AERC event data
    data = {
        "name": "Test Event",
        "source": "AERC",
        "event_type": "endurance",
        "date_start": now,
        "location": {
            "name": "Test Venue",
            "city": "Test City",
            "state": "CA"
        }
    }
    
    event = validate_event(data, EventSourceEnum.AERC)
    assert isinstance(event, AERCEvent)
    
    # Invalid source
    with pytest.raises(ValueError):
        validate_event(data, "INVALID")