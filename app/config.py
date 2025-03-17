import os
from pydantic_settings import BaseSettings
from functools import lru_cache
# Load environment variables from .env file
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """Application settings configuration using Pydantic.
    
    This centralizes all environment variables and configuration settings.
    Values can be overridden by environment variables with the same name.
    """
    # Database settings - using Docker service name (db) when running in container
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql+asyncpg://postgres:postgres@db/trailblaze" 
        if os.getenv("DOCKER_ENV") == "true" 
        else "postgresql+asyncpg://postgres:postgres@localhost/trailblaze"
    )
    
    # API settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "TrailBlaze API"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # CORS settings
    CORS_ORIGINS: list[str] = [
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:8000",
        "https://trailblaze.app",
    ]
    
    # Gemini AI settings
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = "gemini-2.0-flash"
    
    # Add lowercase version for compatibility
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Scraping settings
    SCRAPING_SCHEDULE: str = "0 0 * * *"  # Daily at midnight
    
    # Geocoding settings
    GEOCODING_PROVIDER: str = os.getenv("GEOCODING_PROVIDER", "nominatim")  # nominatim or google
    GEOCODING_USER_AGENT: str = os.getenv("GEOCODING_USER_AGENT", "TrailBlazeApp")  # Required for Nominatim
    GEOCODING_API_KEY: str = os.getenv("GEOCODING_API_KEY", "")  # Required for Google
    GEOCODING_TIMEOUT: int = int(os.getenv("GEOCODING_TIMEOUT", "5"))
    GEOCODING_RETRIES: int = int(os.getenv("GEOCODING_RETRIES", "3"))
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields in validation


@lru_cache
def get_settings() -> Settings:
    """Create cached instance of settings.
    
    Returns:
        Settings: Application settings
    """
    return Settings()
