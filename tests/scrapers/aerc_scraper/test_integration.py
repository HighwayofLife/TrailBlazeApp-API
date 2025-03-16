"""Integration tests for AERC scraper."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from scrapers.aerc_scraper.scraper import AERCScraper
from scrapers.aerc_scraper.exceptions import ScraperError

@pytest.fixture
def mock_db():
    """Create mock database session."""
    return MagicMock(spec=AsyncSession)

@pytest.fixture
async def scraper(test_settings):
    """Create scraper instance with test settings."""
    return AERCScraper(settings=test_settings)

@pytest.mark.asyncio
async def test_full_scraper_workflow(scraper, mock_db, test_html, sample_events, mock_gemini_response):
    """Test complete scraper workflow."""
    # Mock the network requests
    with patch('scrapers.aerc_scraper.network.NetworkHandler.make_request') as mock_request:
        mock_request.side_effect = [
            # First call - season IDs page
            '<input name="season[]" value="2024"><input name="season[]" value="2023">',
            # Second call - calendar HTML
            test_html
        ]
        
        # Mock Gemini API
        with patch('google.genai.generate_text', return_value=mock_gemini_response):
            # Mock database operations
            with patch('app.crud.event.get_events', return_value=[]):
                with patch('app.crud.event.create_event') as mock_create:
                    result = await scraper.run(mock_db)
                    
                    # Verify successful completion
                    assert result['status'] == 'success'
                    assert result['events_found'] > 0
                    assert result['events_valid'] > 0
                    assert mock_create.called

@pytest.mark.asyncio
async def test_failed_season_extraction(scraper, mock_db):
    """Test handling of failed season ID extraction."""
    with patch('scrapers.aerc_scraper.network.NetworkHandler.make_request') as mock_request:
        mock_request.return_value = '<div>No season inputs found</div>'
        
        result = await scraper.run(mock_db)
        assert result['status'] == 'error'
        assert 'Failed to extract season IDs' in result['message']

@pytest.mark.asyncio
async def test_failed_calendar_fetch(scraper, mock_db):
    """Test handling of failed calendar fetch."""
    with patch('scrapers.aerc_scraper.network.NetworkHandler.make_request') as mock_request:
        mock_request.side_effect = [
            '<input name="season[]" value="2024">',  # Successful season ID
            None  # Failed calendar fetch
        ]
        
        result = await scraper.run(mock_db)
        assert result['status'] == 'error'
        assert 'Failed to fetch calendar HTML' in result['message']

@pytest.mark.asyncio
async def test_failed_data_extraction(scraper, mock_db, test_html):
    """Test handling of failed data extraction."""
    with patch('scrapers.aerc_scraper.network.NetworkHandler.make_request') as mock_request:
        mock_request.side_effect = [
            '<input name="season[]" value="2024">',
            test_html
        ]
        
        # Mock Gemini API to fail
        with patch('google.genai.generate_text', side_effect=Exception("API Error")):
            result = await scraper.run(mock_db)
            assert result['status'] == 'error'
            assert 'Failed to extract structured data' in result['message']

@pytest.mark.asyncio
async def test_metrics_collection(scraper, mock_db, test_html, mock_gemini_response):
    """Test metrics collection during full workflow."""
    with patch('scrapers.aerc_scraper.network.NetworkHandler.make_request') as mock_request:
        mock_request.side_effect = [
            '<input name="season[]" value="2024">',
            test_html
        ]
        
        with patch('google.genai.generate_text', return_value=mock_gemini_response):
            with patch('app.crud.event.get_events', return_value=[]):
                with patch('app.crud.event.create_event'):
                    await scraper.run(mock_db)
                    
                    # Verify metrics from all components
                    assert scraper.network.get_metrics()['requests'] > 0
                    assert scraper.html_cleaner.get_metrics()['rows_found'] > 0
                    assert scraper.gemini_client.get_metrics()['calls'] > 0
                    assert scraper.cache.get_metrics()['hits'] >= 0

@pytest.mark.asyncio
async def test_cache_usage(scraper, mock_db, test_html, mock_gemini_response):
    """Test cache usage during scraping."""
    with patch('scrapers.aerc_scraper.network.NetworkHandler.make_request') as mock_request:
        mock_request.side_effect = [
            '<input name="season[]" value="2024">',
            test_html
        ]
        
        # First run - should cache
        with patch('google.genai.generate_text', return_value=mock_gemini_response):
            with patch('app.crud.event.get_events', return_value=[]):
                with patch('app.crud.event.create_event'):
                    await scraper.run(mock_db)
                    assert scraper.cache.get_metrics()['hits'] == 0
                    
                    # Second run - should use cache
                    await scraper.run(mock_db)
                    assert scraper.cache.get_metrics()['hits'] > 0

@pytest.mark.asyncio
async def test_database_error_handling(scraper, mock_db, test_html, mock_gemini_response):
    """Test handling of database errors."""
    with patch('scrapers.aerc_scraper.network.NetworkHandler.make_request') as mock_request:
        mock_request.side_effect = [
            '<input name="season[]" value="2024">',
            test_html
        ]
        
        with patch('google.genai.generate_text', return_value=mock_gemini_response):
            # Mock database error
            with patch('app.crud.event.get_events', side_effect=Exception("Database error")):
                result = await scraper.run(mock_db)
                
                assert result['status'] == 'error'
                assert scraper.db_handler.get_metrics()['errors'] > 0

@pytest.mark.asyncio
async def test_html_chunking(scraper, mock_db, test_html):
    """Test HTML chunking for large responses."""
    large_html = test_html * 10  # Make HTML content larger
    
    with patch('scrapers.aerc_scraper.network.NetworkHandler.make_request') as mock_request:
        mock_request.side_effect = [
            '<input name="season[]" value="2024">',
            large_html
        ]
        
        with patch('google.genai.generate_text', return_value=mock_gemini_response):
            with patch('app.crud.event.get_events', return_value=[]):
                with patch('app.crud.event.create_event'):
                    await scraper.run(mock_db)
                    
                    # Verify multiple chunks were processed
                    assert scraper.gemini_client.get_metrics()['calls'] > 1