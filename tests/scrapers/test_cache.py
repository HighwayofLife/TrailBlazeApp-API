"""Tests for shared caching module."""

import pytest
import json
from datetime import datetime, timedelta
from pathlib import Path
from scrapers.cache import Cache
from scrapers.config import ScraperBaseSettings
from scrapers.exceptions import CacheError

@pytest.fixture
def test_settings():
    """Create test settings."""
    return ScraperBaseSettings(
        cache_ttl=60,  # 1 minute TTL for testing
        cache_dir="tests/temp_cache",
        refresh_cache=False,
        debug_mode=True,
        validate_mode=True
    )

@pytest.fixture
def cache(test_settings, tmp_path):
    """Create cache instance with temporary directory."""
    test_settings.cache_dir = str(tmp_path)
    return Cache(test_settings)

def test_cache_set_and_get(cache):
    """Test basic cache set and get operations."""
    test_data = {"test": "value"}
    cache.set("test_key", test_data)
    
    result = cache.get("test_key")
    assert result == test_data
    
    metrics = cache.get_metrics()
    assert metrics['hits'] == 1
    assert metrics['misses'] == 0

def test_cache_ttl(cache):
    """Test cache TTL expiration."""
    test_data = {"test": "value"}
    cache.set("test_key", test_data)
    
    # Modify cached file timestamp to be older than TTL
    cache_path = cache._get_cache_path("test_key")
    cached = json.loads(cache_path.read_text())
    cached['timestamp'] = (
        datetime.now() - timedelta(seconds=cache.settings.cache_ttl + 1)
    ).isoformat()
    cache_path.write_text(json.dumps(cached))
    
    result = cache.get("test_key")
    assert result is None
    
    metrics = cache.get_metrics()
    assert metrics['expired'] == 1

def test_cache_validation(cache):
    """Test cache validation."""
    test_data = {"name": "test", "value": 123}
    validation_data = {
        "format": "json",
        "required_fields": ["name", "value"]
    }
    
    cache.set("test_key", test_data, validation_data)
    result = cache.get("test_key", validate=True)
    assert result == test_data
    
    # Test with invalid data
    invalid_data = {"wrong": "format"}
    cache.set("invalid_key", invalid_data, validation_data)
    result = cache.get("invalid_key", validate=True)
    assert result is None

def test_cache_invalidate(cache):
    """Test cache invalidation."""
    test_data = {"test": "value"}
    cache.set("test_key", test_data)
    
    cache.invalidate("test_key")
    result = cache.get("test_key")
    assert result is None
    
    metrics = cache.get_metrics()
    assert metrics['entries'] == 0

def test_cache_clear(cache):
    """Test clearing all cache entries."""
    # Add multiple entries
    for i in range(3):
        cache.set(f"key_{i}", {"test": i})
    
    cache.clear()
    
    # Verify all entries are gone
    for i in range(3):
        assert cache.get(f"key_{i}") is None
    
    metrics = cache.get_metrics()
    assert metrics['entries'] == 0
    assert metrics['total_size'] == 0

def test_cache_metrics(cache):
    """Test cache metrics collection."""
    # Mix of hits, misses, and errors
    test_data = {"test": "value"}
    cache.set("test_key", test_data)
    
    cache.get("test_key")  # Hit
    cache.get("missing_key")  # Miss
    cache.get("test_key")  # Hit
    
    metrics = cache.get_metrics()
    assert metrics['hits'] == 2
    assert metrics['misses'] == 1
    assert metrics['hit_rate'] == (2 / 3) * 100

def test_cache_errors(cache):
    """Test error handling."""
    with pytest.raises(CacheError):
        # Try to write to a non-existent directory
        bad_settings = ScraperBaseSettings(cache_dir="/nonexistent/path")
        bad_cache = Cache(bad_settings)
        bad_cache.set("test_key", {"test": "value"})