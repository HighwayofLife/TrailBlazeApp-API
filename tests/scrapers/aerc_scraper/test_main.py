"""Tests for AERC scraper main module."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime
from pathlib import Path

from scrapers.aerc_scraper.main import AERCScraper, run_scraper
from scrapers.config import ScraperSettings
from scrapers.exceptions import NetworkError, ValidationError, DatabaseError

@pytest.fixture
def settings():
    """Create test settings."""
    return ScraperSettings(
        database_url="postgresql+asyncpg://test:test@localhost:5432/test_db",
        requests_per_second=1.0,
        max_burst_size=2,
        cache_dir="/tmp/test_cache",
        use_ai_extraction=False
    )

@pytest.fixture
def mock_session():
    """Create mock database session."""
    return AsyncMock()

@pytest.fixture
def scraper(settings, mock_session):
    """Create scraper instance with mocked components."""
    with patch('scrapers.aerc_scraper.main.NetworkHandler') as mock_network, \
         patch('scrapers.aerc_scraper.main.HTMLCleaner') as mock_cleaner, \
         patch('scrapers.aerc_scraper.main.HtmlChunker') as mock_chunker, \
         patch('scrapers.aerc_scraper.main.EventParser') as mock_parser, \
         patch('scrapers.aerc_scraper.main.DataValidator') as mock_validator, \
         patch('scrapers.aerc_scraper.main.DatabaseHandler') as mock_db:
        
        # Set up mock returns
        mock_network.return_value.fetch_calendar = AsyncMock(return_value="<html>test</html>")
        mock_network.return_value.get_metrics = Mock(return_value={'requests': 1})
        
        mock_cleaner.return_value.clean = Mock(return_value="<clean>test</clean>")
        
        mock_chunker.return_value.create_chunks = Mock(return_value=["chunk1", "chunk2"])
        
        mock_parser.return_value.parse_chunk = Mock(return_value=[{"name": "Test Event"}])
        
        mock_validator.return_value.validate_events = Mock(return_value=[{"name": "Valid Event"}])
        mock_validator.return_value.get_metrics = Mock(return_value={'valid': 1})
        
        mock_db.return_value.store_events = AsyncMock(return_value={'added': 1, 'updated': 0})
        mock_db.return_value.get_metrics = Mock(return_value={'inserts': 1})
        
        scraper = AERCScraper(settings, mock_session, metrics_dir="/tmp/test_metrics")
        
        # Save mocks for test access
        scraper.mock_network = mock_network
        scraper.mock_cleaner = mock_cleaner
        scraper.mock_chunker = mock_chunker
        scraper.mock_parser = mock_parser
        scraper.mock_validator = mock_validator
        scraper.mock_db = mock_db
        
        return scraper

@pytest.mark.asyncio
async def test_scraper_successful_run(scraper):
    """Test successful scraper run."""
    result = await scraper.scrape()
    
    assert result['success'] is True
    assert result['events_found'] == 2  # One event per chunk
    assert result['events_valid'] == 1
    assert result['events_stored'] == 1
    assert 'run_id' in result
    
    # Verify component calls
    scraper.mock_network.return_value.fetch_calendar.assert_called_once()
    scraper.mock_cleaner.return_value.clean.assert_called_once()
    scraper.mock_chunker.return_value.create_chunks.assert_called_once()
    assert scraper.mock_parser.return_value.parse_chunk.call_count == 2
    scraper.mock_validator.return_value.validate_events.assert_called_once()
    scraper.mock_db.return_value.store_events.assert_called_once()

@pytest.mark.asyncio
async def test_scraper_with_ai_extraction(settings, mock_session):
    """Test scraper with AI extraction enabled."""
    settings.use_ai_extraction = True
    
    with patch('scrapers.aerc_scraper.main.GeminiAPI') as mock_gemini:
        mock_gemini.return_value.extract_events = AsyncMock(return_value=[{"name": "AI Event"}])
        
        scraper = AERCScraper(settings, mock_session)
        assert scraper.gemini is not None

@pytest.mark.asyncio
async def test_scraper_network_error(scraper):
    """Test handling of network errors."""
    scraper.mock_network.return_value.fetch_calendar.side_effect = NetworkError("Connection failed")
    
    result = await scraper.scrape()
    assert result['success'] is False
    assert "Connection failed" in result['error']

@pytest.mark.asyncio
async def test_scraper_validation_error(scraper):
    """Test handling of validation errors."""
    scraper.mock_validator.return_value.validate_events.side_effect = ValidationError("Invalid data")
    
    result = await scraper.scrape()
    assert result['success'] is False
    assert "Invalid data" in result['error']

@pytest.mark.asyncio
async def test_scraper_database_error(scraper):
    """Test handling of database errors."""
    scraper.mock_db.return_value.store_events.side_effect = DatabaseError("Database error")
    
    result = await scraper.scrape()
    assert result['success'] is False
    assert "Database error" in result['error']

@pytest.mark.asyncio
async def test_scraper_cleanup(scraper):
    """Test cleanup on scraper completion."""
    await scraper.scrape()
    
    scraper.mock_network.return_value.close.assert_called_once()

@pytest.mark.asyncio
async def test_run_scraper_integration(settings):
    """Test run_scraper integration."""
    with patch('scrapers.aerc_scraper.main.ScraperSettings') as mock_settings, \
         patch('scrapers.aerc_scraper.main.DatabaseHandler') as mock_db, \
         patch('scrapers.aerc_scraper.main.AERCScraper') as mock_scraper:
        
        mock_settings.from_yaml.return_value = settings
        mock_scraper.return_value.scrape = AsyncMock(return_value={'success': True})
        
        result = await run_scraper("test_config.yaml", "/tmp/test_metrics")
        
        assert result['success'] is True
        mock_settings.from_yaml.assert_called_once_with("test_config.yaml")
        mock_scraper.assert_called_once()