"""Geocoding enrichment service for events."""
import logging
from typing import Optional

from app.models import Event
from app.services.enrichment.base import EnrichmentService
from app.services.geocoding import GeocodingService

logger = logging.getLogger(__name__)

class GeocodingEnrichmentService(EnrichmentService):
    """Service for enriching events with geocoding data."""
    
    def __init__(self):
        """Initialize the geocoding enrichment service."""
        super().__init__()
        self.geocoding_service = GeocodingService()
        
    async def enrich_event(self, event: Event) -> bool:
        """
        Enrich an event with geocoding data.
        
        Args:
            event: The Event object to enrich
            
        Returns:
            True if enrichment was successful, False otherwise
        """
        # Skip if already geocoded
        if event.latitude is not None and event.longitude is not None:
            self.logger.debug(f"Event {event.id} already has coordinates")
            return True
        
        # Skip if no location
        if not event.location:
            self.logger.warning(f"No location provided for event {event.id}")
            return False
        
        # Geocode the event
        return await self.geocoding_service.geocode_event(event)
        
    def clear_cache(self):
        """Clear the geocoding cache."""
        self.geocoding_service.clear_cache()
        self.logger.info("Geocoding cache cleared") 