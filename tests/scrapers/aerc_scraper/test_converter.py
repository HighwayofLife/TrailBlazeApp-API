"""Tests for data converter module."""

import pytest
from datetime import datetime
from scrapers.aerc_scraper.converter import DataConverter
from scrapers.aerc_scraper.exceptions import DataExtractionError
from app.schemas.event import EventCreate

@pytest.fixture
def converter():
    """Create converter instance."""
    return DataConverter()

def test_convert_valid_events(converter, sample_events):
    """Test conversion of valid events."""
    db_events = converter.convert_to_db_events(sample_events)
    
    assert len(db_events) == 2
    assert all(isinstance(event, EventCreate) for event in db_events)
    assert converter.get_metrics()['converted'] == 2
    assert converter.get_metrics()['conversion_errors'] == 0

def test_convert_event_dates(converter):
    """Test date conversion and multi-day event handling."""
    events = [
        {
            "rideName": "Multi-day Event",
            "date": "2024-03-15",
            "region": "W",
            "location": "Test Location",
            "distances": [
                {
                    "distance": "50",
                    "date": "2024-03-15",
                    "startTime": "6:30 AM"
                },
                {
                    "distance": "100",
                    "date": "2024-03-16",  # Next day
                    "startTime": "5:30 AM"
                }
            ]
        }
    ]
    
    db_events = converter.convert_to_db_events(events)
    assert len(db_events) == 1
    
    event = db_events[0]
    assert event.date_start == datetime.strptime("2024-03-15", "%Y-%m-%d")
    assert event.date_end == datetime.strptime("2024-03-16", "%Y-%m-%d")
    assert len(event.distances) == 2

def test_convert_contact_info(converter):
    """Test contact information formatting."""
    events = [
        {
            "rideName": "Test Event",
            "date": "2024-03-15",
            "region": "W",
            "location": "Test Location",
            "rideManager": "John Doe",
            "rideManagerContact": {
                "email": "john@example.com",
                "phone": "123-456-7890"
            }
        }
    ]
    
    db_events = converter.convert_to_db_events(events)
    event = db_events[0]
    
    assert "Ride Manager: John Doe" in event.description
    assert "Email: john@example.com" in event.description
    assert "Phone: 123-456-7890" in event.description

def test_convert_control_judges(converter):
    """Test control judges formatting."""
    events = [
        {
            "rideName": "Test Event",
            "date": "2024-03-15",
            "region": "W",
            "location": "Test Location",
            "controlJudges": [
                {"role": "Head Control Judge", "name": "Alice Smith"},
                {"role": "Treatment Vet", "name": "Bob Jones"}
            ]
        }
    ]
    
    db_events = converter.convert_to_db_events(events)
    event = db_events[0]
    
    assert "Head Control Judge: Alice Smith" in event.additional_info
    assert "Treatment Vet: Bob Jones" in event.additional_info

def test_convert_missing_optional_fields(converter):
    """Test conversion with missing optional fields."""
    events = [
        {
            "rideName": "Minimal Event",
            "date": "2024-03-15",
            "region": "W",
            "location": "Test Location"
        }
    ]
    
    db_events = converter.convert_to_db_events(events)
    event = db_events[0]
    
    assert event.description is None
    assert event.additional_info is None
    assert event.distances == []
    assert event.map_url is None
    assert event.has_intro_ride is False

def test_convert_malformed_dates(converter):
    """Test handling of malformed dates."""
    events = [
        {
            "rideName": "Test Event",
            "date": "invalid-date",
            "region": "W",
            "location": "Test Location"
        }
    ]
    
    db_events = converter.convert_to_db_events(events)
    assert len(db_events) == 0
    assert converter.get_metrics()['conversion_errors'] == 1

def test_convert_empty_events(converter):
    """Test conversion of empty events list."""
    db_events = converter.convert_to_db_events([])
    assert len(db_events) == 0
    assert converter.get_metrics()['converted'] == 0

def test_convert_preserves_external_id(converter):
    """Test external ID preservation."""
    events = [
        {
            "rideName": "Test Event",
            "date": "2024-03-15",
            "region": "W",
            "location": "Test Location",
            "tag": 12345
        }
    ]
    
    db_events = converter.convert_to_db_events(events)
    assert db_events[0].external_id == "12345"

def test_convert_handles_unicode(converter):
    """Test handling of Unicode characters."""
    events = [
        {
            "rideName": "Test Event – with em dash",
            "date": "2024-03-15",
            "region": "W",
            "location": "Test Location 🏃‍♂️"
        }
    ]
    
    db_events = converter.convert_to_db_events(events)
    assert len(db_events) == 1
    assert "Test Event – with em dash" == db_events[0].name
    assert "Test Location 🏃‍♂️" == db_events[0].location

def test_metrics_accuracy(converter):
    """Test accuracy of metrics collection."""
    events = [
        {
            "rideName": "Valid Event",
            "date": "2024-03-15",
            "region": "W",
            "location": "Location 1"
        },
        {
            "rideName": "Invalid Event",
            "date": "invalid",
            "region": "W",
            "location": "Location 2"
        }
    ]
    
    converter.convert_to_db_events(events)
    metrics = converter.get_metrics()
    
    assert metrics['converted'] == 1
    assert metrics['conversion_errors'] == 1