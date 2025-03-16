"""
Gemini API client for AI-based data extraction.
"""

import logging
import json
import asyncio
from typing import List, Dict, Any, Optional
from google import genai
from ..config import get_scraper_settings
from ..exceptions import APIError, DataExtractionError

logger = logging.getLogger(__name__)

class GeminiClient:
    """Client for interacting with Google's Gemini API."""
    
    def __init__(self, settings):
        self.settings = settings
        genai.configure(api_key=settings.gemini_api_key)
        
        self.client = genai.GenerationConfig(
            temperature=settings.temperature,
            candidate_count=1,
            max_output_tokens=settings.max_output_tokens,
            response_mime_type="application/json"
        )
        
        self.metrics = {
            'calls': 0,
            'errors': 0,
            'fallback_successes': 0,
            'total_tokens': 0
        }
    
    def _create_prompt(self, chunk: str) -> str:
        """Create a prompt for Gemini models."""
        return f"""
        I need you to extract endurance ride events from this AERC calendar HTML and return a JSON array.

        IMPORTANT FORMATTING INSTRUCTIONS:
        - Return ONLY the raw JSON array with no markdown code blocks, no backticks
        - Do not add any explanations, descriptions, or notes before or after the JSON
        - Start your response with '[' and end with ']'
        - This JSON will be directly parsed by a machine, not read by a human
        - Follow the exact structure defined below with no additional fields

        JSON Structure:
        [
          {{
            "rideName": "event name",
            "date": "YYYY-MM-DD",
            "region": "AERC region code",
            "location": "event location",
            "distances": [
              {{
                "distance": "distance value",
                "date": "YYYY-MM-DD",
                "startTime": "start time"
              }}
            ],
            "rideManager": "manager name",
            "rideManagerContact": {{
              "name": "contact name",
              "email": "email address",
              "phone": "phone number"
            }},
            "controlJudges": [
              {{
                "role": "role title",
                "name": "judge name"
              }}
            ],
            "mapLink": "Google Maps URL",
            "hasIntroRide": boolean
          }}
        ]

        Calendar HTML:
        {chunk}
        """
    
    async def extract_data(self, html_chunk: str, chunk_idx: int = 0) -> List[Dict[str, Any]]:
        """Extract structured data from HTML using Gemini API."""
        self.metrics['calls'] += 1
        
        try:
            # Try primary model first
            try:
                prompt = self._create_prompt(html_chunk)
                response = await asyncio.to_thread(
                    lambda: genai.generate_text(
                        model=self.settings.primary_model,
                        prompt=prompt,
                        generation_config=self.client
                    )
                )
                
                result = self._process_response(response, chunk_idx)
                if result:
                    return result
                    
            except Exception as e:
                logger.warning(f"Primary model failed for chunk {chunk_idx}: {e}")
                self.metrics['errors'] += 1
            
            # Try fallback model
            logger.info(f"Using fallback model for chunk {chunk_idx}")
            response = await asyncio.to_thread(
                lambda: genai.generate_text(
                    model=self.settings.fallback_model,
                    prompt=prompt,
                    generation_config=self.client
                )
            )
            
            result = self._process_response(response, chunk_idx)
            if result:
                self.metrics['fallback_successes'] += 1
                return result
            
            raise APIError("Gemini", f"Both models failed to extract data from chunk {chunk_idx}")
            
        except Exception as e:
            self.metrics['errors'] += 1
            if isinstance(e, APIError):
                raise
            raise APIError("Gemini", f"Data extraction failed: {str(e)}")
    
    def _process_response(self, response: Any, chunk_idx: int) -> Optional[List[Dict[str, Any]]]:
        """Process and validate Gemini API response."""
        try:
            if not response:
                logger.error(f"Empty response from Gemini API for chunk {chunk_idx}")
                return None
            
            # Get text content
            text = response.text if hasattr(response, 'text') else str(response)
            
            if not text:
                logger.error(f"Empty text in response for chunk {chunk_idx}")
                return None
            
            # Extract JSON array
            text = text.strip()
            start_idx = text.find('[')
            end_idx = text.rfind(']')
            
            if start_idx == -1 or end_idx == -1:
                logger.warning(f"No JSON array found in response for chunk {chunk_idx}")
                return None
            
            # Parse JSON
            json_str = text[start_idx:end_idx + 1]
            json_str = self._fix_json_syntax(json_str)
            
            try:
                events_data = json.loads(json_str)
                if isinstance(events_data, list):
                    return events_data
                else:
                    logger.error(f"Invalid JSON structure in chunk {chunk_idx}")
                    return None
                    
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error in chunk {chunk_idx}: {e}")
                return None
                
        except Exception as e:
            logger.exception(f"Error processing response for chunk {chunk_idx}: {e}")
            return None
    
    def _fix_json_syntax(self, json_str: str) -> str:
        """Fix common JSON syntax issues."""
        # Fix trailing commas
        json_str = json_str.replace(',]', ']').replace(',}', '}')
        
        # Fix missing commas between objects
        json_str = json_str.replace('}{', '},{')
        
        # Ensure proper array closure
        if json_str.startswith('[') and not json_str.endswith(']'):
            json_str += ']'
        
        return json_str
    
    def get_metrics(self) -> dict:
        """Get Gemini API metrics."""
        return self.metrics.copy()