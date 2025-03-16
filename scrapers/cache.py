"""Shared caching module with TTL support and cache validation."""

import os
import json
import hashlib
import logging
from typing import Any, Dict, Optional
from datetime import datetime, timedelta
from pathlib import Path

from .exceptions import CacheError
from .config import ScraperBaseSettings

logger = logging.getLogger(__name__)

class Cache:
    """Cache with TTL support and validation."""
    
    def __init__(self, settings: ScraperBaseSettings):
        self.settings = settings
        self.cache_dir = Path(settings.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.validation_dir = self.cache_dir / "validation"
        self.validation_dir.mkdir(exist_ok=True)
        
        self.metrics = {
            'hits': 0,
            'misses': 0,
            'expired': 0,
            'errors': 0,
            'total_size': 0,
            'entries': 0
        }
        
        # Initialize metrics with current cache state
        self._update_cache_metrics()
    
    def _get_cache_path(self, key: str) -> Path:
        """Get cache file path for a key."""
        hash_key = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{hash_key}.json"
    
    def _get_validation_path(self, key: str) -> Path:
        """Get validation file path for a key."""
        hash_key = hashlib.md5(key.encode()).hexdigest()
        return self.validation_dir / f"{hash_key}.validation"
    
    def _update_cache_metrics(self) -> None:
        """Update cache metrics based on current state."""
        total_size = 0
        entries = 0
        
        for file in self.cache_dir.glob("*.json"):
            try:
                total_size += file.stat().st_size
                entries += 1
            except OSError:
                continue
        
        self.metrics['total_size'] = total_size
        self.metrics['entries'] = entries
    
    def get(self, key: str, validate: bool = True) -> Optional[Any]:
        """Get value from cache if not expired."""
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
            
            # Check TTL
            cached_time = datetime.fromisoformat(cached_data['timestamp'])
            if datetime.now() - cached_time > timedelta(seconds=self.settings.cache_ttl):
                self.metrics['expired'] += 1
                logger.debug(f"Cache entry expired for key: {key}")
                return None
            
            # Validate cache if requested
            if validate and self.settings.validate_mode:
                validation_path = self._get_validation_path(key)
                if validation_path.exists():
                    with validation_path.open('r') as f:
                        validation_data = json.load(f)
                    
                    if not self._validate_cache(cached_data['value'], validation_data):
                        self.metrics['expired'] += 1
                        logger.warning(f"Cache validation failed for key: {key}")
                        return None
            
            self.metrics['hits'] += 1
            return cached_data['value']
            
        except Exception as e:
            self.metrics['errors'] += 1
            logger.error(f"Error reading from cache: {str(e)}")
            return None
    
    def set(self, key: str, value: Any, validation_data: Optional[Dict] = None) -> None:
        """Store value in cache with timestamp."""
        try:
            cache_path = self._get_cache_path(key)
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'value': value
            }
            
            with cache_path.open('w') as f:
                json.dump(cache_data, f)
            
            # Store validation data if provided
            if validation_data:
                validation_path = self._get_validation_path(key)
                with validation_path.open('w') as f:
                    json.dump(validation_data, f)
            
            self._update_cache_metrics()
            
        except Exception as e:
            self.metrics['errors'] += 1
            logger.error(f"Error writing to cache: {str(e)}")
            raise CacheError(f"Failed to store data in cache: {str(e)}")
    
    def invalidate(self, key: str) -> None:
        """Invalidate a cache entry."""
        try:
            cache_path = self._get_cache_path(key)
            validation_path = self._get_validation_path(key)
            
            if cache_path.exists():
                cache_path.unlink()
            if validation_path.exists():
                validation_path.unlink()
            
            self._update_cache_metrics()
            
        except Exception as e:
            self.metrics['errors'] += 1
            logger.error(f"Error invalidating cache: {str(e)}")
            raise CacheError(f"Failed to invalidate cache: {str(e)}")
    
    def clear(self) -> None:
        """Clear all cache entries."""
        try:
            # Only remove JSON and validation files, keep directories
            for file in self.cache_dir.glob("*.json"):
                file.unlink()
            for file in self.validation_dir.glob("*.validation"):
                file.unlink()
            
            self._update_cache_metrics()
            
        except Exception as e:
            self.metrics['errors'] += 1
            logger.error(f"Error clearing cache: {str(e)}")
            raise CacheError(f"Failed to clear cache: {str(e)}")
    
    def _validate_cache(self, cached_value: Any, validation_data: Dict) -> bool:
        """Validate cached data against validation rules."""
        try:
            if not validation_data:
                return True
            
            # Check data format
            if validation_data.get('format') == 'json':
                if not isinstance(cached_value, (dict, list)):
                    return False
            
            # Check expected length for lists
            if validation_data.get('expected_length'):
                if not isinstance(cached_value, list):
                    return False
                if len(cached_value) != validation_data['expected_length']:
                    return False
            
            # Check required fields
            if validation_data.get('required_fields'):
                if not isinstance(cached_value, (dict, list)):
                    return False
                    
                if isinstance(cached_value, list):
                    # Check each item in the list
                    for item in cached_value:
                        if not isinstance(item, dict):
                            return False
                        for field in validation_data['required_fields']:
                            if field not in item:
                                return False
                else:
                    # Check single dictionary
                    for field in validation_data['required_fields']:
                        if field not in cached_value:
                            return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error during cache validation: {str(e)}")
            return False
    
    def get_metrics(self) -> Dict[str, int]:
        """Get cache metrics."""
        # Calculate hit rate if we have any cache access
        total_access = self.metrics['hits'] + self.metrics['misses']
        if total_access > 0:
            self.metrics['hit_rate'] = (self.metrics['hits'] / total_access) * 100
            
        return self.metrics.copy()
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get detailed cache information."""
        return {
            'directory': str(self.cache_dir),
            'total_size_bytes': self.metrics['total_size'],
            'entries': self.metrics['entries'],
            'hit_rate': self.metrics.get('hit_rate', 0),
            'settings': {
                'ttl': self.settings.cache_ttl,
                'refresh': self.settings.refresh_cache,
                'validate': self.settings.validate_mode
            }
        }