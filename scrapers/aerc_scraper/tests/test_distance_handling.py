import pytest
import asyncio
import sys
import os
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

# Add the parent directory to the path so we can import the schema module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from scrapers.aerc_scraper.parser_v2.html_parser import HTMLParser
from scrapers.aerc_scraper.data_handler import DataHandler
from scrapers.schema import AERCEvent, EventSourceEnum, EventTypeEnum, Distance

# Sample HTML with distance and time information
SAMPLE_HTML = """
<div class="calendarRow">
    <span class="rideName">Test Event</span>
    <span class="rideDate">01/15/2023</span>
    <span class="rideLocation">Test Location, CA</span>
    <div>
        <span>25/50 miles on Jan 15 starting at 7:00am</span>
    </div>
    <div>
        <span>Ride Manager: Test Manager</span>
    </div>
</div>
"""

# Test for distance extraction in the HTML parser
def test_extract_distances():
    parser = HTMLParser()
    soup = parser._extract_distances = MagicMock(return_value=[
        {'distance': '25 miles'},
        {'distance': '50 miles'}
    ])
    
    events = parser.parse_html(SAMPLE_HTML)
    assert len(events) > 0
    
    # Verify parser called _extract_distances
    assert parser._extract_distances.called
    
    # Reset the mock for a real test
    parser._extract_distances.reset_mock()
    
    # Test with actual implementation
    parser = HTMLParser()
    events = parser.parse_html(SAMPLE_HTML)
    
    assert len(events) > 0
    event = events[0]
    assert 'distances' in event
    assert len(event['distances']) > 0
    
    # Validate that distances were properly extracted
    distances = event['distances']
    assert any('25' in d['distance'] for d in distances) or any('50' in d['distance'] for d in distances)

# Test for distance transformation in the data handler
def test_transform_distances():
    raw_event = {
        'name': 'Test Event',
        'date_start': '2023-01-15',
        'region': 'Test Region',
        'location': 'Test Location, CA',
        'distances': [
            {'distance': '25 miles'},
            {'distance': '50 miles', 'start_time': '7:00 AM'}
        ],
        'ride_manager': 'Test Manager'
    }
    
    # Transform raw event to AERCEvent
    aerc_event = DataHandler.transform_and_validate(raw_event)
    
    # Verify transformation
    assert isinstance(aerc_event, AERCEvent)
    assert len(aerc_event.distances) == 2
    
    # Check that both distances are present
    distances = [d.distance for d in aerc_event.distances]
    assert '25 miles' in distances
    assert '50 miles' in distances
    
    # Check that start time is maintained when provided
    for distance in aerc_event.distances:
        if distance.distance == '50 miles':
            assert distance.start_time == '7:00 AM'

# Test the complete flow from raw event to EventCreate for database storage
def test_distance_to_event_create():
    raw_event = {
        'name': 'Test Event',
        'date_start': '2023-01-15',
        'region': 'Test Region',
        'location': 'Test Location, CA',
        'distances': [
            {'distance': '25 miles'},
            {'distance': '50 miles', 'start_time': '7:00 AM'}
        ],
        'ride_manager': 'Test Manager'
    }
    
    # Transform raw event to AERCEvent
    aerc_event = DataHandler.transform_and_validate(raw_event)
    
    # Convert to EventCreate
    event_create = DataHandler.to_event_create(aerc_event)
    
    # Verify distance strings are properly formatted for database
    assert event_create.distances is not None
    assert len(event_create.distances) == 2
    assert '25 miles' in event_create.distances
    assert '50 miles' in event_create.distances

# Test for improved distance extraction with start_time
def test_extract_distances_with_start_time():
    # Create a patched version of the HTML parser with improved _extract_distances
    with patch('scrapers.aerc_scraper.parser_v2.html_parser.HTMLParser._extract_distances') as mock_extract:
        # Mock improved extraction that includes start_time
        mock_extract.return_value = [
            {'distance': '25 miles', 'start_time': '6:30 AM'},
            {'distance': '50 miles', 'start_time': '7:00 AM'}
        ]
        
        parser = HTMLParser()
        events = parser.parse_html(SAMPLE_HTML)
        
        assert len(events) > 0
        event = events[0]
        
        # Verify distances have start_time
        assert all('start_time' in d for d in event['distances'])

# Database integration test - simulate storing an event and retrieving it
@pytest.mark.asyncio
async def test_database_storage():
    # Mock database session
    mock_db = AsyncMock()
    
    # Mock CRUD functions
    with patch('app.crud.event.create_event') as mock_create, \
         patch('app.crud.event.get_events') as mock_get_events:
        
        # Prepare test data
        raw_event = {
            'name': 'Test Event',
            'date_start': '2023-01-15',
            'region': 'Test Region',
            'location': 'Test Location, CA',
            'distances': [
                {'distance': '25 miles', 'start_time': '6:30 AM'},
                {'distance': '50 miles', 'start_time': '7:00 AM'}
            ],
            'ride_manager': 'Test Manager'
        }
        
        # Transform to AERCEvent
        aerc_event = DataHandler.transform_and_validate(raw_event)
        
        # Convert to EventCreate
        event_create = DataHandler.to_event_create(aerc_event)
        
        # Mock successful database storage
        mock_create.return_value = MagicMock(id=1)
        mock_get_events.return_value = []
        
        # Import here to avoid circular imports in test
        from scrapers.aerc_scraper.database import DatabaseHandler
        
        # Store the event
        db_handler = DatabaseHandler()
        await db_handler.store_events([event_create], mock_db)
        
        # Verify event was stored with correct data
        mock_create.assert_called_once()
        
        # Extract the actual event create object passed to create_event
        stored_event = mock_create.call_args[0][1]
        
        # Verify distances made it to the database
        assert len(stored_event.distances) == 2
        assert '25 miles' in stored_event.distances
        assert '50 miles' in stored_event.distances 