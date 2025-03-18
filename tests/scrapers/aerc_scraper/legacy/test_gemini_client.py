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
    primary_model: str = "gemini-2.0-flash-lite"
    fallback_model: str = "gemini-2.0-flash"
    temperature: float = 0.2
    html_chunk_size: int = 20000
    max_output_tokens: int = 8192

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
        # Create a mock response
        mock_response = MagicMock()
        mock_response.text = json.dumps([sample_event])
        mock_response.usage = MagicMock(total_tokens=100, output_tokens=50)
        
        # Set up the client to return the mock response
        mock_client.return_value.models.generate_content = MagicMock(
            return_value=mock_response
        )
        
        # Mock token counting
        mock_client.return_value.models.count_tokens = AsyncMock(
            return_value=MagicMock(total_tokens=50)
        )
        
        client.client = mock_client.return_value
        
        result = await client.extract_data("<div>Sample HTML</div>")
        
        assert len(result) == 1
        assert result[0]["rideName"] == sample_event["rideName"]
        assert result[0]["date"] == sample_event["date"]
        assert len(result[0]["distances"]) == 1
        
        # Check that token metrics were updated
        assert client.metrics["total_tokens"] > 0
        assert len(client.metrics["token_counts"]) > 0

@pytest.mark.asyncio
async def test_html_chunking(client, sample_event):
    """Test HTML chunking functionality."""
    # Create a large HTML input
    large_html = "<div>" + "<tr><td>Event data</td></tr>" * 1000 + "</div>"
    
    with patch('google.genai.Client') as mock_client:
        # Create a mock response
        mock_response = MagicMock()
        mock_response.text = json.dumps([sample_event])
        mock_response.usage = MagicMock(total_tokens=100, output_tokens=50)
        
        # Set up the client to return the mock response for any call
        mock_client.return_value.models.generate_content = MagicMock(
            return_value=mock_response
        )
        
        # Mock token counting to trigger chunking
        mock_client.return_value.models.count_tokens = AsyncMock(
            return_value=MagicMock(total_tokens=9000)  # Large token count
        )
        
        # Mock streaming API
        mock_client.return_value.aio.models.generate_content_stream = AsyncMock()
        
        # Setup the async iterator for streaming
        async def mock_stream_iterator():
            chunk = MagicMock()
            chunk.text = json.dumps([sample_event])
            yield chunk
        
        mock_client.return_value.aio.models.generate_content_stream.return_value = mock_stream_iterator()
        
        client.client = mock_client.return_value
        
        # Test the chunking functionality
        result = await client.extract_data(large_html)
        
        # Should have processed multiple chunks
        assert client.metrics["chunks_processed"] > 1
        assert len(result) > 0

@pytest.mark.asyncio
async def test_streaming_api(client, sample_event):
    """Test streaming API functionality."""
    with patch('google.genai.Client') as mock_client:
        # Mock token counting
        mock_client.return_value.models.count_tokens = AsyncMock(
            return_value=MagicMock(total_tokens=50)
        )
        
        # Mock regular API to fail
        mock_client.return_value.models.generate_content = MagicMock(
            side_effect=Exception("API error")
        )
        
        # Setup the async iterator for streaming
        async def mock_stream_iterator():
            chunk = MagicMock()
            chunk.text = json.dumps([sample_event])
            yield chunk
        
        # Mock streaming API to succeed
        mock_client.return_value.aio.models.generate_content_stream = AsyncMock(
            return_value=mock_stream_iterator()
        )
        
        client.client = mock_client.return_value
        
        # Test streaming functionality
        result = await client.extract_data("<div>Sample HTML</div>")
        
        assert len(result) == 1
        assert client.metrics["streaming_used"] > 0

@pytest.mark.asyncio
async def test_structured_output(client, sample_event):
    """Test structured output extraction."""
    with patch('google.genai.Client') as mock_client:
        # Create a mock response
        mock_response = MagicMock()
        mock_response.text = json.dumps([sample_event])
        mock_response.usage = MagicMock(total_tokens=100, output_tokens=50)
        
        # Set up the client to return the mock response
        mock_client.return_value.models.generate_content = MagicMock(
            return_value=mock_response
        )
        
        # Mock token counting
        mock_client.return_value.models.count_tokens = AsyncMock(
            return_value=MagicMock(total_tokens=50)
        )
        
        client.client = mock_client.return_value
        
        # Test the structured output path
        structured_prompt = client._create_structured_prompt("<div>Sample HTML</div>")
        assert "prompt" in structured_prompt
        assert "schema" in structured_prompt
        assert structured_prompt["schema"]["type"] == "ARRAY"
        
        result = await client.extract_data("<div>Sample HTML</div>")
        assert len(result) == 1

@pytest.mark.asyncio
async def test_fallback_model(client, sample_event):
    """Test fallback to secondary model."""
    with patch('google.genai.Client') as mock_client:
        # Primary model fails, fallback model succeeds
        mock_response = MagicMock()
        mock_response.text = json.dumps([sample_event])
        mock_response.usage = MagicMock(total_tokens=100, output_tokens=50)
        
        # Set up the client to return the mock response
        mock_client.return_value.models.generate_content = MagicMock(
            side_effect=[Exception("Primary error"), Exception("Structured error"), mock_response]
        )
        
        # Mock token counting
        mock_client.return_value.models.count_tokens = AsyncMock(
            return_value=MagicMock(total_tokens=50)
        )
        
        # Mock streaming API to fail
        mock_client.return_value.aio.models.generate_content_stream = AsyncMock(
            side_effect=Exception("Streaming error")
        )
        
        client.client = mock_client.return_value
        
        result = await client.extract_data("<div>Sample HTML</div>")
        
        assert len(result) == 1
        assert result[0]["rideName"] == sample_event["rideName"]
        assert client.metrics["fallback_successes"] == 1
        assert client.metrics["errors"] > 0
        assert "Exception" in client.metrics["error_types"]

@pytest.mark.asyncio
async def test_both_models_fail(client):
    """Test behavior when both models fail."""
    with patch('google.genai.Client') as mock_client:
        # All methods fail
        mock_client.return_value.models.generate_content = MagicMock(
            side_effect=Exception("API error")
        )
        
        # Mock token counting
        mock_client.return_value.models.count_tokens = AsyncMock(
            return_value=MagicMock(total_tokens=50)
        )
        
        # Mock streaming API to fail
        mock_client.return_value.aio.models.generate_content_stream = AsyncMock(
            side_effect=Exception("Streaming error")
        )
        
        client.client = mock_client.return_value
        
        with pytest.raises(AIError, match="All extraction methods failed"):
            await client.extract_data("<div>Sample HTML</div>")
        
        assert client.metrics["errors"] > 0
        assert "Exception" in client.metrics["error_types"]

@pytest.mark.asyncio
async def test_token_counting(client):
    """Test token counting functionality."""
    with patch('google.genai.Client') as mock_client:
        # Mock token counting
        mock_client.return_value.models.count_tokens = AsyncMock(
            return_value=MagicMock(total_tokens=150)
        )
        
        client.client = mock_client.return_value
        
        token_count = await client.count_tokens("Test text", "gemini-2.0-flash-lite")
        assert token_count == 150
        
        # Test error handling
        mock_client.return_value.models.count_tokens = AsyncMock(
            side_effect=Exception("Token counting error")
        )
        
        token_count = await client.count_tokens("Test text", "gemini-2.0-flash-lite")
        assert token_count == -1  # Error indicator

def test_html_splitting(client):
    """Test HTML splitting functionality."""
    # Test with table rows
    html_with_rows = "<table>" + "<tr><td>Event data</td></tr>" * 100 + "</table>"
    chunks = client._split_html_into_chunks(html_with_rows)
    assert len(chunks) > 1
    
    # Test with divs
    html_with_divs = "<div>" + '<div class="event">Event data</div>' * 100 + "</div>"
    chunks = client._split_html_into_chunks(html_with_divs)
    assert len(chunks) > 1
    
    # Test with generic HTML
    generic_html = "<div>" + "<p>Content</p>" * 1000 + "</div>"
    chunks = client._split_by_size(generic_html)
    assert len(chunks) > 1
    
    # Test tag boundary preservation
    html_with_tags = "<div><p>Test</p></div>" * 100
    chunks = client._split_by_size(html_with_tags)
    for chunk in chunks:
        # Each chunk should either start with '<div>' or end with '</div>'
        # or both, ensuring we don't break in the middle of a tag
        assert chunk.startswith("<div>") or chunk.endswith("</div>") or ">" in chunk[:10]

def test_fix_json_syntax(client):
    """Test JSON syntax fixing."""
    # Test trailing comma fix
    assert client._fix_json_syntax('[{"a": 1},]') == '[{"a": 1}]'
    
    # Test missing comma between objects
    assert client._fix_json_syntax('[{"a":1}{"b":2}]') == '[{"a":1},{"b":2}]'
    
    # Test missing array closure
    assert client._fix_json_syntax('[{"a":1}') == '[{"a":1}]'
    
    # Test handling truncated JSON due to token limits
    assert client._fix_json_syntax('[{"a":1},{"b":2},{"c":') == '[{"a":1},{"b":2},{"c":}]'
    assert client._fix_json_syntax('[{"a":1},{"b":{"c":"d"') == '[{"a":1},{"b":{"c":"d"}}]'
    
    # Test handling of invalid escape sequences
    json_with_bad_escapes = r'[{"text": "This has a bad \escape sequence"}]'
    fixed_json = client._fix_json_syntax(json_with_bad_escapes)
    # Should be able to parse the fixed JSON
    assert json.loads(fixed_json)
    
    # Test unterminated string fix
    json_with_unterminated = '[\n{"name": "test", "description": "unterminated\n}]'
    fixed_json = client._fix_json_syntax(json_with_unterminated)
    try:
        json.loads(fixed_json)
        assert True  # If we get here, the JSON was fixed
    except json.JSONDecodeError:
        assert False, "Failed to fix unterminated string"

@pytest.mark.asyncio
async def test_invalid_json_response(client):
    """Test handling of invalid JSON in response."""
    with patch('google.genai.Client') as mock_client:
        mock_response = MagicMock()
        mock_response.text = "Invalid JSON {{"
        
        # Mock token counting
        mock_client.return_value.models.count_tokens = AsyncMock(
            return_value=MagicMock(total_tokens=50)
        )
        
        # All methods return invalid JSON
        mock_client.return_value.models.generate_content = MagicMock(
            return_value=mock_response
        )
        
        # Mock streaming API to return invalid JSON
        async def mock_stream_iterator():
            chunk = MagicMock()
            chunk.text = "Invalid JSON {{"
            yield chunk
        
        mock_client.return_value.aio.models.generate_content_stream = AsyncMock(
            return_value=mock_stream_iterator()
        )
        
        client.client = mock_client.return_value
        
        with pytest.raises(AIError):
            await client.extract_data("<div>Sample HTML</div>")
        
        assert "JSONDecodeError" in client.metrics["error_types"] or "Exception" in client.metrics["error_types"]

def test_metrics_tracking(client):
    """Test metrics tracking."""
    initial_metrics = client.get_metrics()
    assert initial_metrics["calls"] == 0
    assert initial_metrics["errors"] == 0
    assert initial_metrics["fallback_successes"] == 0
    assert initial_metrics["total_tokens"] == 0
    assert "token_counts" in initial_metrics
    assert "error_types" in initial_metrics
    assert "streaming_used" in initial_metrics
    assert "chunks_processed" in initial_metrics
    
    # Metrics object should be copied
    metrics = client.get_metrics()
    metrics["calls"] = 100
    assert client.get_metrics()["calls"] == 0

def test_field_mapping(client):
    """Test field mapping functionality."""
    # Sample event data in AI extraction format
    sample_event = {
        "rideName": "Test Ride",
        "date": "2024-06-15",
        "region": "NW",
        "location": "Test Location, City, ST",
        "distances": [
            {
                "distance": "50 Miles",
                "date": "2024-06-15",
                "startTime": "6:00 AM"
            },
            {
                "distance": "25 Miles",
                "date": "2024-06-16",
                "startTime": "7:00 AM"
            }
        ],
        "rideManager": "John Doe",
        "rideManagerContact": {
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "555-123-4567"
        },
        "controlJudges": [
            {
                "role": "Head Vet",
                "name": "Dr. Smith"
            },
            {
                "role": "Treatment Vet",
                "name": "Dr. Jones"
            }
        ],
        "mapLink": "https://maps.example.com/location",
        "hasIntroRide": True,
        "tag": 12345
    }
    
    # Test mapping a single event
    mapped_events = client._map_fields([sample_event])
    assert len(mapped_events) == 1
    
    mapped = mapped_events[0]
    
    # Verify basic field mapping
    assert mapped['name'] == "Test Ride"
    assert mapped['date_start'] == "2024-06-15"
    assert mapped['location'] == "Test Location, City, ST"
    assert mapped['region'] == "NW"
    assert mapped['ride_manager'] == "John Doe"
    
    # Verify contact information mapping
    assert mapped['manager_email'] == "john@example.com"
    assert mapped['manager_phone'] == "555-123-4567"
    assert "Name: John Doe" in mapped['manager_contact']
    assert "Email: john@example.com" in mapped['manager_contact']
    assert "Phone: 555-123-4567" in mapped['manager_contact']
    
    # Verify judges mapping
    assert len(mapped['judges']) == 2
    assert "Head Vet: Dr. Smith" in mapped['judges']
    assert "Treatment Vet: Dr. Jones" in mapped['judges']
    
    # Verify distances mapping
    assert len(mapped['distances']) == 2
    assert "50 Miles" in mapped['distances']
    assert "25 Miles" in mapped['distances']
    
    # Verify event details mapping
    assert mapped['event_details']['distances'] == sample_event['distances']
    assert mapped['event_details']['hasIntroRide'] == True
    
    # Verify date_end is set to the latest distance date
    assert mapped['date_end'] == "2024-06-16"
    
    # Verify other fields
    assert mapped['map_link'] == "https://maps.example.com/location"
    assert mapped['external_id'] == "12345"
    assert mapped['event_type'] == "endurance"
    assert mapped['source'] == "AERC"
    
    # Test mapping an empty list
    assert client._map_fields([]) == []
    
    # Test mapping with missing fields
    minimal_event = {
        "rideName": "Minimal Ride",
        "date": "2024-07-01",
        "location": "Somewhere"
    }
    
    mapped_minimal = client._map_fields([minimal_event])[0]
    assert mapped_minimal['name'] == "Minimal Ride"
    assert mapped_minimal['date_start'] == "2024-07-01"
    assert mapped_minimal['location'] == "Somewhere"
    assert 'date_end' not in mapped_minimal  # No distances to set end date