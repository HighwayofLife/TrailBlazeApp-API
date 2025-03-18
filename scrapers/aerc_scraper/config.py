"""Configuration management for AERC scraper."""
from functools import lru_cache
from typing import Dict, Any
from pydantic_settings import BaseSettings
from scrapers.config import ScraperBaseSettings, ScraperSettings

# Alias for backward compatibility
ScraperSettings = ScraperBaseSettings

class AERCScraperSettings(ScraperSettings):
    """AERC-specific scraper settings."""
    
    # AERC API settings
    gemini_api_key: str = ""
    primary_model: str = "gemini-2.0-flash-lite"
    fallback_model: str = "gemini-2.0-flash"
    temperature: float = 0.1
    max_output_tokens: int = 8192
    
    # Use AI for extraction (set to False to use only HTML parser)
    use_ai_extraction: bool = False
    
    # Network settings
    request_timeout: int = 30
    retry_delay: int = 2
    
    # Cache settings
    refresh_cache: bool = False
    
    # Chunking settings
    initial_chunk_size: int = 10000  # Initial HTML chunk size in characters (for first level chunking)
    min_chunk_size: int = 5000      # Minimum HTML chunk size (used for further chunking when needed)
    max_chunk_size: int = 15000     # Maximum HTML chunk size (upper bound for any chunking operation)
    html_chunk_size: int = 5000     # Standard HTML chunk size for direct use by GeminiClient
    chunk_adjust_factor: float = 0.75  # Factor to adjust chunk size when needed (multiplier)
    
    # AERC URLs
    base_url: str = "https://aerc.org/wp-admin/admin-ajax.php"
    calendar_url: str = "https://aerc.org/calendar"
    
    # Additional headers for AERC site
    @property
    def http_headers(self) -> Dict[str, str]:
        """Get headers for AERC requests."""
        headers = self.default_headers.copy()
        headers.update({
            "Referer": "https://aerc.org/",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1"
        })
        return headers
    
    class Config:
        env_prefix = "AERC_"
        case_sensitive = False
        env_file = ".env"
        extra = "ignore"  # Ignore unknown fields

@lru_cache()
def get_settings(base_settings: ScraperSettings = None) -> AERCScraperSettings:
    """Get cached settings instance."""
    return AERCScraperSettings()