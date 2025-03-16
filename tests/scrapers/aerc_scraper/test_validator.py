"""Tests for AERC validator module."""

import pytest
from datetime import datetime
from scrapers.aerc_scraper.validator import DataValidator
from scrapers.exceptions import ValidationError

@pytest.fixture
def validator():
    """Create validator instance."""
    return DataValidator()

@pytest.fixture
def valid_event_data():
    """Create valid event data fixture."""
    return {
        "name": "Test AERC Event",
        "date_start": "2024-03-15",
        "date_end": "2024-03-16",
        "location": "Test Venue, Test City, CA",
        "ride_manager": "John Doe",
        "ride_manager_email": "john@example.com",
        "ride_manager_phone": "+12345678900",
        "control_judges": [
            "Dr. Smith",
            {
                "name": "Dr. Jones",
                "email": "jones@example.com",
                "role": "Treatment Vet"
            }
        ],
        "distances": [
            "50 Miles",
            {
                "distance": "100 Miles",
                "start_time": "5:00 AM"
            }
        ]
    }

def test_validate_valid_event(validator, valid_event_data):
    """Test validation of a valid event."""
    result = validator.validate_events([valid_event_data])
    
    assert len(result) == 1
    event = result[0]
    
    assert event['name'] == "Test AERC Event"
    assert isinstance(event['date_start'], datetime)
    assert len(event['contacts']) == 3  # Manager + 2 judges
    assert len(event['distances']) == 2
    assert event['source'] == "AERC"
    assert event['event_type'] == "endurance"

def test_validate_missing_required_fields(validator):
    """Test validation with missing required fields."""
    invalid_data = {
        "name": "Test Event",
        # Missing date_start and location
    }
    
    result = validator.validate_events([invalid_data])
    assert len(result) == 0
    assert validator.get_metrics()['invalid'] == 1

def test_validate_date_formats(validator, valid_event_data):
    """Test validation of different date formats."""
    # Test multiple date formats
    date_formats = [
        "2024-03-15",
        "03/15/2024",
        "2024-03-15T08:00:00"
    ]
    
    for date_format in date_formats:
        data = valid_event_data.copy()
        data['date_start'] = date_format
        result = validator.validate_events([data])
        assert len(result) == 1
        assert isinstance(result[0]['date_start'], datetime)

def test_validate_location_parsing(validator, valid_event_data):
    """Test location string parsing."""
    # Full format: Venue, City, State
    data = valid_event_data.copy()
    result = validator.validate_events([data])
    assert len(result) == 1
    assert result[0]['location']['name'] == "Test Venue"
    assert result[0]['location']['city'] == "Test City"
    assert result[0]['location']['state'] == "CA"
    
    # Just venue name
    data['location'] = "Simple Venue"
    result = validator.validate_events([data])
    assert len(result) == 1
    assert result[0]['location']['name'] == "Simple Venue"

def test_validate_contacts_structuring(validator, valid_event_data):
    """Test contact information structuring."""
    result = validator.validate_events([valid_event_data])
    assert len(result) == 1
    
    contacts = result[0]['contacts']
    # Verify ride manager contact
    manager = next(c for c in contacts if c['role'] == 'Ride Manager')
    assert manager['name'] == "John Doe"
    assert manager['email'] == "john@example.com"
    
    # Verify control judges
    judges = [c for c in contacts if c['role'] in ('Control Judge', 'Treatment Vet')]
    assert len(judges) == 2
    assert any(j['name'] == "Dr. Smith" for j in judges)
    assert any(j['name'] == "Dr. Jones" for j in judges)

def test_validate_distances_structuring(validator, valid_event_data):
    """Test distance information structuring."""
    result = validator.validate_events([valid_event_data])
    assert len(result) == 1
    
    distances = result[0]['distances']
    assert len(distances) == 2
    
    # Simple distance string should be structured
    assert any(d['distance'] == "50 Miles" for d in distances)
    # Complex distance object should be preserved
    assert any(
        d['distance'] == "100 Miles" and d['start_time'] == "5:00 AM"
        for d in distances
    )

def test_validate_multiple_events(validator, valid_event_data):
    """Test validation of multiple events."""
    # Create a copy with different name
    second_event = valid_event_data.copy()
    second_event['name'] = "Second Event"
    
    result = validator.validate_events([valid_event_data, second_event])
    assert len(result) == 2
    assert result[0]['name'] != result[1]['name']

def test_validate_metrics(validator, valid_event_data):
    """Test metrics collection during validation."""
    result = validator.validate_events([
        valid_event_data,
        {"name": "Invalid Event"}  # Missing required fields
    ])
    
    metrics = validator.get_metrics()
    assert metrics['validated'] == 1
    assert metrics['invalid'] == 1
    assert metrics['validation_time'] > 0