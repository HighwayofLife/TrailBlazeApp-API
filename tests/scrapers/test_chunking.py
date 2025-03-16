"""Tests for HTML chunking module."""

import pytest
from bs4 import BeautifulSoup
from scrapers.aerc_scraper.chunking import HtmlChunker
from scrapers.exceptions import ChunkingError
from scrapers.config import ScraperBaseSettings

@pytest.fixture
def test_settings():
    """Create test settings."""
    return ScraperBaseSettings(
        initial_chunk_size=1000,
        min_chunk_size=500,
        max_chunk_size=2000,
        chunk_adjust_factor=0.75
    )

@pytest.fixture
def chunker(test_settings):
    """Create chunker instance."""
    return HtmlChunker(test_settings)

def test_create_chunks_with_valid_html(chunker):
    """Test chunking with valid HTML."""
    # Create test HTML with multiple calendar rows
    rows = []
    for i in range(10):
        rows.append(f'''
            <div class="calendarRow">
                <h2>Event {i}</h2>
                <div class="event-details">
                    <p>Date: 2024-{i+1}-15</p>
                    <p>Location: Test Location {i}</p>
                </div>
            </div>
        ''')
    
    test_html = f'<div class="calendar-content">{"".join(rows)}</div>'
    chunks = chunker.create_chunks(test_html)
    
    assert len(chunks) > 0
    assert all('<div class="calendar-content">' in chunk for chunk in chunks)
    
    # Verify each chunk contains complete calendar rows
    for chunk in chunks:
        soup = BeautifulSoup(chunk, 'lxml')
        rows = soup.find_all('div', class_='calendarRow')
        assert len(rows) > 0
        assert all(row.find('h2') is not None for row in rows)

def test_create_chunks_with_large_rows(chunker):
    """Test chunking with unusually large rows."""
    # Create a row that's larger than the initial chunk size
    large_row = f'''
        <div class="calendarRow">
            <h2>Large Event</h2>
            <div class="event-details">
                {'<p>Large content</p>' * 50}
            </div>
        </div>
    '''
    
    test_html = f'<div class="calendar-content">{large_row * 3}</div>'
    chunks = chunker.create_chunks(test_html)
    
    assert len(chunks) > 1
    metrics = chunker.get_metrics()
    assert metrics['chunk_size_adjustments'] > 0
    assert metrics['avg_chunk_size'] <= chunker.settings.max_chunk_size

def test_create_chunks_with_invalid_html(chunker):
    """Test chunking with invalid HTML."""
    invalid_html = "<div>Unclosed div"
    chunks = chunker.create_chunks(invalid_html)
    
    # Should still work using BeautifulSoup fallback
    assert len(chunks) > 0
    assert all('<div class="calendar-content">' in chunk for chunk in chunks)

def test_empty_html(chunker):
    """Test handling of empty HTML."""
    with pytest.raises(ChunkingError):
        chunker.create_chunks("")

def test_html_without_calendar_rows(chunker):
    """Test HTML without calendar rows."""
    test_html = '''
        <div class="content">
            <h1>Some Content</h1>
            <p>But no calendar rows</p>
        </div>
    '''
    
    with pytest.raises(ChunkingError, match="No calendar rows found"):
        chunker.create_chunks(test_html)

def test_chunk_size_boundaries(chunker):
    """Test that chunk sizes stay within boundaries."""
    # Create rows of varying sizes
    rows = []
    for i in range(20):
        # Alternate between small and large rows
        content_multiplier = 1 if i % 2 == 0 else 10
        rows.append(f'''
            <div class="calendarRow">
                <h2>Event {i}</h2>
                <div class="event-details">
                    {'<p>Content</p>' * content_multiplier}
                </div>
            </div>
        ''')
    
    test_html = f'<div class="calendar-content">{"".join(rows)}</div>'
    chunks = chunker.create_chunks(test_html)
    
    # Verify chunk sizes
    for chunk in chunks:
        size = len(chunk)
        assert size >= chunker.settings.min_chunk_size
        assert size <= chunker.settings.max_chunk_size

def test_metrics_collection(chunker):
    """Test metrics collection."""
    rows = [f'<div class="calendarRow"><h2>Event {i}</h2></div>' for i in range(5)]
    test_html = f'<div class="calendar-content">{"".join(rows)}</div>'
    
    chunks = chunker.create_chunks(test_html)
    metrics = chunker.get_metrics()
    
    assert metrics['chunks_created'] == len(chunks)
    assert metrics['total_rows'] == 5
    assert metrics['avg_chunk_size'] > 0