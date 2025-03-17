"""Tests for the enrich_website_flyer.py script."""
import asyncio
from datetime import datetime, timedelta
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.models import Event
from scripts.enrich_website_flyer import enrich_website_flyer, get_events_needing_enrichment

@pytest.mark.asyncio
async def test_get_events_needing_enrichment():
    """Test getting events that need website/flyer enrichment."""
    # Create some test events
    events = [
        Event(id=1, name="Event 1", website_url="https://example.com/1"),
        Event(id=2, name="Event 2", website_url="https://example.com/2")
    ]
    
    # Mock the session query
    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.scalars.return_value.all.return_value = events
    mock_session.execute.return_value = mock_result
    
    # Call the function
    result = await get_events_needing_enrichment(mock_session)
    
    # Verify the result
    assert result == events
    
    # Verify the session was queried
    assert mock_session.execute.call_count == 1

@pytest.mark.asyncio
async def test_enrich_website_flyer_no_events_with_url():
    """Test processing when there are no events with website URLs."""
    # Mock the session query to return 0 events
    mock_session = AsyncMock()
    mock_count_result = AsyncMock()
    mock_count_result.scalar_one.return_value = 0
    mock_session.execute.return_value = mock_count_result
    
    # Mock the WebsiteFlyerEnrichmentService
    mock_service = MagicMock()
    mock_service.close = AsyncMock()
    
    with patch('scripts.enrich_website_flyer.async_session') as mock_async_session, \
         patch('scripts.enrich_website_flyer.WebsiteFlyerEnrichmentService') as mock_service_class:
        
        # Configure mocks
        mock_async_session.return_value.__aenter__.return_value = mock_session
        mock_service_class.return_value = mock_service
        
        # Call the function
        result = await enrich_website_flyer()
        
        # Verify the result
        assert result["total_processed"] == 0
        assert result["total_enriched"] == 0
        assert result["success_rate"] == 0
        
        # Verify the session was queried for events
        assert mock_session.execute.call_count == 1
        
        # Verify service.close was called
        mock_service.close.assert_called_once()

@pytest.mark.asyncio
async def test_enrich_website_flyer_with_events():
    """Test processing events that need website/flyer enrichment."""
    # Create some test events
    events = [
        Event(id=1, name="Event 1", website_url="https://example.com/1"),
        Event(id=2, name="Event 2", website_url="https://example.com/2"),
        Event(id=3, name="Event 3", website_url="https://example.com/3")
    ]
    
    # Mock the session query
    mock_session = AsyncMock()
    mock_count_result = AsyncMock()
    mock_count_result.scalar_one.return_value = 3
    
    # Mock the get_events_needing_enrichment function
    mock_get_events = AsyncMock()
    mock_get_events.return_value = events
    
    # Configure mock_session.execute to return the count
    mock_session.execute.return_value = mock_count_result
    
    # Mock the WebsiteFlyerEnrichmentService
    mock_service = MagicMock()
    mock_service.enrich_event = AsyncMock()
    mock_service.enrich_event.side_effect = [True, False, True]  # First and third succeed, second fails
    mock_service.close = AsyncMock()
    
    with patch('scripts.enrich_website_flyer.async_session') as mock_async_session, \
         patch('scripts.enrich_website_flyer.WebsiteFlyerEnrichmentService') as mock_service_class, \
         patch('scripts.enrich_website_flyer.get_events_needing_enrichment', mock_get_events):
        
        # Configure mocks
        mock_async_session.return_value.__aenter__.return_value = mock_session
        mock_service_class.return_value = mock_service
        
        # Call the function
        result = await enrich_website_flyer()
        
        # Verify the result
        assert result["total_processed"] == 3
        assert result["total_enriched"] == 2
        assert result["success_rate"] == 2/3 * 100
        
        # Verify the session was queried for events count
        assert mock_session.execute.call_count == 1
        
        # Verify get_events_needing_enrichment was called
        mock_get_events.assert_called_once()
        
        # Verify each event was processed
        assert mock_service.enrich_event.call_count == 3
        
        # Verify mock_service.enrich_event was called with each event
        mock_service.enrich_event.assert_any_call(events[0])
        mock_service.enrich_event.assert_any_call(events[1])
        mock_service.enrich_event.assert_any_call(events[2])
        
        # Verify session.commit was called
        mock_session.commit.assert_called_once()
        
        # Verify service.close was called
        mock_service.close.assert_called_once()

@pytest.mark.asyncio
async def test_enrich_website_flyer_with_limit():
    """Test processing events with a limit."""
    # Create some test events
    events = [
        Event(id=1, name="Event 1", website_url="https://example.com/1"),
        Event(id=2, name="Event 2", website_url="https://example.com/2")
    ]
    
    # Mock the session query
    mock_session = AsyncMock()
    mock_count_result = AsyncMock()
    mock_count_result.scalar_one.return_value = 5  # 5 total events with URLs
    
    # Mock the get_events_needing_enrichment function
    mock_get_events = AsyncMock()
    mock_get_events.return_value = events
    
    # Configure mock_session.execute to return the count
    mock_session.execute.return_value = mock_count_result
    
    # Mock the WebsiteFlyerEnrichmentService
    mock_service = MagicMock()
    mock_service.enrich_event = AsyncMock()
    mock_service.enrich_event.side_effect = [True, True]  # Both succeed
    mock_service.close = AsyncMock()
    
    with patch('scripts.enrich_website_flyer.async_session') as mock_async_session, \
         patch('scripts.enrich_website_flyer.WebsiteFlyerEnrichmentService') as mock_service_class, \
         patch('scripts.enrich_website_flyer.get_events_needing_enrichment', mock_get_events):
        
        # Configure mocks
        mock_async_session.return_value.__aenter__.return_value = mock_session
        mock_service_class.return_value = mock_service
        
        # Call the function with a limit
        result = await enrich_website_flyer(limit=2)
        
        # Verify the result
        assert result["total_processed"] == 2
        assert result["total_enriched"] == 2
        assert result["success_rate"] == 100.0
        
        # Verify the session was queried for events count
        assert mock_session.execute.call_count == 1
        
        # Verify get_events_needing_enrichment was called with the right parameters
        mock_get_events.assert_called_once()
        assert mock_get_events.call_args[0][1] <= 2  # batch_size parameter
        
        # Verify each event was processed
        assert mock_service.enrich_event.call_count == 2
        
        # Verify session.commit was called
        mock_session.commit.assert_called_once()
        
        # Verify service.close was called
        mock_service.close.assert_called_once()

@pytest.mark.asyncio
async def test_enrich_website_flyer_error_handling():
    """Test error handling during website/flyer enrichment."""
    # Mock the session query
    mock_session = AsyncMock()
    mock_count_result = AsyncMock()
    mock_count_result.scalar_one.return_value = 3
    
    # Mock the get_events_needing_enrichment function to raise an exception
    mock_get_events = AsyncMock()
    mock_get_events.side_effect = Exception("Test error")
    
    # Configure mock_session.execute to return the count
    mock_session.execute.return_value = mock_count_result
    
    # Mock the WebsiteFlyerEnrichmentService
    mock_service = MagicMock()
    mock_service.close = AsyncMock()
    
    with patch('scripts.enrich_website_flyer.async_session') as mock_async_session, \
         patch('scripts.enrich_website_flyer.WebsiteFlyerEnrichmentService') as mock_service_class, \
         patch('scripts.enrich_website_flyer.get_events_needing_enrichment', mock_get_events):
        
        # Configure mocks
        mock_async_session.return_value.__aenter__.return_value = mock_session
        mock_service_class.return_value = mock_service
        
        # Call the function and check that it raises the exception
        with pytest.raises(Exception) as exc_info:
            await enrich_website_flyer()
        
        # Verify the error message
        assert "Test error" in str(exc_info.value)
        
        # Verify service.close was called even though an error occurred
        mock_service.close.assert_called_once() 