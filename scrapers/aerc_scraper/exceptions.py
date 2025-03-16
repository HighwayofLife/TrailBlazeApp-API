"""Custom exceptions for the AERC scraper."""

class ScraperError(Exception):
    """Base exception for scraper errors."""
    pass

class NetworkError(ScraperError):
    """Raised when network requests fail."""
    pass

class DataExtractionError(ScraperError):
    """Raised when data extraction fails."""
    pass

class ValidationError(ScraperError):
    """Raised when data validation fails."""
    pass

class CacheError(ScraperError):
    """Raised when cache operations fail."""
    pass

class GeminiAPIError(ScraperError):
    """Raised when Gemini API calls fail."""
    pass

class DatabaseError(ScraperError):
    """Raised when database operations fail."""
    pass