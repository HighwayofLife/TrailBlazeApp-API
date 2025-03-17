"""Tests for cancelled event detection in the AERC scraper."""

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
def cancelled_events():
    """Sample cancelled event data in various formats."""
    return [
        {
            "rideName": "** CANCELLED ** Test Ride 1",
            "date": "2024-06-15",
            "location": "Test Location 1"
        },
        {
            "rideName": "Test Ride 2 (Cancelled)",
            "date": "2024-07-20",
            "location": "Test Location 2"
        },
        {
            "rideName": "Test Ride 3 - CANCELED",
            "date": "2024-08-10",
            "location": "Test Location 3"
        },
        {
            "rideName": "CANCELLED: Test Ride 4",
            "date": "2024-09-05",
            "location": "Test Location 4"
        }
    ]

@pytest.fixture
def regular_events():
    """Sample regular (not cancelled) event data."""
    return [
        {
            "rideName": "Regular Test Ride 1",
            "date": "2024-06-15",
            "location": "Test Location 1"
        },
        {
            "rideName": "Test Ride with event description",
            "date": "2024-07-20",
            "location": "Test Location 2"
        }
    ]

def test_cancelled_event_detection(client, cancelled_events):
    """Test that cancelled events are properly detected and flagged."""
    # This test will fail until the cancelled event detection is implemented
    mapped_events = client._map_fields(cancelled_events)
    
    # Check that all events are marked as cancelled
    for event in mapped_events:
        assert event.get('is_canceled') is True, f"Event '{event['name']}' should be marked as cancelled"
        
    # Check specific cancellation patterns
    assert mapped_events[0].get('is_canceled') is True  # ** CANCELLED **
    assert mapped_events[1].get('is_canceled') is True  # (Cancelled)
    assert mapped_events[2].get('is_canceled') is True  # - CANCELED
    assert mapped_events[3].get('is_canceled') is True  # CANCELLED:

def test_regular_event_detection(client, regular_events):
    """Test that regular events are not marked as cancelled."""
    # This test will fail until the cancelled event detection is implemented
    mapped_events = client._map_fields(regular_events)
    
    # Check that no events are marked as cancelled
    for event in mapped_events:
        assert event.get('is_canceled') is not True, f"Event '{event['name']}' should not be marked as cancelled"

def test_mixed_events(client, cancelled_events, regular_events):
    """Test a mix of cancelled and regular events."""
    # This test will fail until the cancelled event detection is implemented
    mixed_events = cancelled_events + regular_events
    mapped_events = client._map_fields(mixed_events)
    
    # Check cancelled events
    for i in range(len(cancelled_events)):
        assert mapped_events[i].get('is_canceled') is True, f"Cancelled event '{mapped_events[i]['name']}' not detected"
    
    # Check regular events
    for i in range(len(cancelled_events), len(mixed_events)):
        assert mapped_events[i].get('is_canceled') is not True, f"Regular event '{mapped_events[i]['name']}' incorrectly marked as cancelled" 