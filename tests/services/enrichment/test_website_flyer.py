"""Tests for the WebsiteFlyerEnrichmentService class."""
import datetime
import json
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest
from aiohttp import ClientSession
from google import genai

from app.models import Event
from app.services.ai_service import AIService
from app.services.enrichment.website_flyer import WebsiteFlyerEnrichmentService


@pytest.fixture
def mock_ai_service():
    """Fixture for mocking AIService."""
    with patch("app.services.enrichment.website_flyer.AIService") as mock_service:
        # Create a mock service with AsyncMock for async methods
        service_instance = MagicMock()
        service_instance.generate_text = AsyncMock()
        mock_service.return_value = service_instance
        yield service_instance


@pytest.fixture
def mock_session():
    """Fixture for mocking ClientSession."""
    with patch("aiohttp.ClientSession") as mock_client_session:
        session_instance = MagicMock()
        session_instance.get = AsyncMock()
        mock_client_session.return_value = session_instance
        
        # Create a context manager mock for the get method
        response_mock = AsyncMock()
        response_mock.__aenter__ = AsyncMock(return_value=response_mock)
        response_mock.__aexit__ = AsyncMock()
        response_mock.status = 200
        response_mock.text = AsyncMock(return_value="<html><body>Test Content</body></html>")
        
        # Set up the get method to return the response mock
        session_instance.get.return_value = response_mock
        
        yield session_instance


@pytest.fixture
def enrichment_service(mock_ai_service, mock_session):
    """Fixture for creating a WebsiteFlyerEnrichmentService with mocked dependencies."""
    service = WebsiteFlyerEnrichmentService()
    service.ai_service = mock_ai_service
    # Don't replace session directly as it starts as None
    service._get_session = AsyncMock(return_value=mock_session)
    return service


@pytest.mark.asyncio
async def test_enrich_event_no_website_url(enrichment_service):
    """Test enriching an event with no website URL."""
    # Create an event with no website_url
    event = MagicMock(spec=Event)
    event.id = 1
    event.name = "Test Event"
    event.website_url = None  # This is what's used in the code, not website
    
    # Call the enrich_event method
    result = await enrichment_service.enrich_event(event)
    
    # Verify the result is False (no enrichment occurred)
    assert result is False
    
    # Verify no fetch_url_content call was made
    enrichment_service._get_session.assert_not_called()


@pytest.mark.asyncio
async def test_enrich_event_already_checked_recently(enrichment_service):
    """Test enriching an event that was checked recently."""
    # Create an event with a website_url and a recent last_website_check_at
    event = MagicMock(spec=Event)
    event.id = 1
    event.name = "Test Event"
    event.website_url = "https://example.com"  # This is what's used in the code, not website
    event.last_website_check_at = datetime.datetime.now() - datetime.timedelta(hours=1)
    
    # Mock the _should_update_event method to return False
    with patch.object(enrichment_service, '_should_update_event', return_value=False):
        # Call the enrich_event method
        result = await enrichment_service.enrich_event(event)
    
    # Verify the result is True (no error occurred)
    assert result is True
    
    # Verify no fetch_url_content call was made
    enrichment_service._get_session.assert_not_called()


@pytest.mark.asyncio
async def test_enrich_event_fetch_url_failure(enrichment_service, mock_session):
    """Test enriching an event where fetch_url_content fails."""
    # Create an event with a website_url and no last_website_check_at
    event = MagicMock(spec=Event)
    event.id = 1
    event.name = "Test Event"
    event.website_url = "https://example.com"  # This is what's used in the code, not website
    event.last_website_check_at = None
    
    # Mock the _should_update_event method to return True
    with patch.object(enrichment_service, '_should_update_event', return_value=True):
        # Mock the _fetch_url_content method to return None (failure)
        with patch.object(enrichment_service, '_fetch_url_content', AsyncMock(return_value=None)):
            # Call the enrich_event method
            before_time = datetime.datetime.now()
            result = await enrichment_service.enrich_event(event)
            after_time = datetime.datetime.now()
    
    # Verify the result is False (no enrichment occurred)
    assert result is False
    
    # Verify last_website_check_at was updated
    assert event.last_website_check_at is not None
    assert before_time <= event.last_website_check_at <= after_time


@pytest.mark.asyncio
async def test_enrich_event_success(enrichment_service, mock_ai_service):
    """Test successful enrichment of an event with a website URL."""
    # Create an event with a website_url and no last_website_check_at
    event = MagicMock(spec=Event)
    event.id = 1
    event.name = "Test Event"
    event.website_url = "https://example.com"  # This is what's used in the code, not website
    event.last_website_check_at = None
    event.event_details = None
    
    # Mock the _should_update_event method to return True
    with patch.object(enrichment_service, '_should_update_event', return_value=True):
        # Mock the _fetch_url_content method to return some HTML content
        html_content = "<html><body>Test Content</body></html>"
        with patch.object(enrichment_service, '_fetch_url_content', AsyncMock(return_value=html_content)):
            # Mock the _extract_info_with_ai method to return some event details
            event_details = {
                "description": "Test description",
                "start_time": "10:00 AM",
                "end_time": "2:00 PM",
                "registration_info": "Register online",
                "cost_info": "$10",
                "contact_details": "contact@example.com",
                "requirements": "Bring your own gear",
                "highlights": "Fun activities",
                "organizer": "Test Organization"
            }
            with patch.object(enrichment_service, '_extract_info_with_ai', AsyncMock(return_value=event_details)):
                # Call the enrich_event method
                before_time = datetime.datetime.now()
                result = await enrichment_service.enrich_event(event)
                after_time = datetime.datetime.now()
    
    # Verify the result is True (enrichment occurred)
    assert result is True
    
    # Verify event_details was updated
    assert event.event_details is not None
    assert event.event_details == event_details
    
    # Verify last_website_check_at was updated
    assert event.last_website_check_at is not None
    assert before_time <= event.last_website_check_at <= after_time


@pytest.mark.asyncio
async def test_enrich_event_merge_existing_details(enrichment_service, mock_ai_service):
    """Test enriching an event that already has some details."""
    # Create an event with a website_url and existing details
    existing_details = {
        "description": "Existing description",
        "custom_field": "Custom value"
    }
    
    event = MagicMock(spec=Event)
    event.id = 1
    event.name = "Original Event"
    event.website_url = "https://example.com"  # This is what's used in the code, not website
    event.event_details = existing_details
    
    # Expected merged details
    new_extracted_data = {
        "description": "New description",
        "start_time": "10:00 AM",
        "end_time": "2:00 PM"
    }
    
    expected_merged_details = {
        "description": "New description",  # Overwritten
        "custom_field": "Custom value",    # Preserved
        "start_time": "10:00 AM",          # Added
        "end_time": "2:00 PM"              # Added
    }
    
    # Mock the _should_update_event method to return True
    with patch.object(enrichment_service, '_should_update_event', return_value=True):
        # Mock the _fetch_url_content method to return some HTML content
        html_content = "<html><body>Test Content</body></html>"
        with patch.object(enrichment_service, '_fetch_url_content', AsyncMock(return_value=html_content)):
            # Mock the _extract_info_with_ai method to return some event details
            with patch.object(enrichment_service, '_extract_info_with_ai', AsyncMock(return_value=new_extracted_data)):
                # Call the enrich_event method
                result = await enrichment_service.enrich_event(event)
    
    # Verify the result is True (enrichment occurred)
    assert result is True
    
    # Verify event_details was updated and merged correctly
    assert event.event_details is not None
    assert event.event_details == expected_merged_details


@pytest.mark.parametrize(
    "event_date,last_check,expected_result",
    [
        # Event without date (should update)
        (None, None, True),
        # Event never checked (should update)
        (datetime.datetime.now().date() + datetime.timedelta(days=30), None, True),
        # Event in the past (should not update)
        (datetime.datetime.now().date() - datetime.timedelta(days=1), datetime.datetime.now() - datetime.timedelta(days=1), False),
        # Near-term event checked less than 24 hours ago (should not update)
        (datetime.datetime.now().date() + datetime.timedelta(days=30), 
         datetime.datetime.now() - datetime.timedelta(hours=12), False),
        # Near-term event checked more than 24 hours ago (should update)
        (datetime.datetime.now().date() + datetime.timedelta(days=30), 
         datetime.datetime.now() - datetime.timedelta(hours=25), True),
        # Future event checked less than 7 days ago (should not update)
        (datetime.datetime.now().date() + datetime.timedelta(days=120), 
         datetime.datetime.now() - datetime.timedelta(days=3), False),
        # Future event checked more than 7 days ago (should update)
        (datetime.datetime.now().date() + datetime.timedelta(days=120), 
         datetime.datetime.now() - datetime.timedelta(days=8), True),
    ]
)
def test_should_update_event(enrichment_service, event_date, last_check, expected_result):
    """Test the _should_update_event method with various scenarios."""
    # Create an event with the given parameters
    event = MagicMock(spec=Event)
    event.id = 1
    event.name = "Test Event"
    event.date = event_date  # This is what's used in the code, not date_start
    event.last_website_check_at = last_check
    
    # Check if the event should be updated
    result = enrichment_service._should_update_event(event)
    
    # Verify the result
    assert result is expected_result


@pytest.mark.asyncio
async def test_extract_info_with_ai_success(enrichment_service, mock_ai_service):
    """Test successful extraction of info using AI."""
    # Create a test event
    event = MagicMock(spec=Event)
    event.id = 1
    event.name = "Test Event"
    event.location = "Test Location"
    event.date = datetime.datetime.now().date()  # This is what's used in the code, not date_start
    
    # Mock the AI response
    ai_response = json.dumps({
        "description": "Test description",
        "start_time": "10:00 AM",
        "end_time": "2:00 PM",
        "cost_info": "$10"
    })
    mock_ai_service.generate_text.return_value = ai_response
    
    # Call the _extract_info_with_ai method
    result = await enrichment_service._extract_info_with_ai("Test content", event)
    
    # Verify the AI service was called with the correct prompt
    mock_ai_service.generate_text.assert_called_once()
    # Extract the first argument of the first call
    call_args = mock_ai_service.generate_text.call_args[0]
    assert "Test content" in call_args[0]
    assert "JSON" in call_args[0]
    
    # Verify the result contains the expected details
    assert result["description"] == "Test description"
    assert result["start_time"] == "10:00 AM"
    assert result["end_time"] == "2:00 PM"
    assert result["cost_info"] == "$10"


@pytest.mark.asyncio
async def test_extract_info_with_ai_json_error(enrichment_service, mock_ai_service):
    """Test handling of invalid JSON from AI."""
    # Create a test event
    event = MagicMock(spec=Event)
    event.id = 1
    event.name = "Test Event"
    event.date = None
    event.location = "Test Location"
    
    # Mock the AI response with invalid JSON
    mock_ai_service.generate_text.return_value = "Not valid JSON"
    
    # Call the _extract_info_with_ai method
    result = await enrichment_service._extract_info_with_ai("Test content", event)
    
    # Verify the result has the extraction_error flag
    assert result is not None
    assert isinstance(result, dict)
    assert "extraction_error" in result
    assert result["extraction_error"] is True


@pytest.mark.asyncio
async def test_close(enrichment_service, mock_session):
    """Test closing the service."""
    # Set up the session in the service
    enrichment_service.session = mock_session
    mock_session.closed = False
    mock_session.close = AsyncMock()
    
    # Call the close method
    await enrichment_service.close()
    
    # Verify the session was closed
    mock_session.close.assert_called_once()


def test_clear_cache(enrichment_service):
    """Test clearing the cache."""
    # Add some items to the cache
    enrichment_service._cache = {"url1": "content1", "url2": "content2"}
    
    # Clear the cache
    enrichment_service.clear_cache()
    
    # Verify the cache is empty
    assert len(enrichment_service._cache) == 0 