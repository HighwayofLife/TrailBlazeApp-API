"""Tests for Gemini API integration."""

import pytest
from unittest.mock import AsyncMock, patch
import json

from scrapers.aerc_scraper.gemini_api import GeminiAPI
from scrapers.exceptions import AIError

@pytest.fixture
def api():
    """Create GeminiAPI instance with test key."""
    return GeminiAPI("test_api_key")

@pytest.fixture
def sample_html():
    """Create sample HTML content."""
    return """
    <div class="event">
        <h2>Summer Solstice Ride</h2>
        <p>Date: June 21, 2024</p>
        <p>Location: Desert Trails Ranch, Nevada</p>
        <p>Distances: 25, 50, 75 miles</p>
        <p>Manager: John Smith (555-123-4567)</p>
        <p>Entry Fee: $150</p>
    </div>
    """

@pytest.fixture
def sample_response():
    """Create sample Gemini API response."""
    return {
        "name": "Summer Solstice Ride",
        "date": "June 21, 2024",
        "location": "Desert Trails Ranch, Nevada",
        "distances": ["25", "50", "75"],
        "manager": "John Smith",
        "phone": "555-123-4567",
        "entry_fee": 150
    }

@pytest.mark.asyncio
async def test_successful_extraction(api, sample_html, sample_response):
    """Test successful event extraction."""
    with patch('google.generativeai.GenerativeModel') as mock_model:
        # Setup mock response
        mock_response = AsyncMock()
        mock_response.text = json.dumps(sample_response)
        mock_model.return_value.generate_content_async = AsyncMock(return_value=mock_response)
        
        events = await api.extract_events(sample_html)
        
        assert len(events) == 1
        event = events[0]
        assert event['name'] == "Summer Solstice Ride"
        assert event['date'] == "June 21, 2024"
        assert event['location'] == "Desert Trails Ranch, Nevada"
        assert event['distances'] == ["25", "50", "75"]

@pytest.mark.asyncio
async def test_empty_response(api, sample_html):
    """Test handling of empty API response."""
    with patch('google.generativeai.GenerativeModel') as mock_model:
        mock_response = AsyncMock()
        mock_response.text = ""
        mock_model.return_value.generate_content_async = AsyncMock(return_value=mock_response)
        
        with pytest.raises(AIError, match="Empty response from Gemini API"):
            await api.extract_events(sample_html)

@pytest.mark.asyncio
async def test_invalid_json_response(api, sample_html):
    """Test handling of invalid JSON response."""
    with patch('google.generativeai.GenerativeModel') as mock_model:
        mock_response = AsyncMock()
        mock_response.text = "Invalid JSON {{"
        mock_model.return_value.generate_content_async = AsyncMock(return_value=mock_response)
        
        with pytest.raises(AIError, match="Failed to parse Gemini response as JSON"):
            await api.extract_events(sample_html)

@pytest.mark.asyncio
async def test_missing_required_fields(api, sample_html):
    """Test handling of response missing required fields."""
    with patch('google.generativeai.GenerativeModel') as mock_model:
        mock_response = AsyncMock()
        mock_response.text = json.dumps({
            "name": "Test Event",
            # missing date and location
        })
        mock_model.return_value.generate_content_async = AsyncMock(return_value=mock_response)
        
        with pytest.raises(AIError, match="No valid events found in extracted data"):
            await api.extract_events(sample_html)

@pytest.mark.asyncio
async def test_multiple_events(api, sample_html):
    """Test handling of multiple events in response."""
    events = [
        {
            "name": "Event 1",
            "date": "2024-01-01",
            "location": "Location 1"
        },
        {
            "name": "Event 2",
            "date": "2024-01-02",
            "location": "Location 2"
        }
    ]
    
    with patch('google.generativeai.GenerativeModel') as mock_model:
        mock_response = AsyncMock()
        mock_response.text = json.dumps(events)
        mock_model.return_value.generate_content_async = AsyncMock(return_value=mock_response)
        
        extracted = await api.extract_events(sample_html)
        
        assert len(extracted) == 2
        assert extracted[0]['name'] == "Event 1"
        assert extracted[1]['name'] == "Event 2"

def test_html_cleaning(api):
    """Test HTML cleaning functionality."""
    long_html = "x" * 25000
    cleaned = api._clean_html(long_html)
    
    assert len(cleaned) <= 20000
    assert cleaned.endswith("...")
    
    # Test whitespace cleaning
    messy_html = """
        <div>
            Multiple    Spaces
            And LineBreaks
        </div>
    """
    cleaned = api._clean_html(messy_html)
    assert "Multiple Spaces And LineBreaks" in cleaned

@pytest.mark.asyncio
async def test_api_error_handling(api, sample_html):
    """Test handling of API errors."""
    with patch('google.generativeai.GenerativeModel') as mock_model:
        mock_model.return_value.generate_content_async = AsyncMock(
            side_effect=Exception("API Error")
        )
        
        with pytest.raises(AIError, match="Gemini API extraction failed: API Error"):
            await api.extract_events(sample_html)

@pytest.mark.asyncio
async def test_close(api):
    """Test cleanup method."""
    # Currently just verifies it doesn't raise exceptions
    await api.close()