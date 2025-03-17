"""Base scraper interface and abstract class."""

import abc
import logging
from typing import Dict, List, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.logging_config import get_logger

class BaseScraper(abc.ABC):
    """Abstract base class for all scrapers."""
    
    def __init__(self, source_name: str, logger=None):
        """Initialize base scraper."""
        self.source_name = source_name
        self.logger = logger or get_logger(f"scrapers.{source_name.lower().replace(' ', '_')}")
        self.start_time = datetime.now()
    
    @abc.abstractmethod
    async def run(self, db: AsyncSession) -> Dict[str, Any]:
        """Run the scraper end-to-end."""
        pass
    
    @abc.abstractmethod
    def get_metrics(self) -> Dict[str, Any]:
        """Get scraper metrics."""
        pass
    
    @abc.abstractmethod
    def clean_data(self, raw_data: str) -> str:
        """Clean and preprocess raw data."""
        pass
    
    @abc.abstractmethod
    def validate_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate extracted data."""
        pass
    
    @abc.abstractmethod
    def convert_to_db_schema(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert validated data to database schema."""
        pass