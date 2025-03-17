"""Tests for the geocode_events.py script."""
import asyncio
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.models import Event
from scripts.geocode_events import geocode_events

@pytest.mark.asyncio
async def test_geocode_events_no_events():
    """Test processing when there are no events to geocode."""
    # Mock the session query to return 0 events
    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.scalar_one.return_value = 0
    mock_session.execute.return_value = mock_result
    
    # Mock the GeocodingEnrichmentService
    mock_service = MagicMock()
    
    with patch('scripts.geocode_events.async_session') as mock_async_session, \
         patch('scripts.geocode_events.GeocodingEnrichmentService') as mock_service_class:
        
        # Configure mocks
        mock_async_session.return_value.__aenter__.return_value = mock_session
        mock_service_class.return_value = mock_service
        
        # Call the function
        await geocode_events()
        
        # Verify the session was queried for events
        assert mock_session.execute.call_count == 1
        
        # Verify no further processing was done
        assert not mock_session.execute.call_count > 1
        assert mock_service.enrich_event.call_count == 0

@pytest.mark.asyncio
async def test_geocode_events_with_events():
    """Test processing events that need geocoding."""
    # Create some test events
    events = [
        Event(id=1, name="Event 1", location="Location 1"),
        Event(id=2, name="Event 2", location="Location 2"),
        Event(id=3, name="Event 3", location="Location 3")
    ]
    
    # Mock the session query to return 3 events
    mock_session = AsyncMock()
    mock_count_result = AsyncMock()
    mock_count_result.scalar_one.return_value = 3
    
    mock_events_result = AsyncMock()
    mock_events_result.scalars.return_value.all.return_value = events
    
    # Configure mock_session.execute to return different results based on call order
    mock_session.execute.side_effect = [mock_count_result, mock_events_result]
    
    # Mock the GeocodingEnrichmentService
    mock_service = MagicMock()
    mock_service.enrich_event = AsyncMock()
    mock_service.enrich_event.side_effect = [True, False, True]  # First and third succeed, second fails
    
    with patch('scripts.geocode_events.async_session') as mock_async_session, \
         patch('scripts.geocode_events.GeocodingEnrichmentService') as mock_service_class:
        
        # Configure mocks
        mock_async_session.return_value.__aenter__.return_value = mock_session
        mock_service_class.return_value = mock_service
        
        # Call the function
        await geocode_events()
        
        # Verify the session was queried for events
        assert mock_session.execute.call_count == 2
        
        # Verify each event was processed
        assert mock_service.enrich_event.call_count == 3
        
        # Verify mock_service.enrich_event was called with each event
        mock_service.enrich_event.assert_any_call(events[0])
        mock_service.enrich_event.assert_any_call(events[1])
        mock_service.enrich_event.assert_any_call(events[2])
        
        # Verify session.commit was called
        mock_session.commit.assert_called_once()

@pytest.mark.asyncio
async def test_geocode_events_with_limit():
    """Test processing events with a limit."""
    # Create some test events
    events = [
        Event(id=1, name="Event 1", location="Location 1"),
        Event(id=2, name="Event 2", location="Location 2")
    ]
    
    # Mock the session query to return 5 events total, but we'll limit to 2
    mock_session = AsyncMock()
    mock_count_result = AsyncMock()
    mock_count_result.scalar_one.return_value = 5
    
    mock_events_result = AsyncMock()
    mock_events_result.scalars.return_value.all.return_value = events
    
    # Configure mock_session.execute to return different results based on call order
    mock_session.execute.side_effect = [mock_count_result, mock_events_result]
    
    # Mock the GeocodingEnrichmentService
    mock_service = MagicMock()
    mock_service.enrich_event = AsyncMock()
    mock_service.enrich_event.side_effect = [True, True]  # Both succeed
    
    with patch('scripts.geocode_events.async_session') as mock_async_session, \
         patch('scripts.geocode_events.GeocodingEnrichmentService') as mock_service_class:
        
        # Configure mocks
        mock_async_session.return_value.__aenter__.return_value = mock_session
        mock_service_class.return_value = mock_service
        
        # Call the function with a limit
        await geocode_events(limit=2)
        
        # Verify the session was queried for events
        assert mock_session.execute.call_count == 2
        
        # Verify each event was processed
        assert mock_service.enrich_event.call_count == 2
        
        # Verify session.commit was called
        mock_session.commit.assert_called_once() 