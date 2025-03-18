"""AERC Calendar Scraper package."""

from .parser_v2.main_v2 import AERCScraperV2 as AERCScraper
from .config import ScraperSettings, get_settings
from .metrics import ScraperMetrics
from .exceptions import (
    ScraperError,
    NetworkError,
    DataExtractionError,
    ValidationError,
    CacheError,
    AIError,
    DatabaseError
)

__all__ = [
    'AERCScraper',  # Expose V2 as the default scraper
    'ScraperSettings',
    'get_settings',
    'ScraperMetrics',
    'ScraperError',
    'NetworkError',
    'DataExtractionError',
    'ValidationError',
    'CacheError',
    'AIError',
    'DatabaseError'
]

__version__ = '1.0.0'
