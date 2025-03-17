"""Geocoding service for converting addresses to coordinates."""
import logging
import time
from typing import Dict, Optional, Tuple, List, Any, Union
from functools import lru_cache

from geopy.geocoders import Nominatim, GoogleV3
from geopy.adapters import AioHTTPAdapter
from geopy.exc import GeocoderServiceError, GeocoderTimedOut, GeocoderUnavailable
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import get_settings
from app.models import Event

# Configure logging
logger = logging.getLogger(__name__)

class GeocodingService:
    """Service for geocoding addresses to coordinates."""
    
    def __init__(self):
        """Initialize the geocoding service with configuration."""
        self.settings = get_settings()
        self.provider = self.settings.GEOCODING_PROVIDER
        self.user_agent = self.settings.GEOCODING_USER_AGENT
        self.api_key = self.settings.GEOCODING_API_KEY
        self.timeout = self.settings.GEOCODING_TIMEOUT
        self.max_retries = self.settings.GEOCODING_RETRIES
        
        # Initialize the geocoder
        if self.provider.lower() == "google":
            self.geocoder = GoogleV3(
                api_key=self.api_key,
                timeout=self.timeout,
                adapter_factory=AioHTTPAdapter,
            )
        else:
            # Default to Nominatim (OpenStreetMap)
            self.geocoder = Nominatim(
                user_agent=self.user_agent,
                timeout=self.timeout,
                adapter_factory=AioHTTPAdapter,
            )
        
        # Cache for geocoding results
        self._cache = {}
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((GeocoderTimedOut, GeocoderServiceError, GeocoderUnavailable)),
    )
    async def geocode_address(self, address: str) -> Optional[Tuple[float, float]]:
        """
        Geocode an address to get latitude and longitude.
        
        Args:
            address: The address to geocode
            
        Returns:
            Tuple of (latitude, longitude) or None if geocoding failed
        """
        if not address:
            logger.warning("Empty address provided for geocoding")
            return None
        
        # Check cache first
        if address in self._cache:
            logger.debug(f"Returning cached coordinates for address: {address}")
            return self._cache[address]
        
        try:
            logger.info(f"Geocoding address: {address}")
            location = await self.geocoder.geocode(address)
            
            if location:
                # Cache the result
                coordinates = (location.latitude, location.longitude)
                self._cache[address] = coordinates
                logger.info(f"Geocoded {address} to {coordinates}")
                return coordinates
            else:
                logger.warning(f"No location found for address: {address}")
                return None
        except (GeocoderTimedOut, GeocoderServiceError, GeocoderUnavailable) as e:
            logger.error(f"Geocoding error for address {address}: {str(e)}")
            # Let tenacity retry handle these exceptions
            raise
        except Exception as e:
            logger.exception(f"Unexpected error geocoding address {address}: {str(e)}")
            return None
        
    async def geocode_event(self, event: Event) -> bool:
        """
        Geocode an event's location and update its latitude and longitude.
        
        Args:
            event: The Event object to geocode
            
        Returns:
            True if geocoding was successful, False otherwise
        """
        if not event.location:
            logger.warning(f"No location provided for event {event.id}")
            return False
        
        # Skip if already geocoded
        if event.latitude is not None and event.longitude is not None:
            logger.debug(f"Event {event.id} already has coordinates")
            return True
        
        coordinates = await self.geocode_address(event.location)
        if coordinates:
            event.latitude, event.longitude = coordinates
            logger.info(f"Updated event {event.id} with coordinates {coordinates}")
            return True
        else:
            logger.warning(f"Failed to geocode event {event.id} location: {event.location}")
            return False
    
    def clear_cache(self):
        """Clear the geocoding cache."""
        self._cache.clear()
        logger.info("Geocoding cache cleared")
        
    @property
    def cache_size(self) -> int:
        """Get the current size of the geocoding cache."""
        return len(self._cache) 