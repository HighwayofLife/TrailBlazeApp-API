"""Tests for GeminiClient class."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
from dataclasses import dataclass

from scrapers.aerc_scraper.gemini_client import GeminiClient
from scrapers.exceptions import AIError

@dataclass
class MockSettings:
    """Mock settings for testing."""
    gemini_api_key: str = "test_key"
    primary_model: str = "gemini-2.0-flash"
    fallback_model: str = "gemini-pro"
    temperature: float = 0.2

@pytest.fixture
def client():
    """Create GeminiClient instance with mock settings."""
    return GeminiClient(MockSettings())

@pytest.fixture
def sample_event():
    """Sample event data."""
    return {
        "rideName": "Test Endurance Ride",
        "date": "2024-06-15",
        "region": "MT",
        "location": "Mountain Trail Ranch",
        "distances": [
            {
                "distance": "50",
                "date": "2024-06-15",
                "startTime": "06:00"
            }
        ],
        "rideManager": "Jane Smith",
        "rideManagerContact": {
            "name": "Jane Smith",
            "email": "jane@example.com",
            "phone": "555-0123"
        },
        "controlJudges": [
            {
                "role": "Head Veterinarian",
                "name": "Dr. John Doe"
            }
        ],
        "mapLink": "https://maps.google.com/test",
        "hasIntroRide": True
    }

@pytest.mark.asyncio
async def test_successful_extraction(client, sample_event):
    """Test successful data extraction."""
    with patch('google.genai.Client') as mock_client:
        mock_response = MagicMock()
        mock_response.text = json.dumps([sample_event])
        mock_client.return_value.models.generate_content_async = AsyncMock(
            return_value=mock_response
        )
        client.client = mock_client.return_value
        
        result = await client.extract_data("<div>Sample HTML</div>")
        
        assert len(result) == 1
        assert result[0]["rideName"] == sample_event["rideName"]
        assert result[0]["date"] == sample_event["date"]
        assert len(result[0]["distances"]) == 1

@pytest.mark.asyncio
async def test_fallback_model(client, sample_event):
    """Test fallback to secondary model."""
    with patch('google.genai.Client') as mock_client:
        # Primary model fails
        mock_client.return_value.models.generate_content_async = AsyncMock(
            side_effect=[Exception("Primary model error"), MagicMock(text=json.dumps([sample_event]))]
        )
        client.client = mock_client.return_value
        
        result = await client.extract_data("<div>Sample HTML</div>")
        
        assert len(result) == 1
        assert result[0]["rideName"] == sample_event["rideName"]
        assert client.metrics["fallback_successes"] == 1
        assert client.metrics["errors"] == 1

@pytest.mark.asyncio
async def test_both_models_fail(client):
    """Test behavior when both models fail."""
    with patch('google.genai.Client') as mock_client:
        mock_client.return_value.models.generate_content_async = AsyncMock(
            side_effect=[Exception("Primary error"), Exception("Fallback error")]
        )
        client.client = mock_client.return_value
        
        with pytest.raises(AIError, match="Both models failed"):
            await client.extract_data("<div>Sample HTML</div>")
        
        assert client.metrics["errors"] == 2

def test_fix_json_syntax(client):
    """Test JSON syntax fixing."""
    # Test trailing comma fix
    assert client._fix_json_syntax('[{"a": 1},]') == '[{"a": 1}]'
    
    # Test missing comma between objects
    assert client._fix_json_syntax('[{"a":1}{"b":2}]') == '[{"a":1},{"b":2}]'
    
    # Test missing array closure
    assert client._fix_json_syntax('[{"a":1}') == '[{"a":1}]'

@pytest.mark.asyncio
async def test_invalid_json_response(client):
    """Test handling of invalid JSON in response."""
    with patch('google.genai.Client') as mock_client:
        mock_response = MagicMock()
        mock_response.text = "Invalid JSON {{"
        mock_client.return_value.models.generate_content_async = AsyncMock(
            side_effect=[mock_response, mock_response]
        )
        client.client = mock_client.return_value
        
        with pytest.raises(AIError):
            await client.extract_data("<div>Sample HTML</div>")

def test_metrics_tracking(client):
    """Test metrics tracking."""
    initial_metrics = client.get_metrics()
    assert initial_metrics["calls"] == 0
    assert initial_metrics["errors"] == 0
    assert initial_metrics["fallback_successes"] == 0
    assert initial_metrics["total_tokens"] == 0
    
    # Metrics object should be copied
    metrics = client.get_metrics()
    metrics["calls"] = 100
    assert client.get_metrics()["calls"] == 0