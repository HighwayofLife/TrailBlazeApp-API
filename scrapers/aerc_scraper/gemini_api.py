"""Google Gemini API integration for event extraction."""

import json
import asyncio
from typing import List, Dict, Any
import google.generativeai as genai
from google.generativeai.types import AsyncGenerativeModel

from ..exceptions import AIError

class GeminiAPI:
    """Wrapper for Google Gemini API integration."""
    
    def __init__(self, api_key: str):
        """Initialize Gemini API client.
        
        Args:
            api_key: Google Gemini API key
        """
        self.api_key = api_key
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        
        # Extraction prompt template
        self.prompt_template = """
        Extract endurance riding event details from the following HTML content.
        Focus on key event information like:
        - Event name
        - Date
        - Location
        - Distance options (e.g. 25, 50, 75, 100 miles)
        - Ride manager contact
        - Entry fees
        - Special requirements
        
        Format the output as a JSON object with these fields.
        Only include information that is explicitly present in the content.
        
        HTML Content:
        {html_content}
        """
    
    async def extract_events(self, html_content: str) -> List[Dict[str, Any]]:
        """Extract event information from HTML using Gemini.
        
        Args:
            html_content: HTML content containing event information
            
        Returns:
            List of dictionaries containing extracted event details
            
        Raises:
            AIError: If extraction fails
        """
        try:
            # Clean HTML for prompt
            cleaned_content = self._clean_html(html_content)
            
            # Generate prompt
            prompt = self.prompt_template.format(html_content=cleaned_content)
            
            # Get completion from Gemini
            response = await self.model.generate_content_async(prompt)
            
            if not response.text:
                raise AIError("Empty response from Gemini API")
            
            # Extract JSON from response
            try:
                # Look for JSON in response
                json_start = response.text.find('{')
                json_end = response.text.rfind('}') + 1
                if json_start == -1 or json_end == 0:
                    raise ValueError("No JSON found in response")
                
                json_str = response.text[json_start:json_end]
                events = json.loads(json_str)
                
                # Handle both single event and list of events
                if isinstance(events, dict):
                    events = [events]
                
                return self._validate_events(events)
                
            except json.JSONDecodeError as e:
                raise AIError(f"Failed to parse Gemini response as JSON: {str(e)}")
            
        except Exception as e:
            raise AIError(f"Gemini API extraction failed: {str(e)}")
    
    def _clean_html(self, html: str) -> str:
        """Clean HTML content for prompt.
        
        Args:
            html: Raw HTML content
            
        Returns:
            Cleaned HTML suitable for prompting
        """
        # Remove unnecessary whitespace
        html = ' '.join(html.split())
        
        # Truncate if too long (Gemini has ~30k token limit)
        if len(html) > 20000:
            html = html[:20000] + "..."
        
        return html
    
    def _validate_events(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate extracted events.
        
        Args:
            events: List of extracted events
            
        Returns:
            List of validated events
            
        Raises:
            AIError: If validation fails
        """
        required_fields = {'name', 'date', 'location'}
        validated = []
        
        for event in events:
            # Check required fields
            missing = required_fields - set(event.keys())
            if missing:
                continue  # Skip events missing required fields
            
            # Basic data type validation
            if not isinstance(event['name'], str) or \
               not isinstance(event['location'], str):
                continue
            
            validated.append(event)
        
        if not validated:
            raise AIError("No valid events found in extracted data")
        
        return validated
    
    async def close(self) -> None:
        """Clean up resources."""
        # Currently no cleanup needed for Gemini API
        pass