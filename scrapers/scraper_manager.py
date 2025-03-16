"""Scraper manager module for coordinating scraper execution."""

import logging
from typing import Dict, List, Any, Type, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from .base_scraper import BaseScraper
from .aerc_scraper import AERCScraper
from .exceptions import ScraperError

logger = logging.getLogger(__name__)

class ScraperManager:
    """Manages scraper registration and execution."""
    
    def __init__(self):
        """Initialize scraper manager."""
        self._scrapers: Dict[str, Type[BaseScraper]] = {}
        self._results: Dict[str, Dict[str, Any]] = {}
        self.start_time = datetime.now()
    
    def register_scraper(self, scraper_id: str, scraper_class: Type[BaseScraper]) -> None:
        """Register a scraper with the manager."""
        if scraper_id in self._scrapers:
            logger.warning(f"Overwriting existing scraper registration for {scraper_id}")
        self._scrapers[scraper_id] = scraper_class
        logger.info(f"Registered scraper: {scraper_id}")
    
    def get_registered_scrapers(self) -> List[str]:
        """Get list of registered scraper IDs."""
        return list(self._scrapers.keys())
    
    async def run_scraper(self, scraper_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Run a specific scraper."""
        try:
            if scraper_id not in self._scrapers:
                raise ScraperError(f"No scraper registered for ID: {scraper_id}")
            
            scraper_class = self._scrapers[scraper_id]
            scraper = scraper_class()
            
            logger.info(f"Running scraper: {scraper_id}")
            result = await scraper.run(db)
            
            self._results[scraper_id] = {
                "timestamp": datetime.now().isoformat(),
                "metrics": scraper.get_metrics(),
                "status": result.get("status", "unknown"),
                "events_found": result.get("events_found", 0),
                "events_valid": result.get("events_valid", 0),
                "events_added": result.get("events_added", 0),
                "events_updated": result.get("events_updated", 0)
            }
            
            return result
            
        except Exception as e:
            logger.exception(f"Error running scraper {scraper_id}: {e}")
            self._results[scraper_id] = {
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": str(e)
            }
            raise ScraperError(f"Failed to run scraper {scraper_id}: {str(e)}")
    
    async def run_all_scrapers(self, db: AsyncSession) -> Dict[str, Any]:
        """Run all registered scrapers."""
        overall_results = {
            "start_time": self.start_time.isoformat(),
            "end_time": None,
            "scrapers": {},
            "total_events_found": 0,
            "total_events_added": 0,
            "errors": []
        }
        
        for scraper_id in self._scrapers:
            try:
                result = await self.run_scraper(scraper_id, db)
                overall_results["scrapers"][scraper_id] = result
                if result.get("status") == "success":
                    overall_results["total_events_found"] += result.get("events_found", 0)
                    overall_results["total_events_added"] += result.get("events_added", 0)
            except Exception as e:
                overall_results["errors"].append({
                    "scraper": scraper_id,
                    "error": str(e)
                })
        
        overall_results["end_time"] = datetime.now().isoformat()
        return overall_results
    
    def get_results(self, scraper_id: Optional[str] = None) -> Dict[str, Any]:
        """Get results for a specific scraper or all scrapers."""
        if scraper_id:
            return self._results.get(scraper_id, {})
        return self._results.copy()
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary metrics across all scrapers."""
        summary = {
            "total_events_found": 0,
            "total_events_valid": 0,
            "total_events_added": 0,
            "total_events_updated": 0,
            "errors": 0,
            "success_rate": 0
        }
        
        for result in self._results.values():
            metrics = result.get("metrics", {})
            summary["total_events_found"] += metrics.get("events_found", 0)
            summary["total_events_valid"] += metrics.get("events_valid", 0)
            summary["total_events_added"] += metrics.get("events_added", 0)
            summary["total_events_updated"] += metrics.get("events_updated", 0)
            if result.get("status") == "error":
                summary["errors"] += 1
        
        if summary["total_events_found"] > 0:
            summary["success_rate"] = (
                summary["total_events_valid"] / summary["total_events_found"]
            ) * 100
            
        return summary