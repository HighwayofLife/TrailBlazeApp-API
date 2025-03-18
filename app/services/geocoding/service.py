"""Geocoding service for converting addresses to coordinates."""
import logging
import time
from typing import Dict, Optional, Tuple, List, Any, Union
from functools import lru_cache
import re

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
    
    def _clean_address(self, address: str) -> str:
        """
        Clean and format an address to improve geocoding success.
        
        Args:
            address: The raw address string
            
        Returns:
            Cleaned address string
        """
        if not address:
            return ""
            
        # Remove any text after a semicolon (often contains non-address info)
        if ";" in address:
            address = address.split(";")[0].strip()
            
        # Remove any instructions in parentheses
        address = re.sub(r'\([^)]*\)', '', address)
        
        # Remove "intro ride each day" and similar phrases
        address = re.sub(r'intro ride.*', '', address, flags=re.IGNORECASE)
        address = re.sub(r'limited entries.*', '', address, flags=re.IGNORECASE)
        
        # If the address contains a dash, try the part after the dash as it might contain the location
        if " - " in address:
            parts = address.split(" - ", 1)
            # If the second part looks like an address (contains numbers, street names, etc.)
            if re.search(r'\d+|\brd\b|\bst\b|\bave\b|\bhwy\b|\broute\b|\bcounty\b|\bpark\b', parts[1], re.IGNORECASE):
                address = parts[1].strip()
        
        # Clean up extra whitespace
        address = re.sub(r'\s+', ' ', address).strip()
        
        # Add "USA" if it's likely a US address without country specification
        us_state_pattern = r'(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY)'
        if re.search(f"{us_state_pattern}\\b", address) and "USA" not in address and "US" not in address:
            address += ", USA"
            
        return address
        
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
        
        # Clean and format the address
        cleaned_address = self._clean_address(address)
        if not cleaned_address:
            logger.warning(f"Address cleaning resulted in empty string: {address}")
            return None
            
        logger.debug(f"Cleaned address: '{address}' -> '{cleaned_address}'")
        
        # Check cache first
        if cleaned_address in self._cache:
            logger.debug(f"Returning cached coordinates for address: {cleaned_address}")
            return self._cache[cleaned_address]
        
        try:
            logger.info(f"Geocoding address: {cleaned_address}")
            location = await self.geocoder.geocode(cleaned_address)
            
            if location:
                # Cache the result
                coordinates = (location.latitude, location.longitude)
                self._cache[cleaned_address] = coordinates
                logger.info(f"Geocoded '{cleaned_address}' to {coordinates}")
                return coordinates
            else:
                # If the cleaned address failed, try with the original address
                if cleaned_address != address:
                    logger.info(f"Trying original address: {address}")
                    location = await self.geocoder.geocode(address)
                    if location:
                        coordinates = (location.latitude, location.longitude)
                        self._cache[cleaned_address] = coordinates
                        logger.info(f"Geocoded original address '{address}' to {coordinates}")
                        return coordinates
                
                logger.warning(f"No location found for address: {cleaned_address}")
                return None
        except (GeocoderTimedOut, GeocoderServiceError, GeocoderUnavailable) as e:
            logger.error(f"Geocoding error for address {cleaned_address}: {str(e)}")
            # Let tenacity retry handle these exceptions
            raise
        except Exception as e:
            logger.exception(f"Unexpected error geocoding address {cleaned_address}: {str(e)}")
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