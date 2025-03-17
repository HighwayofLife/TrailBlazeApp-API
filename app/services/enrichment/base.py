"""Base class for event enrichment services."""
import logging
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

from app.models import Event

logger = logging.getLogger(__name__)

class EnrichmentService(ABC):
    """Base class for services that enrich event data."""
    
    def __init__(self):
        """Initialize the enrichment service."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
    @abstractmethod
    async def enrich_event(self, event: Event) -> bool:
        """
        Enrich a single event with additional data.
        
        Args:
            event: The Event object to enrich
            
        Returns:
            True if enrichment was successful, False otherwise
        """
        pass
        
    async def enrich_events(self, events: List[Event]) -> Dict[str, Any]:
        """
        Enrich multiple events with additional data.
        
        Args:
            events: List of Event objects to enrich
            
        Returns:
            Dictionary containing statistics about the enrichment process
        """
        total = len(events)
        successful = 0
        failed = 0
        
        self.logger.info(f"Starting enrichment of {total} events")
        
        for event in events:
            try:
                success = await self.enrich_event(event)
                if success:
                    successful += 1
                else:
                    failed += 1
            except Exception as e:
                self.logger.exception(f"Error enriching event {event.id}: {str(e)}")
                failed += 1
                
        result = {
            "total": total,
            "successful": successful,
            "failed": failed,
            "success_rate": (successful / total) * 100 if total > 0 else 0
        }
        
        self.logger.info(f"Enrichment complete: {result}")
        return result 