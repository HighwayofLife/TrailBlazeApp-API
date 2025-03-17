"""
Gemini API client for AI-based data extraction.
"""

import logging
import json
import asyncio
import re
from typing import List, Dict, Any, Optional, Tuple
from bs4 import BeautifulSoup
from google import genai
from google.genai import types
from .config import get_settings  # Changed from ..config import get_scraper_settings
from ..exceptions import AIError, DataExtractionError

logger = logging.getLogger(__name__)

class GeminiClient:
    """Client for interacting with Google's Gemini API."""
    
    def __init__(self, settings):
        self.settings = settings
        self.client = genai.Client(api_key=settings.gemini_api_key)
        
        self.metrics = {
            'calls': 0,
            'errors': 0,
            'fallback_successes': 0,
            'total_tokens': 0,
            'token_counts': [],
            'error_types': {},
            'streaming_used': 0,
            'chunks_processed': 0
        }
        
        # Default max tokens for models
        self.model_token_limits = {
            'gemini-2.0-flash-lite': 8192,
            'gemini-2.0-flash': 8192,
            'gemini-1.5-flash': 8192,
            'gemini-1.0-pro': 8192
        }
        
        # Maximum input tokens to allow before chunking
        self.max_input_tokens = 4000  # Conservative limit to leave room for output
        
        # Maximum HTML size per chunk (characters)
        self.max_html_chunk_size = 7500  # Reduced to 75% of original 10000 to avoid excessive chunking
    
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
        - If the HTML chunk is incomplete or cut off, just extract what you can see

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
    
    def _create_structured_prompt(self, chunk: str) -> Dict[str, Any]:
        """Create a structured prompt for Gemini models with proper config."""
        # Define the schema for the structured output
        schema = {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "rideName": {"type": "STRING", "description": "Name of the endurance ride event"},
                    "date": {"type": "STRING", "description": "Event date in YYYY-MM-DD format"},
                    "region": {"type": "STRING", "description": "AERC region code"},
                    "location": {"type": "STRING", "description": "Location of the event"},
                    "distances": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "distance": {"type": "STRING", "description": "Distance value"},
                                "date": {"type": "STRING", "description": "Date for this distance in YYYY-MM-DD format"},
                                "startTime": {"type": "STRING", "description": "Start time for this distance"}
                            }
                        }
                    },
                    "rideManager": {"type": "STRING", "description": "Name of the ride manager"},
                    "rideManagerContact": {
                        "type": "OBJECT",
                        "properties": {
                            "name": {"type": "STRING", "description": "Contact name"},
                            "email": {"type": "STRING", "description": "Email address"},
                            "phone": {"type": "STRING", "description": "Phone number"}
                        }
                    },
                    "controlJudges": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "role": {"type": "STRING", "description": "Role title"},
                                "name": {"type": "STRING", "description": "Judge name"}
                            }
                        }
                    },
                    "mapLink": {"type": "STRING", "description": "Google Maps URL"},
                    "hasIntroRide": {"type": "BOOLEAN", "description": "Whether the event has an intro ride"}
                }
            }
        }
        
        # Create the prompt with structured output instructions
        prompt = f"""
        Extract endurance ride events from this AERC calendar HTML.
        If the HTML chunk is incomplete or cut off, just extract what you can see.
        
        Calendar HTML:
        {chunk}
        """
        
        return {
            "prompt": prompt,
            "schema": schema
        }
    
    async def count_tokens(self, text: str, model: str) -> int:
        """Count tokens in text for a specific model."""
        try:
            response = self.client.models.count_tokens(
                model=model,
                contents=text
            )
            return response.total_tokens
        except Exception as e:
            logger.warning(f"Failed to count tokens: {e}")
            return -1  # Return -1 to indicate error
    
    def _split_html_into_chunks(self, html: str) -> List[str]:
        """Split HTML into smaller chunks based on natural boundaries."""
        try:
            # Try to parse with BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Look for natural boundaries like table rows or divs
            chunks = []
            events = []
            
            # Try to find event containers (table rows, divs with event info, etc.)
            rows = soup.find_all('tr')
            if len(rows) > 5:  # If we have a table structure
                current_chunk = ""
                for row in rows:
                    row_html = str(row)
                    if len(current_chunk) + len(row_html) > self.max_html_chunk_size and current_chunk:
                        chunks.append(current_chunk)
                        current_chunk = row_html
                    else:
                        current_chunk += row_html
                
                if current_chunk:
                    chunks.append(current_chunk)
                
                return chunks
            
            # If no table rows, try divs
            divs = soup.find_all('div', class_=lambda c: c and ('event' in c.lower() or 'ride' in c.lower()))
            if len(divs) > 3:
                current_chunk = ""
                for div in divs:
                    div_html = str(div)
                    if len(current_chunk) + len(div_html) > self.max_html_chunk_size and current_chunk:
                        chunks.append(current_chunk)
                        current_chunk = div_html
                    else:
                        current_chunk += div_html
                
                if current_chunk:
                    chunks.append(current_chunk)
                
                return chunks
            
            # If no clear event containers, split by size
            return self._split_by_size(html)
            
        except Exception as e:
            logger.warning(f"Error parsing HTML with BeautifulSoup: {e}")
            # Fallback to simple size-based splitting
            return self._split_by_size(html)
    
    def _split_by_size(self, html: str) -> List[str]:
        """Split HTML by size, trying to preserve tag boundaries."""
        chunks = []
        current_pos = 0
        
        while current_pos < len(html):
            # Find a good breaking point near max_html_chunk_size
            end_pos = min(current_pos + self.max_html_chunk_size, len(html))
            
            # If we're not at the end, try to find a tag boundary
            if end_pos < len(html):
                # Look for closing tag
                next_close = html.find('>', end_pos)
                if next_close != -1 and next_close - end_pos < 100:  # Don't look too far ahead
                    end_pos = next_close + 1
            
            chunks.append(html[current_pos:end_pos])
            current_pos = end_pos
        
        return chunks
    
    async def _process_html_chunk(self, html_chunk: str, chunk_idx: int) -> List[Dict[str, Any]]:
        """Process a single HTML chunk and extract data."""
        # Count input tokens
        input_tokens = await self.count_tokens(html_chunk, self.settings.primary_model)
        if input_tokens > 0:
            logger.info(f"Input tokens for chunk {chunk_idx}: {input_tokens}")
            
            # Check if input is too large
            if input_tokens > self.max_input_tokens:
                logger.warning(f"Input chunk {chunk_idx} is too large ({input_tokens} tokens). Splitting further.")
                # Split the HTML into smaller pieces
                sub_chunks = self._split_by_size(html_chunk)
                logger.info(f"Split chunk {chunk_idx} into {len(sub_chunks)} sub-chunks")
                
                # Process each sub-chunk and combine results
                all_results = []
                for i, sub_chunk in enumerate(sub_chunks):
                    sub_results = await self._extract_data_with_fallbacks(sub_chunk, f"{chunk_idx}.{i}")
                    if sub_results:
                        all_results.extend(sub_results)
                
                return all_results
        
        # Process the chunk directly if it's not too large
        return await self._extract_data_with_fallbacks(html_chunk, chunk_idx)
    
    async def _extract_data_with_fallbacks(self, html_chunk: str, chunk_idx: Any) -> List[Dict[str, Any]]:
        """Extract data with multiple fallback strategies."""
        # Try structured output first
        try:
            structured_data = self._create_structured_prompt(html_chunk)
            
            # Use the correct config format according to documentation
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=structured_data["schema"],
                temperature=0.2,
                max_output_tokens=4096  # Set explicit output token limit
            )
            
            response = self.client.models.generate_content(
                model=self.settings.primary_model,
                contents=structured_data["prompt"],
                config=config
            )
            
            # Track token usage
            self._track_token_usage(response, chunk_idx)
            
            result = self._process_structured_response(response, chunk_idx)
            if result:
                return result
                
        except Exception as e:
            self._track_error(e, f"Structured output failed for chunk {chunk_idx}")
        
        # Try streaming with primary model
        try:
            prompt = self._create_prompt(html_chunk)
            
            # Use config with explicit token limits
            config = types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=4096  # Set explicit output token limit
            )
            
            # Use streaming to avoid truncation
            full_response = await self._stream_response(
                self.settings.primary_model, 
                prompt, 
                config, 
                chunk_idx
            )
            
            if full_response:
                result = self._process_text_response(full_response, chunk_idx)
                if result:
                    self.metrics['streaming_used'] += 1
                    return result
                    
        except Exception as e:
            self._track_error(e, f"Primary model streaming failed for chunk {chunk_idx}")
        
        # Try regular API with primary model
        try:
            prompt = self._create_prompt(html_chunk)
            
            # Use config with explicit token limits
            config = types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=4096  # Set explicit output token limit
            )
            
            response = self.client.models.generate_content(
                model=self.settings.primary_model,
                contents=prompt,
                config=config
            )
            
            # Track token usage
            self._track_token_usage(response, chunk_idx)
            
            result = self._process_response(response, chunk_idx)
            if result:
                return result
                
        except Exception as e:
            self._track_error(e, f"Primary model failed for chunk {chunk_idx}")
        
        # Try fallback model with streaming
        logger.info(f"Using fallback model for chunk {chunk_idx}")
        try:
            prompt = self._create_prompt(html_chunk)
            
            # Use config with explicit token limits
            config = types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=4096  # Set explicit output token limit
            )
            
            # Use streaming to avoid truncation
            full_response = await self._stream_response(
                self.settings.fallback_model, 
                prompt, 
                config, 
                chunk_idx
            )
            
            if full_response:
                result = self._process_text_response(full_response, chunk_idx)
                if result:
                    self.metrics['fallback_successes'] += 1
                    self.metrics['streaming_used'] += 1
                    return result
                    
        except Exception as e:
            self._track_error(e, f"Fallback model streaming failed for chunk {chunk_idx}")
        
        # Try regular API with fallback model as last resort
        try:
            prompt = self._create_prompt(html_chunk)
            
            # Use config with explicit token limits
            config = types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=4096  # Set explicit output token limit
            )
            
            response = self.client.models.generate_content(
                model=self.settings.fallback_model,
                contents=prompt,
                config=config
            )
            
            # Track token usage
            self._track_token_usage(response, chunk_idx)
            
            result = self._process_response(response, chunk_idx)
            if result:
                self.metrics['fallback_successes'] += 1
                return result
            
            # Log error metrics before raising exception
            logger.error(f"Error metrics: {self.metrics['error_types']}")
            raise AIError("Gemini", f"All extraction methods failed for chunk {chunk_idx}")
            
        except Exception as e:
            if isinstance(e, AIError):
                raise
            
            self._track_error(e, f"Fallback model failed for chunk {chunk_idx}")
            
            # Log error metrics before raising exception
            logger.error(f"Error metrics: {self.metrics['error_types']}")
            raise AIError("Gemini", f"All extraction methods failed for chunk {chunk_idx}")
    
    def _track_error(self, e: Exception, message: str):
        """Track error in metrics."""
        error_type = type(e).__name__
        error_msg = str(e)
        
        # Track error types for diagnostics
        if error_type not in self.metrics['error_types']:
            self.metrics['error_types'][error_type] = 0
        self.metrics['error_types'][error_type] += 1
        
        logger.warning(f"{message}: {error_type}: {error_msg}")
        self.metrics['errors'] += 1
    
    def _track_token_usage(self, response: Any, chunk_idx: Any):
        """Track token usage from response."""
        if hasattr(response, 'usage') and response.usage:
            if hasattr(response.usage, 'total_tokens'):
                self.metrics['total_tokens'] += response.usage.total_tokens
                self.metrics['token_counts'].append(response.usage.total_tokens)
                logger.info(f"Total tokens used for chunk {chunk_idx}: {response.usage.total_tokens}")
            
            # Check if we're close to output token limits
            if hasattr(response.usage, 'output_tokens'):
                output_tokens = response.usage.output_tokens
                if output_tokens > 4000:  # Close to typical 4096 limit
                    logger.warning(f"Output tokens ({output_tokens}) close to limit for chunk {chunk_idx}")
    
    async def _stream_response(self, model: str, prompt: str, config: Any, chunk_idx: Any) -> str:
        """Use streaming API to get complete response."""
        try:
            full_text = ""
            async for chunk in self.client.aio.models.generate_content_stream(
                model=model,
                contents=prompt,
                config=config
            ):
                if hasattr(chunk, 'text'):
                    full_text += chunk.text
            
            if not full_text:
                logger.warning(f"Empty response from streaming API for chunk {chunk_idx}")
                return None
            
            return full_text
            
        except Exception as e:
            logger.warning(f"Error using streaming API for chunk {chunk_idx}: {e}")
            return None
    
    async def extract_data(self, html_chunk: str, chunk_idx: int = 0) -> List[Dict[str, Any]]:
        """Extract structured data from HTML using Gemini API."""
        self.metrics['calls'] += 1
        self.metrics['chunks_processed'] += 1
        
        # Check if input is too large and needs to be split
        input_tokens = await self.count_tokens(html_chunk, self.settings.primary_model)
        if input_tokens > 0:
            logger.info(f"Input tokens for chunk {chunk_idx}: {input_tokens}")
            
            # Check if input is too large
            model_limit = self.model_token_limits.get(self.settings.primary_model, 8192)
            if input_tokens > model_limit * 0.7:  # If using more than 70% of limit
                logger.warning(f"Input chunk {chunk_idx} is large ({input_tokens} tokens). Splitting into smaller chunks.")
                
                # Split the HTML into smaller chunks
                html_chunks = self._split_html_into_chunks(html_chunk)
                logger.info(f"Split original chunk into {len(html_chunks)} smaller chunks")
                
                # Process each chunk and combine results
                all_results = []
                for i, sub_chunk in enumerate(html_chunks):
                    try:
                        sub_results = await self._process_html_chunk(sub_chunk, f"{chunk_idx}.{i}")
                        if sub_results:
                            all_results.extend(sub_results)
                    except Exception as e:
                        logger.error(f"Error processing sub-chunk {chunk_idx}.{i}: {e}")
                        # Continue with other chunks even if one fails
                
                if all_results:
                    # Map fields to match database schema
                    mapped_results = self._map_fields(all_results)
                    return mapped_results
                else:
                    raise AIError("Gemini", f"Failed to extract data from all sub-chunks of chunk {chunk_idx}")
        
        # If not too large, process directly
        try:
            results = await self._process_html_chunk(html_chunk, chunk_idx)
            # Map fields to match database schema
            mapped_results = self._map_fields(results)
            return mapped_results
        except Exception as e:
            if isinstance(e, AIError):
                raise
            raise AIError("Gemini", f"Data extraction failed: {str(e)}")
    
    def _process_structured_response(self, response: Any, chunk_idx: Any) -> Optional[List[Dict[str, Any]]]:
        """Process structured response from Gemini API."""
        try:
            if not response:
                logger.error(f"Empty response from Gemini API for chunk {chunk_idx}")
                return None
            
            # For structured responses with JSON mime type, we should have a text field with JSON
            if hasattr(response, 'text'):
                try:
                    # Try to parse the JSON directly
                    events_data = json.loads(response.text)
                    if isinstance(events_data, list):
                        return events_data
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON decode error in structured response: {e}")
                    # If direct parsing fails, try to extract JSON from the text
                    return self._process_text_response(response.text, chunk_idx)
            
            # If we can't find structured output, try to get text and parse it
            return self._process_response(response, chunk_idx)
                
        except Exception as e:
            logger.exception(f"Error processing structured response for chunk {chunk_idx}: {e}")
            return None
    
    def _process_text_response(self, text: str, chunk_idx: Any) -> Optional[List[Dict[str, Any]]]:
        """Process plain text response."""
        try:
            if not text:
                logger.error(f"Empty text for chunk {chunk_idx}")
                return None
            
            # Check if response is truncated (might indicate token limit)
            if len(text) > 100:
                last_chars = text[-10:]
                if not last_chars.endswith(']') and '}' in last_chars:
                    logger.warning(f"Response for chunk {chunk_idx} appears truncated. Possible token limit reached.")
            
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
            logger.exception(f"Error processing text response for chunk {chunk_idx}: {e}")
            return None
    
    def _process_response(self, response: Any, chunk_idx: Any) -> Optional[List[Dict[str, Any]]]:
        """Process and validate Gemini API response."""
        try:
            if not response:
                logger.error(f"Empty response from Gemini API for chunk {chunk_idx}")
                return None
            
            # Get text content
            text = response.text if hasattr(response, 'text') else str(response)
            return self._process_text_response(text, chunk_idx)
                
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
        
        # Handle truncated JSON due to token limits
        if json_str.count('[') > json_str.count(']'):
            json_str += ']' * (json_str.count('[') - json_str.count(']'))
        
        if json_str.count('{') > json_str.count('}'):
            json_str += '}' * (json_str.count('{') - json_str.count('}'))
        
        # Try to parse the JSON
        try:
            json.loads(json_str)
            return json_str
        except json.JSONDecodeError as e:
            logger.warning(f"JSON decode error: {e}")
            
            # Fix common issues
            try:
                # Fix invalid escape sequences
                if "Invalid \\escape" in str(e):
                    json_str = json_str.replace('\\', '\\\\')
                    json_str = json_str.replace('\\\\n', '\\n')
                    json_str = json_str.replace('\\\\r', '\\r')
                    json_str = json_str.replace('\\\\t', '\\t')
                    json_str = json_str.replace('\\\\b', '\\b')
                    json_str = json_str.replace('\\\\f', '\\f')
                    json_str = json_str.replace('\\\\"', '\\"')
                    json_str = json_str.replace('\\\\/', '\\/')
                
                # Fix missing quotes around keys
                if "Expecting property name" in str(e) or "Expecting ':'" in str(e):
                    import re
                    # Find unquoted keys like {key: "value"} and convert to {"key": "value"}
                    json_str = re.sub(r'([{,])\s*([a-zA-Z0-9_]+)\s*:', r'\1"\2":', json_str)
                
                # Fix single quotes used instead of double quotes
                if "Expecting '\"'" in str(e):
                    # Replace single quotes with double quotes, but only if they're not inside double quotes
                    in_double_quotes = False
                    result = []
                    for char in json_str:
                        if char == '"':
                            in_double_quotes = not in_double_quotes
                        elif char == "'" and not in_double_quotes:
                            char = '"'
                        result.append(char)
                    json_str = ''.join(result)
                
                # Fix missing commas between array elements
                if "Expecting ',' delimiter" in str(e):
                    line_info = str(e).split(":")[-2:]
                    if len(line_info) >= 2:
                        try:
                            line = int(line_info[0].strip())
                            col = int(line_info[1].split()[0].strip())
                            
                            # Split the JSON string into lines
                            lines = json_str.split('\n')
                            if 0 <= line - 1 < len(lines):
                                # Insert a comma at the specified position
                                line_content = lines[line - 1]
                                if 0 <= col < len(line_content):
                                    lines[line - 1] = line_content[:col] + ',' + line_content[col:]
                                    json_str = '\n'.join(lines)
                        except (ValueError, IndexError):
                            pass
                
                # Fix unterminated strings
                if "Unterminated string" in str(e):
                    # Try to locate the unterminated string and fix it
                    match = re.search(r'line (\d+) column (\d+)', str(e))
                    if match:
                        try:
                            line = int(match.group(1))
                            col = int(match.group(2))
                            
                            lines = json_str.split('\n')
                            if 0 <= line - 1 < len(lines):
                                # Add a closing quote at the end of the line
                                lines[line - 1] = lines[line - 1] + '"'
                                json_str = '\n'.join(lines)
                        except (ValueError, IndexError):
                            pass
                
                # Try parsing again after fixes
                try:
                    json.loads(json_str)
                    return json_str
                except json.JSONDecodeError:
                    # If still failing, try more aggressive approaches
                    
                    # Replace all backslashes with nothing as a last resort
                    try:
                        fixed_str = json_str.replace('\\', '')
                        json.loads(fixed_str)
                        return fixed_str
                    except json.JSONDecodeError:
                        pass
                    
                    # Try to extract valid JSON subset
                    try:
                        # Find the last complete object in the array
                        last_complete_obj_end = json_str.rfind('}')
                        if last_complete_obj_end > 0:
                            # Find the opening bracket of the array
                            if json_str.startswith('['):
                                # Close the array after the last complete object
                                truncated_json = json_str[:last_complete_obj_end+1] + ']'
                                json.loads(truncated_json)
                                return truncated_json
                    except json.JSONDecodeError:
                        pass
                    
                    # Try to fix JSON by removing problematic sections
                    try:
                        # Find all complete objects in the array
                        objects = re.findall(r'{[^{}]*}', json_str)
                        if objects:
                            # Reconstruct a valid array with the complete objects
                            reconstructed = '[' + ','.join(objects) + ']'
                            json.loads(reconstructed)
                            return reconstructed
                    except (json.JSONDecodeError, re.error):
                        pass
            
            except Exception as nested_e:
                logger.error(f"Error while fixing JSON: {nested_e}")
            
            # Return the original string if all fixes failed
            return json_str
    
    def get_metrics(self) -> dict:
        """Get Gemini API metrics."""
        return self.metrics.copy()
        
    def _map_fields(self, events_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform extracted data to match the database schema.
        
        Maps fields from the AI extraction format to the database schema format:
        - rideName -> name
        - date -> date_start
        - rideManager -> ride_manager
        - mapLink -> map_link
        - etc.
        """
        if not events_data:
            return []
            
        mapped_events = []
        
        for event in events_data:
            mapped_event = {}
            
            # Map basic fields
            if 'rideName' in event:
                mapped_event['name'] = event['rideName']
                
            if 'date' in event:
                mapped_event['date_start'] = event['date']
                
            if 'location' in event:
                mapped_event['location'] = event['location']
                
            if 'region' in event:
                mapped_event['region'] = event['region']
                
            # Map ride manager information
            if 'rideManager' in event:
                mapped_event['ride_manager'] = event['rideManager']
                
            # Map contact information
            if 'rideManagerContact' in event:
                contact = event['rideManagerContact']
                if 'email' in contact:
                    mapped_event['manager_email'] = contact['email']
                if 'phone' in contact:
                    mapped_event['manager_phone'] = contact['phone']
                
                # Store the full contact info in manager_contact
                contact_parts = []
                if 'name' in contact:
                    contact_parts.append(f"Name: {contact['name']}")
                if 'email' in contact:
                    contact_parts.append(f"Email: {contact['email']}")
                if 'phone' in contact:
                    contact_parts.append(f"Phone: {contact['phone']}")
                
                if contact_parts:
                    mapped_event['manager_contact'] = "; ".join(contact_parts)
            
            # Map judges
            if 'controlJudges' in event and event['controlJudges']:
                mapped_event['judges'] = [
                    f"{judge.get('role', 'Judge')}: {judge['name']}" 
                    for judge in event['controlJudges'] 
                    if 'name' in judge
                ]
            
            # Map distances
            if 'distances' in event and event['distances']:
                # Extract just the distance values for the distances array
                mapped_event['distances'] = [
                    d['distance'] for d in event['distances'] 
                    if 'distance' in d
                ]
                
                # Store the full distance details in event_details
                mapped_event['event_details'] = {
                    'distances': event['distances']
                }
                
                # Find the latest date for date_end if there are multiple days
                if 'date_start' in mapped_event:
                    latest_date = mapped_event['date_start']
                    for distance in event['distances']:
                        if 'date' in distance and distance['date'] > latest_date:
                            latest_date = distance['date']
                    
                    if latest_date != mapped_event['date_start']:
                        mapped_event['date_end'] = latest_date
            
            # Map other fields
            if 'mapLink' in event:
                mapped_event['map_link'] = event['mapLink']
                
            if 'hasIntroRide' in event:
                mapped_event['event_details'] = mapped_event.get('event_details', {})
                mapped_event['event_details']['hasIntroRide'] = event['hasIntroRide']
                
            if 'tag' in event:
                mapped_event['external_id'] = str(event['tag'])
                
            # Set default event type and source
            mapped_event['event_type'] = 'endurance'
            mapped_event['source'] = 'AERC'
            
            mapped_events.append(mapped_event)
            
        return mapped_events