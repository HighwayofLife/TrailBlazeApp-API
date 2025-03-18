"""Shared exceptions for scraper modules."""

class ScraperError(Exception):
    """Base exception for all scraper errors."""
    pass

class NetworkError(ScraperError):
    """Raised when network operations fail."""
    pass

class ValidationError(ScraperError):
    """Raised when data validation fails."""
    pass

class DatabaseError(ScraperError):
    """Raised when database operations fail."""
    pass

class ConfigError(ScraperError):
    """Raised when configuration is invalid."""
    pass

class CacheError(ScraperError):
    """Raised when cache operations fail."""
    pass

class ParserError(ScraperError):
    """Raised when parsing operations fail."""
    pass

class RateLimitError(ScraperError):
    """Raised when rate limits are exceeded."""
    pass

class AIError(ScraperError):
    """Raised when AI operations fail."""
    pass

class DataExtractionError(ScraperError):
    """Raised when data extraction operations fail."""
    pass

class ChunkingError(ScraperError):
    """Raised when HTML chunking operations fail."""
    pass