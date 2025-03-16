"""Tests for cache module."""

import pytest
import time
import json
from pathlib import Path
import shutil
from scrapers.aerc_scraper.cache import Cache
from scrapers.aerc_scraper.exceptions import CacheError

@pytest.fixture
def test_cache_dir():
    """Create and clean up test cache directory."""
    cache_dir = Path("tests/temp_cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    yield cache_dir
    shutil.rmtree(cache_dir)

@pytest.fixture
def test_cache(test_settings, test_cache_dir):
    """Create cache instance with test settings."""
    test_settings.cache_dir = str(test_cache_dir)
    test_settings.refresh_cache = False
    return Cache(test_settings)

def test_cache_set_get(test_cache):
    """Test setting and getting cache values."""
    key = "test_key"
    value = {"data": "test_value"}
    
    test_cache.set(key, value)
    cached = test_cache.get(key)
    
    assert cached == value
    assert test_cache.get_metrics()['hits'] == 1

def test_cache_ttl(test_cache, test_settings):
    """Test cache TTL expiration."""
    test_settings.cache_ttl = 1  # 1 second TTL
    key = "ttl_test"
    value = {"data": "expires_soon"}
    
    test_cache.set(key, value)
    time.sleep(1.1)  # Wait for TTL to expire
    
    assert test_cache.get(key) is None
    assert test_cache.get_metrics()['expired'] == 1

def test_cache_refresh_mode(test_settings, test_cache_dir):
    """Test cache refresh mode."""
    test_settings.cache_dir = str(test_cache_dir)
    test_settings.refresh_cache = True
    refresh_cache = Cache(test_settings)
    
    key = "refresh_test"
    value = {"data": "should_not_cache"}
    
    refresh_cache.set(key, value)
    assert refresh_cache.get(key) is None
    assert refresh_cache.get_metrics()['misses'] == 1

def test_cache_clear(test_cache):
    """Test clearing cache."""
    keys = ["key1", "key2", "key3"]
    value = {"data": "test"}
    
    for key in keys:
        test_cache.set(key, value)
    
    test_cache.clear()
    
    for key in keys:
        assert test_cache.get(key) is None
    assert test_cache.get_metrics()['misses'] == len(keys)

def test_invalid_json(test_cache):
    """Test handling invalid JSON in cache file."""
    key = "invalid_json"
    cache_path = test_cache._get_cache_path(key)
    
    # Write invalid JSON
    with cache_path.open('w') as f:
        f.write("invalid{json")
    
    assert test_cache.get(key) is None
    assert test_cache.get_metrics()['errors'] == 1

def test_metrics_collection(test_cache):
    """Test metrics collection."""
    key = "metrics_test"
    value = {"data": "test"}
    
    # Test cache miss
    assert test_cache.get(key) is None
    assert test_cache.get_metrics()['misses'] == 1
    
    # Test cache hit
    test_cache.set(key, value)
    assert test_cache.get(key) == value
    assert test_cache.get_metrics()['hits'] == 1
    
    # Test cache error
    with pytest.raises(CacheError):
        test_cache.set("bad/key\0", value)
    assert test_cache.get_metrics()['errors'] == 1

def test_concurrent_access(test_cache):
    """Test concurrent access patterns."""
    key = "concurrent_test"
    values = [{"data": f"value_{i}"} for i in range(5)]
    
    # Simulate concurrent writes
    for value in values:
        test_cache.set(key, value)
    
    # Should have the last value written
    assert test_cache.get(key) == values[-1]

def test_large_values(test_cache):
    """Test handling large cache values."""
    key = "large_value"
    large_value = {
        "data": "x" * 1024 * 1024  # 1MB of data
    }
    
    test_cache.set(key, large_value)
    cached = test_cache.get(key)
    
    assert cached == large_value

def test_cache_directory_creation(test_settings):
    """Test cache directory creation."""
    test_dir = Path("tests/new_cache_dir")
    test_settings.cache_dir = str(test_dir)
    
    try:
        cache = Cache(test_settings)
        assert test_dir.exists()
        assert test_dir.is_dir()
    finally:
        if test_dir.exists():
            shutil.rmtree(test_dir)