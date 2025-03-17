"""Website/Flyer enrichment service for events."""
import logging
import time
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

import aiohttp
from bs4 import BeautifulSoup

from app.models import Event
from app.services.enrichment.base import EnrichmentService
from app.services.ai_service import AIService
from app.config import get_settings

logger = logging.getLogger(__name__)

class WebsiteFlyerEnrichmentService(EnrichmentService):
    """Service for enriching events with website/flyer data."""
    
    def __init__(self):
        """Initialize the website/flyer enrichment service."""
        super().__init__()
        self.settings = get_settings()
        self.ai_service = AIService()
        self.session = None
        self._cache = {}
        
        # Update frequency settings
        self.near_term_days = 90  # Events within 3 months are checked nightly
        
    async def _get_session(self):
        """Get or create an aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={"User-Agent": "TrailBlazeApp/1.0"}
            )
        return self.session
        
    async def _fetch_url_content(self, url: str) -> Optional[str]:
        """
        Fetch content from a URL.
        
        Args:
            url: The URL to fetch
            
        Returns:
            HTML content as string or None if fetch failed
        """
        if not url:
            return None
            
        # Check cache first
        if url in self._cache:
            self.logger.debug(f"Returning cached content for URL: {url}")
            return self._cache[url]
            
        try:
            session = await self._get_session()
            self.logger.info(f"Fetching content from URL: {url}")
            
            async with session.get(url) as response:
                if response.status == 200:
                    content = await response.text()
                    
                    # Cache the result
                    self._cache[url] = content
                    self.logger.info(f"Successfully fetched content from {url} ({len(content)} bytes)")
                    return content
                else:
                    self.logger.warning(f"Failed to fetch URL {url}: HTTP {response.status}")
                    return None
        except Exception as e:
            self.logger.exception(f"Error fetching URL {url}: {str(e)}")
            return None
            
    async def _extract_info_with_ai(self, content: str, event: Event) -> Dict[str, Any]:
        """
        Use AI to extract structured information from content.
        
        Args:
            content: HTML or text content to analyze
            event: The event being processed, for context
            
        Returns:
            Dictionary of extracted information
        """
        # First, clean the HTML to get plain text
        soup = BeautifulSoup(content, 'html.parser')
        text = soup.get_text(separator="\n", strip=True)
        
        # Trim the text if it's too long (15000 characters should be enough for most content)
        if len(text) > 15000:
            self.logger.warning(f"Trimming content for event {event.id} from {len(text)} to 15000 chars")
            text = text[:15000]
            
        # Create a prompt for the AI service
        prompt = f"""
        Extract detailed information about this event:
        
        Event Name: {event.name if event.name else 'Unknown'}
        Date: {event.date if event.date else 'Unknown'}
        Location: {event.location if event.location else 'Unknown'}
        
        Extract the following information from the text (if available):
        - Detailed description of the event
        - Start time and end time
        - Registration information and deadlines
        - Cost/fee information
        - Contact details
        - Any special requirements or gear needed
        - Event highlights
        - Organizer information
        
        Text content from website:
        {text}
        
        Return the information as a JSON object with these fields (leave blank if not found):
        {{
            "description": "",
            "start_time": "",
            "end_time": "",
            "registration_info": "",
            "cost_info": "",
            "contact_details": "",
            "requirements": "",
            "highlights": "",
            "organizer": ""
        }}
        """
        
        try:
            # Call the AI service to process the prompt
            result = await self.ai_service.generate_text(prompt)
            
            # Try to parse the result as JSON
            # Sometimes the AI might not return valid JSON, so we need to handle that
            try:
                # Extract JSON from the response if needed
                if "```json" in result:
                    json_part = result.split("```json")[1].split("```")[0].strip()
                    extracted_data = json.loads(json_part)
                elif "{" in result and "}" in result:
                    # Find the JSON part
                    start = result.find("{")
                    end = result.rfind("}") + 1
                    json_part = result[start:end]
                    extracted_data = json.loads(json_part)
                else:
                    extracted_data = json.loads(result)
                    
                self.logger.info(f"Successfully extracted data for event {event.id}")
                return extracted_data
            except json.JSONDecodeError:
                self.logger.error(f"Failed to parse AI response as JSON for event {event.id}")
                # Return a minimal structure in case of parsing failure
                return {
                    "description": "Error parsing AI response.",
                    "extraction_error": True,
                    "raw_response": result[:500]  # Include truncated response for debugging
                }
        except Exception as e:
            self.logger.exception(f"Error processing content with AI for event {event.id}: {str(e)}")
            return {
                "description": f"Error processing with AI: {str(e)}",
                "extraction_error": True
            }
            
    def _should_update_event(self, event: Event) -> bool:
        """
        Determine if an event should be updated based on its date and last check time.
        
        Args:
            event: The event to check
            
        Returns:
            True if the event should be updated, False otherwise
        """
        now = datetime.now()
        
        # If event has no date, update it
        if not event.date:
            return True
            
        # If event has never been checked, update it
        if not event.last_website_check_at:
            return True
            
        # Calculate days until the event
        days_until_event = (event.date - now.date()).days
        
        # If event is in the past, don't update it
        if days_until_event < 0:
            return False
            
        # If event is within 3 months, check nightly if it hasn't been checked in the last 24 hours
        if days_until_event <= self.near_term_days:
            last_check_age = now - event.last_website_check_at
            return last_check_age > timedelta(hours=24)
        
        # For events further in the future, check weekly
        last_check_age = now - event.last_website_check_at
        return last_check_age > timedelta(days=7)
        
    async def enrich_event(self, event: Event) -> bool:
        """
        Enrich an event with website/flyer data.
        
        Args:
            event: The Event object to enrich
            
        Returns:
            True if enrichment was successful, False otherwise
        """
        # Skip if no website URL
        if not event.website_url:
            self.logger.warning(f"No website URL provided for event {event.id}")
            return False
            
        # Check if event should be updated
        if not self._should_update_event(event):
            self.logger.debug(f"Event {event.id} does not need updating yet")
            return True
            
        # Fetch website content
        content = await self._fetch_url_content(event.website_url)
        if not content:
            self.logger.warning(f"Could not fetch content for event {event.id} from {event.website_url}")
            
            # Update last check time even if we couldn't fetch content
            event.last_website_check_at = datetime.now()
            return False
            
        # Process with AI to extract info
        extracted_data = await self._extract_info_with_ai(content, event)
        
        # Update event details
        if event.event_details is None:
            event.event_details = {}
            
        # Merge the extracted data with existing event_details
        event.event_details.update(extracted_data)
        
        # Always update last check time
        event.last_website_check_at = datetime.now()
        
        self.logger.info(f"Successfully enriched event {event.id} with website data")
        return True
        
    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
            self.logger.debug("Closed aiohttp session")
            
    def clear_cache(self):
        """Clear the content cache."""
        self._cache.clear()
        self.logger.info("Website content cache cleared") 