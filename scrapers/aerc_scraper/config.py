"""
Configuration management for AERC scraper using pydantic settings.
"""

from pydantic_settings import BaseSettings
from typing import List, Dict, Any
from functools import lru_cache

class ScraperSettings(BaseSettings):
    """Scraper configuration settings."""
    # Network settings
    max_retries: int = 3
    retry_delay: int = 5
    request_timeout: int = 30
    
    # Gemini API settings
    gemini_api_key: str = ""
    primary_model: str = "gemini-2.0-flash-lite"
    fallback_model: str = "gemini-2.0-flash"
    temperature: float = 0.1
    max_output_tokens: int = 8192
    
    # Chunking settings
    initial_chunk_size: int = 30000
    min_chunk_size: int = 15000
    max_chunk_size: int = 45000
    chunk_adjust_factor: float = 0.75
    
    # Cache settings
    cache_ttl: int = 3600  # 1 hour in seconds
    cache_dir: str = "cache"
    
    # Debug settings
    debug_mode: bool = False
    refresh_cache: bool = False
    validate_mode: bool = False
    
    # HTTP Headers
    default_headers: Dict[str, str] = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Referer": "https://aerc.org/",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1"
    }
    
    # URLs
    base_url: str = "https://aerc.org/wp-admin/admin-ajax.php"
    calendar_url: str = "https://aerc.org/calendar"
    
    class Config:
        env_prefix = "AERC_"
        case_sensitive = False
        env_file = ".env"
        extra = "ignore"  # Allow extra fields in validation

@lru_cache()
def get_settings() -> ScraperSettings:
    """Get cached settings instance."""
    return ScraperSettings()