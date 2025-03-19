"""
Cache module with TTL support using cachetools.
"""

import os
import json
import time
import logging
import hashlib
from typing import Any, Optional, Dict
from pathlib import Path
from .config import ScraperSettings
from .exceptions import CacheError

logger = logging.getLogger(__name__)

class Cache:
    """File-based cache with TTL support."""

    def __init__(self, settings: ScraperSettings):
        self.settings = settings
        self.cache_dir = Path(settings.cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.metrics = {
            'hits': 0,
            'misses': 0,
            'expired': 0,
            'errors': 0
        }

    def _get_cache_path(self, key: str) -> Path:
        """Generate a cache file path for a given key."""
        hash_key = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{hash_key}.json"

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if it exists and is not expired."""
        if self.settings.refresh_cache:
            self.metrics['misses'] += 1
            return None

        try:
            cache_path = self._get_cache_path(key)
            if not cache_path.exists():
                self.metrics['misses'] += 1
                return None

            with cache_path.open('r') as f:
                cached_data = json.load(f)

            # Check if cache has expired
            if time.time() - cached_data['timestamp'] > self.settings.cache_ttl:
                self.metrics['expired'] += 1
                cache_path.unlink()  # Remove expired cache file
                return None

            self.metrics['hits'] += 1
            return cached_data['value']

        except Exception as e:
            self.metrics['errors'] += 1
            logger.error(f"Cache read error for key {key}: {e}")
            return None

    def set(self, key: str, value: Any) -> None:
        """Save value to cache with timestamp."""
        try:
            cache_path = self._get_cache_path(key)
            cached_data = {
                'timestamp': time.time(),
                'value': value
            }

            with cache_path.open('w') as f:
                json.dump(cached_data, f)

        except Exception as e:
            self.metrics['errors'] += 1
            logger.error(f"Cache write error for key {key}: {e}")
            raise CacheError(f"Failed to write to cache: {str(e)}")

    def clear(self) -> None:
        """Clear all cached data."""
        try:
            for cache_file in self.cache_dir.glob('*.json'):
                cache_file.unlink()
        except Exception as e:
            raise CacheError(f"Failed to clear cache: {str(e)}")

    def get_metrics(self) -> Dict[str, int]:
        """Get cache operation metrics."""
        return self.metrics.copy()
