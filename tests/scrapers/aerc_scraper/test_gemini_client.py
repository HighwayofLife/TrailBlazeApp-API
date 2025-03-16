"""Tests for Gemini client module."""

import pytest
from unittest.mock import patch, MagicMock
import json
from scrapers.aerc_scraper.gemini_client import GeminiClient
from scrapers.aerc_scraper.exceptions import GeminiAPIError

@pytest.fixture
def gemini_client(test_settings):
    """Create Gemini client instance."""
    return GeminiClient(test_settings)

@pytest.mark.asyncio
async def test_successful_extraction(gemini_client, test_html, mock_gemini_response):
    """Test successful data extraction."""
    with patch('google.genai.generate_text', return_value=mock_gemini_response):
        events = await gemini_client.extract_data(test_html)
        
        assert events is not None
        assert isinstance(events, list)
        assert len(events) > 0
        assert gemini_client.get_metrics()['calls'] == 1
        assert gemini_client.get_metrics()['errors'] == 0

@pytest.mark.asyncio
async def test_fallback_model(gemini_client, test_html, mock_gemini_response):
    """Test fallback to secondary model."""
    with patch('google.genai.generate_text') as mock_generate:
        # Primary model fails
        mock_generate.side_effect = [
            Exception("Primary model error"),
            mock_gemini_response  # Fallback model succeeds
        ]
        
        events = await gemini_client.extract_data(test_html)
        
        assert events is not None
        assert gemini_client.get_metrics()['errors'] == 1
        assert gemini_client.get_metrics()['fallback_successes'] == 1

@pytest.mark.asyncio
async def test_both_models_fail(gemini_client, test_html):
    """Test handling when both models fail."""
    with patch('google.genai.generate_text', side_effect=Exception("API error")):
        with pytest.raises(GeminiAPIError):
            await gemini_client.extract_data(test_html)
        
        assert gemini_client.get_metrics()['errors'] == 2  # Both models failed

@pytest.mark.asyncio
async def test_invalid_json_response(gemini_client, test_html):
    """Test handling invalid JSON in response."""
    invalid_response = {
        "text": "Invalid JSON {test: missing quotes}",
        "candidates": [{"content": {"text": "Invalid JSON"}}]
    }
    
    with patch('google.genai.generate_text', return_value=invalid_response):
        with pytest.raises(GeminiAPIError):
            await gemini_client.extract_data(test_html)
        
        assert gemini_client.get_metrics()['errors'] > 0

@pytest.mark.asyncio
async def test_empty_response(gemini_client, test_html):
    """Test handling empty response."""
    empty_response = {
        "text": "[]",
        "candidates": [{"content": {"text": "[]"}}]
    }
    
    with patch('google.genai.generate_text', return_value=empty_response):
        events = await gemini_client.extract_data(test_html)
        
        assert events == []
        assert gemini_client.get_metrics()['calls'] == 1

@pytest.mark.asyncio
async def test_malformed_events(gemini_client, test_html):
    """Test handling malformed events in response."""
    malformed_response = {
        "text": '[{"incomplete": "event"}',
        "candidates": [{"content": {"text": '[{"incomplete": "event"}'}}]
    }
    
    with patch('google.genai.generate_text', return_value=malformed_response):
        with pytest.raises(GeminiAPIError):
            await gemini_client.extract_data(test_html)

@pytest.mark.asyncio
async def test_metrics_tracking(gemini_client, test_html, mock_gemini_response):
    """Test accurate metrics tracking."""
    with patch('google.genai.generate_text') as mock_generate:
        # Simulate various scenarios
        mock_generate.side_effect = [
            Exception("Error"),  # First call fails
            mock_gemini_response  # Second call succeeds
        ]
        
        events = await gemini_client.extract_data(test_html)
        metrics = gemini_client.get_metrics()
        
        assert metrics['calls'] == 2
        assert metrics['errors'] == 1
        assert metrics['fallback_successes'] == 1

@pytest.mark.asyncio
async def test_prompt_formatting(gemini_client, test_html):
    """Test prompt formatting."""
    with patch('google.genai.generate_text') as mock_generate:
        await gemini_client.extract_data(test_html)
        
        # Check that generate_text was called with properly formatted prompt
        call_args = mock_generate.call_args[1]
        prompt = call_args.get('prompt', '')
        
        assert 'IMPORTANT FORMATTING INSTRUCTIONS' in prompt
        assert 'JSON Structure' in prompt
        assert 'Calendar HTML' in prompt

@pytest.mark.asyncio
async def test_response_cleaning(gemini_client):
    """Test response text cleaning."""
    # Test various response formats
    test_cases = [
        ('```json\n[{"test": "value"}]\n```', [{"test": "value"}]),  # Markdown code block
        ('Some text [{"test": "value"}] more text', [{"test": "value"}]),  # Embedded JSON
        ('[{"test": "value"},]', [{"test": "value"}]),  # Trailing comma
        ('[{"test": "value"}}]', [{"test": "value"}])  # Extra brace
    ]
    
    for input_text, expected in test_cases:
        mock_response = {
            "text": input_text,
            "candidates": [{"content": {"text": input_text}}]
        }
        
        with patch('google.genai.generate_text', return_value=mock_response):
            events = await gemini_client.extract_data("test html")
            assert events == expected