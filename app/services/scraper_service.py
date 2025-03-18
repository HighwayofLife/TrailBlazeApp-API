"""Service for managing and running data scrapers."""

from typing import Dict, List, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.logging_config import get_logger
from scrapers.scraper_manager import ScraperManager
from scrapers.aerc_scraper.parser_v2.main_v2 import AERCScraperV2
from scrapers.exceptions import ScraperError

logger = get_logger("services.scraper")

# Initialize and configure scraper manager
_scraper_manager = ScraperManager()
_scraper_manager.register_scraper("aerc_calendar", AERCScraperV2)

async def run_scraper(scraper_id: str, db: AsyncSession) -> Dict[str, Any]:
    """Run a specific scraper."""
    try:
        logger.info(f"Running scraper: {scraper_id}")
        result = await _scraper_manager.run_scraper(scraper_id, db)
        
        logger.info(f"Scraper {scraper_id} completed successfully")
        return {
            "status": "success",
            "scraper": scraper_id,
            "events_found": result.get("events_found", 0),
            "events_added": result.get("events_added", 0),
            "events_updated": result.get("events_updated", 0)
        }
    except ScraperError as e:
        logger.error(f"Error running scraper {scraper_id}: {str(e)}")
        return {
            "status": "error",
            "scraper": scraper_id,
            "message": str(e)
        }
    except Exception as e:
        logger.exception(f"Unexpected error running scraper {scraper_id}: {str(e)}")
        return {
            "status": "error",
            "scraper": scraper_id,
            "message": f"Unexpected error: {str(e)}"
        }

async def run_all_scrapers(db: AsyncSession) -> Dict[str, Any]:
    """Run all registered scrapers."""
    try:
        logger.info("Running all scrapers")
        results = await _scraper_manager.run_all_scrapers(db)
        
        # Get summary metrics
        metrics = _scraper_manager.get_metrics_summary()
        
        return {
            "status": "success",
            "scrapers_run": len(results.get("scrapers", {})),
            "total_events_found": metrics["total_events_found"],
            "total_events_added": metrics["total_events_added"],
            "success_rate": metrics["success_rate"],
            "errors": len(results.get("errors", [])),
            "error_details": results.get("errors", [])
        }
    except Exception as e:
        logger.exception(f"Error running scrapers: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }

def get_available_scrapers() -> List[str]:
    """Get list of registered scraper IDs."""
    return _scraper_manager.get_registered_scrapers()

def get_scraper_results(scraper_id: str = None) -> Dict[str, Any]:
    """Get results for a specific scraper or all scrapers."""
    return _scraper_manager.get_results(scraper_id)
