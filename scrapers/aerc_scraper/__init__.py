"""AERC Calendar Scraper package."""

from .scraper import AERCScraper, run_aerc_scraper
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
    'AERCScraper',
    'run_aerc_scraper',
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
