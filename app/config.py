import os
from pydantic_settings import BaseSettings
from functools import lru_cache

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    """Application settings configuration using Pydantic.
    
    This centralizes all environment variables and configuration settings.
    Values can be overridden by environment variables with the same name.
    """
    # Database settings
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql+asyncpg://postgres:postgres@db/trailblaze"
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
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Scraping settings
    SCRAPING_SCHEDULE: str = "0 0 * * *"  # Daily at midnight
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache
def get_settings() -> Settings:
    """Create cached instance of settings.
    
    Returns:
        Settings: Application settings
    """
    return Settings()
