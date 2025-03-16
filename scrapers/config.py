"""Shared configuration module for scrapers."""

import os
import yaml
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import Field, validator

from .exceptions import ConfigError

class ScraperBaseSettings(BaseSettings):
    """Base settings for all scrapers."""
    
    # Base paths
    cache_dir: str = "cache"
    logs_dir: str = "logs"
    metrics_dir: str = "logs/metrics"
    
    # Database settings
    database_url: str
    
    # Network settings
    requests_per_second: float = 1.0
    max_burst_size: int = 5
    max_retries: int = 3
    timeout_seconds: int = 30
    
    # Default headers
    default_headers: Dict[str, str] = {
        "User-Agent": "TrailBlazeApp/1.0",
        "Accept": "text/html,application/json",
        "Accept-Language": "en-US,en;q=0.9"
    }
    
    # Cache settings
    cache_ttl: int = 3600
    force_refresh: bool = False
    
    # Debug settings
    debug_mode: bool = False
    validate_data: bool = True
    
    class Config:
        env_prefix = "SCRAPER_"
        case_sensitive = False
        env_file = ".env"

class ScraperSettings(BaseSettings):
    """Base settings for all scrapers."""
    
    # Database settings
    database_url: str = Field(
        ...,  # Required
        description="Database connection URL"
    )
    
    # Rate limiting settings
    requests_per_second: float = Field(
        default=1.0,
        ge=0.1,
        le=10.0,
        description="Maximum requests per second"
    )
    max_burst_size: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum burst size for rate limiting"
    )
    max_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum number of retries for failed requests"
    )
    
    # Cache settings
    cache_dir: str = Field(
        default="cache",
        description="Directory for caching data"
    )
    cache_ttl: int = Field(
        default=3600,
        ge=60,
        le=86400,
        description="Cache TTL in seconds"
    )
    
    # Logging settings
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )
    log_file: Optional[str] = Field(
        default=None,
        description="Log file path"
    )
    
    # AI settings
    use_ai_extraction: bool = Field(
        default=False,
        description="Whether to use AI for data extraction"
    )
    gemini_api_key: Optional[str] = Field(
        default=None,
        description="Google Gemini API key"
    )
    
    # HTML processing settings
    chunk_size: int = Field(
        default=5000,
        ge=1000,
        le=50000,
        description="Size of HTML chunks for processing"
    )
    max_chunks: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of chunks to process"
    )
    
    # Scraper-specific settings
    scraper_settings: Dict[str, Any] = Field(
        default_factory=dict,
        description="Scraper-specific settings"
    )
    
    @validator('database_url')
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL format."""
        if not v.startswith(('postgresql://', 'postgresql+asyncpg://')):
            raise ConfigError("Database URL must be PostgreSQL")
        return v
    
    @validator('log_level')
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
        if v.upper() not in valid_levels:
            raise ConfigError(f"Invalid log level. Must be one of: {valid_levels}")
        return v.upper()
    
    @validator('gemini_api_key')
    def validate_gemini_key(cls, v: Optional[str], values: Dict[str, Any]) -> Optional[str]:
        """Validate Gemini API key if AI extraction is enabled."""
        if values.get('use_ai_extraction', False) and not v:
            raise ConfigError("Gemini API key required when AI extraction is enabled")
        return v
    
    @classmethod
    def from_yaml(cls, path: str) -> 'ScraperSettings':
        """Load settings from YAML file."""
        try:
            path = Path(path)
            if not path.exists():
                raise ConfigError(f"Config file not found: {path}")
            
            with open(path) as f:
                config = yaml.safe_load(f)
            
            # Override with environment variables
            for key in cls.__fields__:
                env_key = f"SCRAPER_{key.upper()}"
                if env_key in os.environ:
                    config[key] = os.environ[env_key]
            
            return cls(**config)
            
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML format: {str(e)}")
        except Exception as e:
            raise ConfigError(f"Failed to load config: {str(e)}")
    
    def get_scraper_setting(self, scraper_name: str, key: str, default: Any = None) -> Any:
        """Get a scraper-specific setting."""
        scraper_config = self.scraper_settings.get(scraper_name, {})
        return scraper_config.get(key, default)
    
    def update_scraper_settings(self, scraper_name: str, settings: Dict[str, Any]) -> None:
        """Update scraper-specific settings."""
        if scraper_name not in self.scraper_settings:
            self.scraper_settings[scraper_name] = {}
        self.scraper_settings[scraper_name].update(settings)
    
    def to_yaml(self, path: str) -> None:
        """Save settings to YAML file."""
        try:
            config = self.dict(exclude_none=True)
            
            with open(path, 'w') as f:
                yaml.safe_dump(config, f, default_flow_style=False)
                
        except Exception as e:
            raise ConfigError(f"Failed to save config: {str(e)}")