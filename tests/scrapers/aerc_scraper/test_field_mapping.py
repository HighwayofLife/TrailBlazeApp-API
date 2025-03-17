"""Tests for field mapping functionality in GeminiClient."""

import pytest
from unittest.mock import MagicMock

from scrapers.aerc_scraper.gemini_client import GeminiClient

@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = MagicMock()
    settings.gemini_api_key = "test_key"
    settings.primary_model = "gemini-2.0-flash-lite"
    settings.fallback_model = "gemini-2.0-flash"
    settings.temperature = 0.2
    return settings

@pytest.fixture
def client(mock_settings):
    """Create GeminiClient instance with mock settings."""
    return GeminiClient(mock_settings)

@pytest.fixture
def sample_event():
    """Sample event data in AI extraction format."""
    return {
        "rideName": "Test Ride",
        "date": "2024-06-15",
        "region": "NW",
        "location": "Test Location, City, ST",
        "distances": [
            {
                "distance": "50 Miles",
                "date": "2024-06-15",
                "startTime": "6:00 AM"
            },
            {
                "distance": "25 Miles",
                "date": "2024-06-16",
                "startTime": "7:00 AM"
            }
        ],
        "rideManager": "John Doe",
        "rideManagerContact": {
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "555-123-4567"
        },
        "controlJudges": [
            {
                "role": "Head Vet",
                "name": "Dr. Smith"
            },
            {
                "role": "Treatment Vet",
                "name": "Dr. Jones"
            }
        ],
        "mapLink": "https://maps.example.com/location",
        "hasIntroRide": True,
        "tag": 12345
    }

def test_field_mapping(client, sample_event):
    """Test field mapping functionality."""
    # Test mapping a single event
    mapped_events = client._map_fields([sample_event])
    assert len(mapped_events) == 1
    
    mapped = mapped_events[0]
    
    # Verify basic field mapping
    assert mapped['name'] == "Test Ride"
    assert mapped['date_start'] == "2024-06-15"
    assert mapped['location'] == "Test Location, City, ST"
    assert mapped['region'] == "NW"
    assert mapped['ride_manager'] == "John Doe"
    
    # Verify contact information mapping
    assert mapped['manager_email'] == "john@example.com"
    assert mapped['manager_phone'] == "555-123-4567"
    assert "Name: John Doe" in mapped['manager_contact']
    assert "Email: john@example.com" in mapped['manager_contact']
    assert "Phone: 555-123-4567" in mapped['manager_contact']
    
    # Verify judges mapping
    assert len(mapped['judges']) == 2
    assert "Head Vet: Dr. Smith" in mapped['judges']
    assert "Treatment Vet: Dr. Jones" in mapped['judges']
    
    # Verify distances mapping
    assert len(mapped['distances']) == 2
    assert "50 Miles" in mapped['distances']
    assert "25 Miles" in mapped['distances']
    
    # Verify event details mapping
    assert mapped['event_details']['distances'] == sample_event['distances']
    assert mapped['event_details']['hasIntroRide'] == True
    
    # Verify date_end is set to the latest distance date
    assert mapped['date_end'] == "2024-06-16"
    
    # Verify other fields
    assert mapped['map_link'] == "https://maps.example.com/location"
    assert mapped['external_id'] == "12345"
    assert mapped['event_type'] == "endurance"
    assert mapped['source'] == "AERC"

def test_field_mapping_empty_list(client):
    """Test field mapping with an empty list."""
    assert client._map_fields([]) == []

def test_field_mapping_minimal_event(client):
    """Test field mapping with minimal event data."""
    minimal_event = {
        "rideName": "Minimal Ride",
        "date": "2024-07-01",
        "location": "Somewhere"
    }
    
    mapped_minimal = client._map_fields([minimal_event])[0]
    assert mapped_minimal['name'] == "Minimal Ride"
    assert mapped_minimal['date_start'] == "2024-07-01"
    assert mapped_minimal['location'] == "Somewhere"
    assert 'date_end' not in mapped_minimal  # No distances to set end date 