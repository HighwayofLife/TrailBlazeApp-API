"""AERC event scraper main module."""

import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..config import ScraperSettings
from ..database import DatabaseHandler
from ..metrics import MetricsCollector
from ..rate_limiter import RateLimiter
from ..exceptions import (
    ScraperError,
    ValidationError,
    DatabaseError,
    NetworkError
)

from .network import NetworkHandler
from .validator import DataValidator
from .html_cleaner import HTMLCleaner
from .chunking import HtmlChunker
from .parser import EventParser
from .gemini_api import GeminiAPI

logger = logging.getLogger(__name__)

class AERCScraper:
    """AERC ride calendar scraper implementation."""
    
    def __init__(
        self,
        settings: ScraperSettings,
        session: AsyncSession,
        metrics_dir: Optional[str] = None
    ):
        """Initialize AERC scraper."""
        self.settings = settings
        self.session = session
        
        # Initialize components
        self.db = DatabaseHandler()
        self.metrics = MetricsCollector(
            source="AERC",
            metrics_dir=metrics_dir or "logs/metrics"
        )
        self.rate_limiter = RateLimiter(
            requests_per_second=settings.requests_per_second,
            max_burst=settings.max_burst_size
        )
        
        self.network = NetworkHandler(
            rate_limiter=self.rate_limiter,
            cache_dir=settings.cache_dir
        )
        self.cleaner = HTMLCleaner()
        self.chunker = HtmlChunker(settings)
        self.parser = EventParser()
        self.validator = DataValidator()
        
        if settings.use_ai_extraction:
            self.gemini = GeminiAPI(settings.gemini_api_key)
        else:
            self.gemini = None
    
    async def scrape(self) -> Dict[str, Any]:
        """Run the scraper and return results."""
        try:
            # Fetch and preprocess calendar page
            html = await self.network.fetch_calendar()
            cleaned_html = self.cleaner.clean(html)
            
            # Split into manageable chunks
            chunks = self.chunker.create_chunks(cleaned_html)
            self.metrics.update_network_metrics(self.network.get_metrics())
            
            # Extract events from chunks
            raw_events = []
            for chunk in chunks:
                if self.gemini:
                    # Use AI extraction
                    events = await self.gemini.extract_events(chunk)
                else:
                    # Use traditional parsing
                    events = self.parser.parse_chunk(chunk)
                raw_events.extend(events)
            
            # Validate events
            valid_events = self.validator.validate_events(raw_events)
            self.metrics.update_validation_metrics(self.validator.get_metrics())
            
            # Store events
            results = await self.db.store_events(valid_events, self.session)
            self.metrics.update_storage_metrics(self.db.get_metrics())
            
            # Log summary and save metrics
            self.metrics.log_summary()
            self.metrics.save_metrics()
            
            return {
                'success': True,
                'events_found': len(raw_events),
                'events_valid': len(valid_events),
                'events_stored': results['added'] + results['updated'],
                'run_id': datetime.now().strftime('%Y%m%d_%H%M%S')
            }
            
        except NetworkError as e:
            logger.error(f"Network error: {str(e)}")
            return {'success': False, 'error': str(e)}
            
        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            return {'success': False, 'error': str(e)}
            
        except DatabaseError as e:
            logger.error(f"Database error: {str(e)}")
            return {'success': False, 'error': str(e)}
            
        except Exception as e:
            logger.exception("Unexpected error during scraping")
            return {'success': False, 'error': str(e)}
        
        finally:
            # Clean up
            await self.network.close()
            if self.gemini:
                await self.gemini.close()

async def run_scraper(
    settings_path: str = "config.yaml",
    metrics_dir: Optional[str] = None
) -> Dict[str, Any]:
    """Run the AERC scraper.
    
    Args:
        settings_path: Path to settings file
        metrics_dir: Directory for metrics output
        
    Returns:
        Dictionary with scraping results
    """
    try:
        # Load settings
        settings = ScraperSettings.from_yaml(settings_path)
        
        # Initialize database
        db = DatabaseHandler(settings.database_url)
        async with db._session_factory() as session:
            # Run scraper
            scraper = AERCScraper(settings, session, metrics_dir)
            return await scraper.scrape()
            
    except Exception as e:
        logger.exception("Failed to run scraper")
        return {'success': False, 'error': str(e)}

if __name__ == "__main__":
    asyncio.run(run_scraper())