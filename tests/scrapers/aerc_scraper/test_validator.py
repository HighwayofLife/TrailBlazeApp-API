"""Tests for data validator module."""

import pytest
from datetime import datetime
from scrapers.aerc_scraper.validator import DataValidator, ValidationError

@pytest.fixture
def validator():
    """Create validator instance."""
    return DataValidator()

def test_validate_valid_events(validator, sample_events):
    """Test validation of valid events."""
    valid_events = validator.validate_events(sample_events)
    
    assert len(valid_events) == 2
    assert validator.get_metrics()['events_found'] == 2
    assert validator.get_metrics()['events_valid'] == 2
    assert validator.get_metrics()['validation_errors'] == 0

def test_validate_missing_required_fields(validator):
    """Test validation with missing required fields."""
    invalid_events = [
        {
            # Missing rideName
            "date": "2024-03-15",
            "region": "W",
            "location": "Test Location"
        },
        {
            "rideName": "Test Ride",
            # Missing date
            "region": "W",
            "location": "Test Location"
        }
    ]
    
    valid_events = validator.validate_events(invalid_events)
    assert len(valid_events) == 0
    assert validator.get_metrics()['validation_errors'] == 2

def test_validate_invalid_dates(validator):
    """Test validation of invalid dates."""
    events = [
        {
            "rideName": "Test Ride",
            "date": "invalid-date",
            "region": "W",
            "location": "Test Location"
        },
        {
            "rideName": "Test Ride 2",
            "date": "2024-13-45",  # Invalid month/day
            "region": "W",
            "location": "Test Location"
        }
    ]
    
    valid_events = validator.validate_events(events)
    assert len(valid_events) == 0
    assert validator.get_metrics()['validation_errors'] == 2

def test_validate_duplicate_events(validator):
    """Test handling of duplicate events."""
    events = [
        {
            "rideName": "Duplicate Ride",
            "date": "2024-03-15",
            "region": "W",
            "location": "Same Location"
        },
        {
            "rideName": "Duplicate Ride",
            "date": "2024-03-15",
            "region": "W",
            "location": "Same Location"
        }
    ]
    
    valid_events = validator.validate_events(events)
    assert len(valid_events) == 1
    assert validator.get_metrics()['events_duplicate'] == 1

def test_validate_phone_numbers(validator):
    """Test validation of phone numbers."""
    events = [
        {
            "rideName": "Test Ride",
            "date": "2024-03-15",
            "region": "W",
            "location": "Test Location",
            "rideManagerContact": {
                "phone": "123-456-7890"  # Valid format
            }
        },
        {
            "rideName": "Test Ride 2",
            "date": "2024-03-15",
            "region": "W",
            "location": "Test Location",
            "rideManagerContact": {
                "phone": "invalid"  # Invalid format
            }
        }
    ]
    
    valid_events = validator.validate_events(events)
    assert len(valid_events) == 1
    assert validator.get_metrics()['validation_errors'] == 1

def test_validate_map_links(validator):
    """Test validation of Google Maps links."""
    events = [
        {
            "rideName": "Test Ride",
            "date": "2024-03-15",
            "region": "W",
            "location": "Test Location",
            "mapLink": "https://maps.google.com/valid"  # Valid format
        },
        {
            "rideName": "Test Ride 2",
            "date": "2024-03-15",
            "region": "W",
            "location": "Test Location",
            "mapLink": "https://invalid-map-link.com"  # Invalid format
        }
    ]
    
    valid_events = validator.validate_events(events)
    assert len(valid_events) == 1
    assert validator.get_metrics()['validation_errors'] == 1

def test_validate_empty_events(validator):
    """Test validation of empty events list."""
    valid_events = validator.validate_events([])
    assert len(valid_events) == 0
    assert validator.get_metrics()['events_found'] == 0

def test_validate_tag_generation(validator):
    """Test automatic tag generation."""
    event = {
        "rideName": "Test Ride",
        "date": "2024-03-15",
        "region": "W",
        "location": "Test Location"
    }
    
    valid_events = validator.validate_events([event])
    assert len(valid_events) == 1
    assert 'tag' in valid_events[0]
    assert isinstance(valid_events[0]['tag'], int)

def test_validate_location_cleaning(validator):
    """Test location field cleaning."""
    events = [
        {
            "rideName": "Test Ride",
            "date": "2024-03-15",
            "region": "W",
            "location": "tba"
        },
        {
            "rideName": "Test Ride 2",
            "date": "2024-03-15",
            "region": "W",
            "location": "To Be Announced"
        }
    ]
    
    valid_events = validator.validate_events(events)
    assert len(valid_events) == 2
    assert all(e['location'] == 'Location TBA' for e in valid_events)

def test_metrics_accuracy(validator):
    """Test accuracy of metrics collection."""
    events = [
        {
            "rideName": "Valid Ride",
            "date": "2024-03-15",
            "region": "W",
            "location": "Location 1"
        },
        {
            "rideName": "Invalid Ride",
            "date": "invalid",
            "region": "W",
            "location": "Location 2"
        },
        {
            "rideName": "Valid Ride",  # Duplicate
            "date": "2024-03-15",
            "region": "W",
            "location": "Location 1"
        }
    ]
    
    validator.validate_events(events)
    metrics = validator.get_metrics()
    
    assert metrics['events_found'] == 3
    assert metrics['events_valid'] == 1
    assert metrics['events_duplicate'] == 1
    assert metrics['validation_errors'] == 1