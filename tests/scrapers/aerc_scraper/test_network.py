"""Tests for network handler module."""

import pytest
import aiohttp
from unittest.mock import patch, MagicMock
from scrapers.aerc_scraper.network import NetworkHandler
from scrapers.aerc_scraper.exceptions import NetworkError

@pytest.fixture
def network_handler(test_settings):
    """Create network handler instance."""
    return NetworkHandler(test_settings)

@pytest.mark.asyncio
async def test_successful_request(network_handler):
    """Test successful request."""
    url = "https://example.com"
    test_response = "test response"
    
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.text = MagicMock(return_value=test_response)
    
    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_get.return_value.__aenter__.return_value = mock_response
        response = await network_handler.make_request(url)
        
        assert response == test_response
        assert network_handler.get_metrics()['requests'] == 1
        assert network_handler.get_metrics()['errors'] == 0

@pytest.mark.asyncio
async def test_retry_on_timeout(network_handler):
    """Test retry on timeout."""
    url = "https://example.com"
    
    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_get.side_effect = [
            aiohttp.ClientTimeout(),  # First attempt fails
            MagicMock(__aenter__=MagicMock(
                return_value=MagicMock(status=200, text=MagicMock(return_value="success"))
            ))  # Second attempt succeeds
        ]
        
        response = await network_handler.make_request(url)
        assert response == "success"
        assert network_handler.get_metrics()['retries'] == 1

@pytest.mark.asyncio
async def test_retry_on_429(network_handler):
    """Test retry on rate limit (429)."""
    url = "https://example.com"
    
    mock_429 = MagicMock()
    mock_429.status = 429
    mock_429.headers = {"Retry-After": "1"}
    
    mock_200 = MagicMock()
    mock_200.status = 200
    mock_200.text = MagicMock(return_value="success")
    
    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_get.return_value.__aenter__.side_effect = [mock_429, mock_200]
        
        response = await network_handler.make_request(url)
        assert response == "success"
        assert network_handler.get_metrics()['retries'] == 1

@pytest.mark.asyncio
async def test_max_retries_exceeded(network_handler):
    """Test max retries exceeded."""
    url = "https://example.com"
    
    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_get.side_effect = aiohttp.ClientError()
        
        with pytest.raises(NetworkError, match="Max retries.*exceeded"):
            await network_handler.make_request(url)
        
        assert network_handler.get_metrics()['errors'] == 1
        assert network_handler.get_metrics()['retries'] == 2  # Based on test settings

@pytest.mark.asyncio
async def test_post_request(network_handler):
    """Test POST request with data."""
    url = "https://example.com"
    data = {"key": "value"}
    test_response = "test response"
    
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.text = MagicMock(return_value=test_response)
    
    with patch('aiohttp.ClientSession.post') as mock_post:
        mock_post.return_value.__aenter__.return_value = mock_response
        response = await network_handler.make_request(url, method="POST", data=data)
        
        assert response == test_response
        mock_post.assert_called_once()

@pytest.mark.asyncio
async def test_server_error_retry(network_handler):
    """Test retry on server error (500)."""
    url = "https://example.com"
    
    mock_500 = MagicMock()
    mock_500.status = 500
    
    mock_200 = MagicMock()
    mock_200.status = 200
    mock_200.text = MagicMock(return_value="success")
    
    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_get.return_value.__aenter__.side_effect = [mock_500, mock_200]
        
        response = await network_handler.make_request(url)
        assert response == "success"
        assert network_handler.get_metrics()['retries'] == 1