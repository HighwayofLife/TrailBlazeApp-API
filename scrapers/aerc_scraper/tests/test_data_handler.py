"""Tests for the AERC data handler."""

import pytest
from datetime import datetime

from scrapers.aerc_scraper.data_handler import DataHandler
from app.schemas.event import AERCEvent, EventSourceEnum, EventTypeEnum

def test_transform_and_validate_minimal():
    """Test transformation of minimal valid event data."""
    raw_event = {
        'name': 'Test Ride',
        'date_start': '2024-03-20',
        'location': 'Test City, ST',
    }
    
    event = DataHandler.transform_and_validate(raw_event)
    
    assert isinstance(event, AERCEvent)
    assert event.name == 'Test Ride'
    assert event.date_start == datetime(2024, 3, 20)
    assert event.source == EventSourceEnum.AERC
    assert event.event_type == EventTypeEnum.ENDURANCE
    assert event.location == 'Test City, ST'
    # Check location_details field instead
    assert event.location_details.city == 'Test City'
    assert event.location_details.state == 'ST'
    assert event.location_details.country == 'USA'

def test_transform_and_validate_full():
    """Test transformation of complete event data."""
    raw_event = {
        'name': 'Full Test Ride',
        'date_start': '2024-03-20',
        'location': 'Ride Location - Test City, ST',
        'region': 'Mountain',
        'ride_manager': 'John Doe',
        'ride_manager_contact': {
            'email': 'john@example.com',
            'phone': '1234567890'
        },
        'website': 'example.com',
        'flyer_url': 'https://example.com/flyer.pdf',
        'distances': [
            {'distance': '50'},
            {'distance': '100'}
        ]
    }
    
    event = DataHandler.transform_and_validate(raw_event)
    
    assert isinstance(event, AERCEvent)
    assert event.name == 'Full Test Ride'
    assert event.date_start == datetime(2024, 3, 20)
    assert event.source == EventSourceEnum.AERC
    assert event.event_type == EventTypeEnum.ENDURANCE
    assert event.region == 'Mountain'
    
    # Check location parsing
    assert event.location == 'Ride Location - Test City, ST'
    # Check location_details field instead
    assert event.location_details is not None
    assert event.location_details.city == 'Test City'
    assert event.location_details.state == 'ST'
    
    # Check manager info
    assert event.ride_manager == 'John Doe'
    assert event.manager_email == 'john@example.com'
    assert event.manager_phone == '1234567890'
    
    # Check URLs
    assert event.website == 'https://example.com/'
    assert event.flyer_url == 'https://example.com/flyer.pdf'
    
    # Check distances
    assert len(event.distances) == 2
    assert event.distances[0].distance == '50'
    assert event.distances[1].distance == '100'

def test_parse_location():
    """Test location string parsing."""
    test_cases = [
        (
            "Ride Name - City, ST",
            {'city': 'City', 'state': 'ST', 'country': 'USA'}
        ),
        (
            "City, State",
            {'city': 'City', 'state': 'State', 'country': 'USA'}
        ),
        (
            "Location Name",
            {'city': 'Location Name', 'country': 'USA'}
        ),
        (
            "",
            {}
        ),
    ]
    
    for input_str, expected in test_cases:
        result = DataHandler._parse_location(input_str)
        assert result == expected, f"Failed for input: {input_str}"

def test_validate_url():
    """Test URL validation and normalization."""
    test_cases = [
        ('https://example.com', 'https://example.com/'),
        ('http://example.com', 'http://example.com/'),
        ('example.com', 'https://example.com/'),
        ('', None),
        (None, None),
        ('not-a-url', None),
    ]
    
    for input_url, expected in test_cases:
        result = DataHandler._validate_url(input_url)
        if expected is None:
            assert result is None, f"Failed for input: {input_url}"
        else:
            assert str(result) == expected, f"Failed for input: {input_url}" 