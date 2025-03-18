"""Tests for the AERC data handler."""

import pytest
from datetime import datetime

from scrapers.aerc_scraper.data_handler import DataHandler
from scrapers.schema import AERCEvent, EventSourceEnum, EventTypeEnum

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
    assert event.location.city == 'Test City'
    assert event.location.state == 'ST'
    assert event.location.country == 'USA'

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
    assert event.location.name == 'Ride Location'
    assert event.location.city == 'Test City'
    assert event.location.state == 'ST'
    
    # Check contact info
    assert len(event.contacts) == 1
    contact = event.contacts[0]
    assert contact.name == 'John Doe'
    assert contact.email == 'john@example.com'
    assert contact.phone == '1234567890'
    assert contact.role == 'Ride Manager'
    
    # Check URLs
    assert str(event.website_url) == 'https://example.com/'
    assert str(event.registration_url) == 'https://example.com/flyer.pdf'
    
    # Check distances
    assert len(event.distances) == 2
    assert event.distances[0].distance == '50'
    assert event.distances[1].distance == '100'

def test_parse_location():
    """Test location string parsing."""
    test_cases = [
        (
            "Ride Name - City, ST",
            {'name': 'Ride Name', 'city': 'City', 'state': 'ST'}
        ),
        (
            "City, State",
            {'name': None, 'city': 'City', 'state': 'State'}
        ),
        (
            "Location Name",
            {'name': 'Location Name', 'city': None, 'state': None}
        ),
        (
            "",
            {'name': None, 'city': None, 'state': None}
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