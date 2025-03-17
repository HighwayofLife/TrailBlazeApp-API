"""Tests for the geocoding enrichment service."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.models import Event
from app.services.enrichment import GeocodingEnrichmentService

@pytest.fixture
def mock_geocoding_service():
    """Create a mocked geocoding service."""
    with patch('app.services.enrichment.geocoding.GeocodingService') as mock:
        mock_instance = MagicMock()
        mock_instance.geocode_event = AsyncMock()
        mock.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def geocoding_enrichment_service(mock_geocoding_service):
    """Create a geocoding enrichment service with mocked dependencies."""
    return GeocodingEnrichmentService()

@pytest.mark.asyncio
async def test_enrich_event_already_geocoded(geocoding_enrichment_service):
    """Test enriching an event that already has coordinates."""
    # Create an event with coordinates
    event = Event(
        id=1,
        name="Test Event",
        location="123 Test St, Testville, TS",
        latitude=42.0,
        longitude=-71.0
    )
    
    # Enrich the event
    result = await geocoding_enrichment_service.enrich_event(event)
    
    # Verify the result
    assert result is True
    
    # Verify the geocode_event method was not called
    geocoding_enrichment_service.geocoding_service.geocode_event.assert_not_called()

@pytest.mark.asyncio
async def test_enrich_event_no_location(geocoding_enrichment_service):
    """Test enriching an event with no location."""
    # Create an event without a location
    event = Event(
        id=1,
        name="Test Event",
        location=None
    )
    
    # Enrich the event
    result = await geocoding_enrichment_service.enrich_event(event)
    
    # Verify the result
    assert result is False
    
    # Verify the geocode_event method was not called
    geocoding_enrichment_service.geocoding_service.geocode_event.assert_not_called()

@pytest.mark.asyncio
async def test_enrich_event_success(geocoding_enrichment_service):
    """Test enriching an event successfully."""
    # Create an event that needs geocoding
    event = Event(
        id=1,
        name="Test Event",
        location="123 Test St, Testville, TS"
    )
    
    # Configure the mock to return success
    geocoding_enrichment_service.geocoding_service.geocode_event.return_value = True
    
    # Enrich the event
    result = await geocoding_enrichment_service.enrich_event(event)
    
    # Verify the result
    assert result is True
    
    # Verify the geocode_event method was called with the right parameters
    geocoding_enrichment_service.geocoding_service.geocode_event.assert_called_once_with(event)

@pytest.mark.asyncio
async def test_enrich_event_failure(geocoding_enrichment_service):
    """Test enriching an event with geocoding failure."""
    # Create an event that needs geocoding
    event = Event(
        id=1,
        name="Test Event",
        location="123 Test St, Testville, TS"
    )
    
    # Configure the mock to return failure
    geocoding_enrichment_service.geocoding_service.geocode_event.return_value = False
    
    # Enrich the event
    result = await geocoding_enrichment_service.enrich_event(event)
    
    # Verify the result
    assert result is False
    
    # Verify the geocode_event method was called with the right parameters
    geocoding_enrichment_service.geocoding_service.geocode_event.assert_called_once_with(event)

def test_clear_cache(geocoding_enrichment_service):
    """Test clearing the cache."""
    # Clear the cache
    geocoding_enrichment_service.clear_cache()
    
    # Verify the clear_cache method was called on the underlying service
    geocoding_enrichment_service.geocoding_service.clear_cache.assert_called_once() 