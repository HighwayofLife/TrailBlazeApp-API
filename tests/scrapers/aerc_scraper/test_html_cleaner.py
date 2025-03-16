"""Tests for HTML cleaning module."""

import pytest
from scrapers.aerc_scraper.html_cleaner import HtmlCleaner
from scrapers.aerc_scraper.exceptions import DataExtractionError

def test_clean_empty_html():
    """Test cleaning empty HTML."""
    cleaner = HtmlCleaner()
    with pytest.raises(DataExtractionError, match="No HTML content provided"):
        cleaner.clean("")

def test_clean_invalid_html():
    """Test cleaning invalid HTML."""
    cleaner = HtmlCleaner()
    html = "<div>Test<div"  # Invalid HTML
    cleaned = cleaner.clean(html)
    assert "Test" in cleaned
    assert cleaner.get_metrics()['cleaned_size'] > 0

def test_clean_no_calendar_rows():
    """Test cleaning HTML with no calendar rows."""
    cleaner = HtmlCleaner()
    html = "<div>Some content without calendar rows</div>"
    with pytest.raises(DataExtractionError, match="No calendar rows found"):
        cleaner.clean(html)

def test_clean_with_calendar_rows(test_html):
    """Test cleaning HTML with calendar rows."""
    cleaner = HtmlCleaner()
    cleaned = cleaner.clean(test_html)
    
    assert 'calendarRow' in cleaned
    assert '<script>' not in cleaned
    assert '<style>' not in cleaned
    assert cleaner.get_metrics()['rows_found'] > 0

def test_remove_unwanted_elements():
    """Test removing unwanted elements."""
    cleaner = HtmlCleaner()
    html = """
    <div>
        <script>alert('test');</script>
        <style>body { color: red; }</style>
        <nav>Navigation</nav>
        <header>Header</header>
        <footer>Footer</footer>
        <div class="calendarRow">Event</div>
    </div>
    """
    cleaned = cleaner.clean(html)
    
    assert 'script' not in cleaned.lower()
    assert 'style' not in cleaned.lower()
    assert 'navigation' not in cleaned.lower()
    assert 'header' not in cleaned.lower()
    assert 'footer' not in cleaned.lower()
    assert 'Event' in cleaned

def test_metrics_collection():
    """Test metrics collection."""
    cleaner = HtmlCleaner()
    html = '<div class="calendarRow">Test Event</div>'
    cleaner.clean(html)
    
    metrics = cleaner.get_metrics()
    assert metrics['rows_found'] == 1
    assert metrics['cleaned_size'] > 0

def test_handle_malformed_html():
    """Test handling malformed HTML."""
    cleaner = HtmlCleaner()
    html = """
    <div class="calendarRow">
        <p>Unclosed paragraph
        <div>Nested unclosed div
        <span>Test</span>
    </div>
    """
    cleaned = cleaner.clean(html)
    
    assert 'Test' in cleaned
    assert cleaned.count('<div') == cleaned.count('</div>')
    assert cleaned.count('<p') == cleaned.count('</p>')
    assert cleaned.count('<span') == cleaned.count('</span>')