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
from app.logging_config import get_logger

# Use the properly configured logger from app.logging_config
logger = get_logger("scrapers.aerc_scraper.gemini")

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
            'chunks_processed': 0,
            'events_found': 0,          # Total events found in HTML
            'events_extracted': 0,      # Events successfully extracted from HTML
            'events_processed': 0,      # Events processed through mapping
            'events_with_issues': [],   # Track events that had issues
            'chunk_split_count': 0      # Number of times chunks needed further splitting
        }
        
        # Default max tokens for models
        self.model_token_limits = {
            'gemini-2.0-flash-lite': 8192,
            'gemini-2.0-flash': 8192,
            'gemini-1.5-flash': 8192,
            'gemini-1.0-pro': 8192
        }
        
        # Maximum input tokens to allow before chunking - based on model limits
        # Use 90% of the model limit to leave some room for safety
        model_limit = self.model_token_limits.get(self.settings.primary_model, 8192)
        self.max_input_tokens = int(model_limit * 0.9)
        
        # Maximum HTML size per chunk - use html_chunk_size from settings
        # This ensures we're using the configured value specifically intended for this purpose
        self.max_html_chunk_size = settings.html_chunk_size
    
    def _create_prompt(self, chunk: str) -> str:
        """Create a prompt for Gemini models."""
        # Log chunk size and content preview
        chunk_size = len(chunk)
        preview = chunk[:200] + "..." if len(chunk) > 200 else chunk
        logger.info(f"Processing chunk of size {chunk_size} bytes")
        logger.debug(f"Chunk preview: {preview}")
        
        return f"""
        I need you to extract endurance ride events from this AERC calendar HTML and return a JSON array.

        IMPORTANT FORMATTING INSTRUCTIONS:
        - Return ONLY the raw JSON array with no markdown code blocks, no backticks
        - Do not add any explanations, descriptions, or notes before or after the JSON
        - Start your response with '[' and end with ']'
        - This JSON will be directly parsed by a machine, not read by a human
        - Follow the exact structure defined below with no additional fields
        - If the HTML chunk is incomplete or cut off, just extract what you can see

        CRITICAL FIELDS (These three fields MUST always be extracted):
        - "rideName": The name of the ride event (MUST not be empty)
        - "date": The event start date in YYYY-MM-DD format (MUST not be empty)
        - "location": The physical location of the event (MUST not be empty)

        JSON Structure:
        [
          {{
            "rideName": "event name", // REQUIRED - must extract this field
            "date": "YYYY-MM-DD", // REQUIRED - must be in this exact format
            "region": "AERC region code",
            "location": "event location", // REQUIRED - must extract this field
            "distances": [
              {{
                "distance": "distance value",
                "date": "YYYY-MM-DD", // Must use this exact date format 
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

        IMPORTANT RULES:
        1. Every event MUST include the rideName, date, and location fields
        2. If you can't find an exact value for these required fields, make your best guess
        3. For dates, use YYYY-MM-DD format ONLY (e.g., 2024-06-15)
        4. Extract every event you can find in the HTML
        5. Every event must be a complete object, even if some fields are missing
        6. If an event seems to have multiple days, include each day as a separate distance item

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
                    "rideName": {"type": "STRING", "description": "Name of the endurance ride event - REQUIRED FIELD"},
                    "date": {"type": "STRING", "description": "Event date in YYYY-MM-DD format - REQUIRED FIELD"},
                    "region": {"type": "STRING", "description": "AERC region code (e.g., MT, NW, SE)"},
                    "location": {"type": "STRING", "description": "Location of the event - REQUIRED FIELD"},
                    "distances": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "distance": {"type": "STRING", "description": "Distance value (e.g., 25, 50, 100 miles)"},
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
                    "hasIntroRide": {"type": "BOOLEAN", "description": "Whether the event has an introductory ride"},
                    "is_canceled": {"type": "BOOLEAN", "description": "Whether the event has been canceled"}
                },
                "required": ["rideName", "date", "location"]
            }
        }
        
        # Create the prompt with structured output instructions
        prompt = f"""
        Extract all endurance ride events from this AERC calendar HTML.
        
        CRITICAL INSTRUCTIONS:
        1. Every event MUST have the 'rideName', 'date', and 'location' fields.
        2. If exact values aren't found, make your best informed guess.
        3. All dates must be in YYYY-MM-DD format (example: 2024-06-15).
        4. Extract every event you can find, even if some are partial.
        5. If an event has multiple days, include each day as a separate distance.
        
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
            
            # Count total event elements for metrics
            event_elements = self._count_event_elements(soup)
            self.metrics['events_found'] += event_elements
            logger.info(f"Found approximately {event_elements} event elements in HTML")
            
            # Look for natural boundaries like table rows or divs
            chunks = []
            
            # Try to find event containers (table rows, divs with event info, etc.)
            rows = soup.find_all('tr')
            if len(rows) > 5:  # If we have a table structure
                logger.info(f"Using table row chunking strategy for {len(rows)} rows")
                current_chunk = ""
                chunk_rows = []
                max_rows_per_chunk = 50  # Adjust based on typical row size
                
                for i, row in enumerate(rows):
                    chunk_rows.append(str(row))
                    
                    if len(chunk_rows) >= max_rows_per_chunk or i == len(rows) - 1:
                        # Create a chunk with a proper HTML structure
                        chunk_html = f"<table>{''.join(chunk_rows)}</table>"
                        chunks.append(chunk_html)
                        logger.info(f"Created chunk with {len(chunk_rows)} table rows ({len(chunk_html)} bytes)")
                        chunk_rows = []
                
                logger.info(f"Created {len(chunks)} chunks using table row strategy")
                return chunks
            
            # If no table structure, try divs with event-related classes
            event_divs = soup.find_all('div', class_=lambda c: c and any(keyword in c.lower() for keyword in ['event', 'ride', 'calendar', 'calendarRow']))
            if len(event_divs) > 0:
                logger.info(f"Using div chunking strategy for {len(event_divs)} divs")
                
                current_chunk = []
                current_chunk_size = 0
                max_chunk_size = self.max_html_chunk_size
                
                for i, div in enumerate(event_divs):
                    div_str = str(div)
                    div_size = len(div_str)
                    
                    # Check if adding this div would exceed the chunk size
                    if current_chunk_size + div_size > max_chunk_size and current_chunk:
                        # Create a chunk with all the collected divs
                        chunk_html = f"<div class='event-container'>{''.join(current_chunk)}</div>"
                        chunks.append(chunk_html)
                        logger.info(f"Created chunk with {len(current_chunk)} event divs ({len(chunk_html)} bytes)")
                        current_chunk = []
                        current_chunk_size = 0
                    
                    current_chunk.append(div_str)
                    current_chunk_size += div_size
                
                # Add the last chunk if there's anything left
                if current_chunk:
                    chunk_html = f"<div class='event-container'>{''.join(current_chunk)}</div>"
                    chunks.append(chunk_html)
                    logger.info(f"Created final chunk with {len(current_chunk)} event divs ({len(chunk_html)} bytes)")
                
                logger.info(f"Created {len(chunks)} chunks using div chunking strategy")
                return chunks
                
            # No clear event containers, try to split by common closing tags
            logger.info("No table rows or event divs found, using tag boundary chunking")
            chunks = self._split_by_tag_boundaries(html)
            logger.info(f"Created {len(chunks)} chunks using tag boundary strategy")
            return chunks
            
        except Exception as e:
            logger.warning(f"Error parsing HTML with BeautifulSoup: {e}")
            # Fallback to tag-boundary splitting
            logger.info("Falling back to tag boundary chunking due to parsing error")
            chunks = self._split_by_tag_boundaries(html)
            logger.info(f"Created {len(chunks)} chunks using tag boundary fallback strategy")
            return chunks
    
    def _count_event_elements(self, soup) -> int:
        """Count the number of event elements in the HTML."""
        # Look for various event indicators
        event_count = 0
        
        # First try to find elements with the class 'calendarRow' which is commonly used in AERC
        calendar_rows = soup.find_all('div', class_='calendarRow')
        if calendar_rows:
            event_count = len(calendar_rows)
            logger.info(f"🔍 EVENTS FOUND: {event_count} calendar rows")
            return event_count
        
        # Try table rows with specific classes or containing event info
        rows = soup.find_all('tr', class_=lambda c: c and any(keyword in c.lower() for keyword in ['event', 'ride', 'calendar']))
        if rows:
            event_count = len(rows)
            logger.info(f"🔍 EVENTS FOUND: {event_count} table rows with event-related classes")
            return event_count
        
        # Try any table rows that might contain event data
        all_rows = soup.find_all('tr')
        if all_rows and len(all_rows) > 5:  # Ignore small tables that might be headers
            # Check if rows have date patterns or location info
            event_rows = []
            for row in all_rows:
                text = row.get_text()
                # Look for date patterns
                if re.search(r'\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2}', text):
                    event_rows.append(row)
                # Look for location patterns (state abbreviations)
                elif re.search(r'\b[A-Z]{2}\b', text) and len(text) > 30:  # Avoid false positives
                    event_rows.append(row)
            
            if event_rows:
                event_count = len(event_rows)
                logger.info(f"🔍 EVENTS FOUND: {event_count} table rows with date/location patterns")
                return event_count
        
        # Try div elements with event-related classes
        divs = soup.find_all('div', class_=lambda c: c and any(keyword in c.lower() for keyword in ['event', 'ride', 'calendar']))
        if divs:
            event_count = len(divs)
            logger.info(f"🔍 EVENTS FOUND: {event_count} divs with event-related classes")
            return event_count
        
        # Try list items that might contain events
        list_items = soup.find_all('li', class_=lambda c: c and any(keyword in c.lower() for keyword in ['event', 'ride', 'calendar']))
        if list_items:
            event_count = len(list_items)
            logger.info(f"🔍 EVENTS FOUND: {event_count} list items with event-related classes")
            return event_count
        
        # If we can't find specific event elements, estimate based on common patterns in the whole text
        # Check for date patterns in text
        text = soup.get_text()
        date_patterns = re.findall(r'\b\d{1,2}/\d{1,2}/\d{4}\b|\b\d{4}-\d{2}-\d{2}\b', text)
        if date_patterns:
            event_count = len(date_patterns)
            logger.info(f"🔍 EVENTS FOUND: {event_count} date patterns in text")
            return event_count
        
        logger.warning("⚠️ NO EVENTS FOUND IN HTML CHUNK - could not detect any recognizable event elements")
        return event_count  # Return 0 if we couldn't identify events
    
    def _split_by_tag_boundaries(self, html: str) -> List[str]:
        """Split HTML by tag boundaries like </div>, </tr>, etc."""
        chunks = []
        current_pos = 0
        current_chunk = ""
        
        # Common closing tags that might indicate logical boundaries
        boundary_tags = ['</div>', '</tr>', '</table>', '</section>', '</li>', '</article>']
        
        while current_pos < len(html):
            # Find the next closest tag boundary
            next_boundary = len(html)
            chosen_boundary = None
            
            for tag in boundary_tags:
                tag_pos = html.find(tag, current_pos)
                if tag_pos != -1 and tag_pos < next_boundary:
                    next_boundary = tag_pos
                    chosen_boundary = tag
            
            # If we found a boundary and adding content up to and including it wouldn't exceed limit
            if chosen_boundary and (len(current_chunk) + (next_boundary + len(chosen_boundary) - current_pos)) <= self.max_html_chunk_size:
                # Add content up to and including the boundary tag
                current_chunk += html[current_pos:next_boundary + len(chosen_boundary)]
                current_pos = next_boundary + len(chosen_boundary)
            else:
                # If we're about to exceed the limit or no boundary found
                # Check if we have content already
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""
                else:
                    # If no content yet, we need to split arbitrarily (as a last resort)
                    end_pos = min(current_pos + self.max_html_chunk_size, len(html))
                    chunks.append(html[current_pos:end_pos])
                    current_pos = end_pos
        
        # Add any remaining content
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def _split_by_size(self, html: str) -> List[str]:
        """Split HTML by size, trying to preserve tag boundaries. (Legacy method)"""
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
                sub_chunks = self._split_by_tag_boundaries(html_chunk)
                logger.info(f"Split chunk {chunk_idx} into {len(sub_chunks)} sub-chunks")
                self.metrics['chunk_split_count'] += 1
                
                # Process each sub-chunk and combine results
                all_results = []
                for i, sub_chunk in enumerate(sub_chunks):
                    sub_results = await self._extract_data_with_fallbacks(sub_chunk, f"{chunk_idx}.{i}")
                    if sub_results:
                        all_results.extend(sub_results)
                        self.metrics['events_extracted'] += len(sub_results)
                
                return all_results
        
        # Process the chunk directly if it's not too large
        results = await self._extract_data_with_fallbacks(html_chunk, chunk_idx)
        if results:
            self.metrics['events_extracted'] += len(results)
        return results
    
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
                max_output_tokens=self.settings.max_output_tokens  # Use config value instead of hardcoding
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
        
        # Try regular API with primary model with retry mechanism
        max_retries = 2
        for retry in range(max_retries + 1):
            try:
                prompt = self._create_prompt(html_chunk)
                
                # Use config with explicit token limits
                config = types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=self.settings.max_output_tokens  # Use config value instead of hardcoding
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
                
                # If we get here but have no results, log and try again
                if retry < max_retries:
                    logger.info(f"No results from primary model on attempt {retry+1}, retrying...")
                    await asyncio.sleep(1)  # Short delay before retry
                
            except Exception as e:
                self._track_error(e, f"Primary model failed on attempt {retry+1} for chunk {chunk_idx}")
                if retry < max_retries:
                    logger.info(f"Retrying primary model for chunk {chunk_idx}...")
                    await asyncio.sleep(1)  # Short delay before retry
        
        # Try fallback model as last resort
        logger.info(f"Using fallback model for chunk {chunk_idx}")
        try:
            prompt = self._create_prompt(html_chunk)
            
            # Use more conservative settings for fallback
            config = types.GenerateContentConfig(
                temperature=0.1,  # Lower temperature for more consistent results
                max_output_tokens=self.settings.max_output_tokens  # Use config value instead of hardcoding
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
        try:
            # The Gemini API provides usage stats in different ways depending on the version
            # First try the standard format
            if hasattr(response, 'usage') and response.usage:
                if hasattr(response.usage, 'total_tokens'):
                    self.metrics['total_tokens'] += response.usage.total_tokens
                    self.metrics['token_counts'].append(response.usage.total_tokens)
                    logger.info(f"Total tokens used for chunk {chunk_idx}: {response.usage.total_tokens}")
                
                # Check if we're close to input token limits
                if hasattr(response.usage, 'input_tokens'):
                    input_tokens = response.usage.input_tokens
                    model_limit = self.model_token_limits.get(self.settings.primary_model, 8192)
                    if input_tokens > model_limit * 0.85:  # If over 85% of limit
                        logger.warning(f"Input tokens ({input_tokens}) close to model limit for chunk {chunk_idx}")
                
                # Check if we're close to output token limits
                if hasattr(response.usage, 'output_tokens'):
                    output_tokens = response.usage.output_tokens
                    output_token_limit = self.settings.max_output_tokens
                    if output_tokens > output_token_limit * 0.85:  # Close to 85% of the configured limit
                        logger.warning(f"Output tokens ({output_tokens}) close to limit for chunk {chunk_idx}")
                        
                    # Log token usage for monitoring
                    logger.info(f"Output tokens for chunk {chunk_idx}: {output_tokens} (max: {output_token_limit})")
            # Try alternative format (direct attributes)
            elif hasattr(response, 'prompt_token_count') and hasattr(response, 'candidates'):
                prompt_tokens = response.prompt_token_count
                # Sum token counts from all candidates
                candidate_tokens = sum(c.token_count for c in response.candidates if hasattr(c, 'token_count'))
                total_tokens = prompt_tokens + candidate_tokens
                
                self.metrics['total_tokens'] += total_tokens
                self.metrics['token_counts'].append(total_tokens)
                
                logger.info(f"Total tokens for chunk {chunk_idx}: {total_tokens} (prompt: {prompt_tokens}, candidates: {candidate_tokens})")
                
                # Check token limits
                model_limit = self.model_token_limits.get(self.settings.primary_model, 8192)
                if prompt_tokens > model_limit * 0.85:
                    logger.warning(f"Prompt tokens ({prompt_tokens}) close to model limit for chunk {chunk_idx}")
            # Try another alternative for newer versions of the API
            elif hasattr(response, '_response') and hasattr(response._response, 'usage_metadata'):
                usage = response._response.usage_metadata
                if hasattr(usage, 'total_token_count'):
                    total_tokens = usage.total_token_count
                    self.metrics['total_tokens'] += total_tokens
                    self.metrics['token_counts'].append(total_tokens)
                    logger.info(f"Total tokens used for chunk {chunk_idx}: {total_tokens}")
            else:
                # If we couldn't find usage data in any format, log it but don't treat as an error
                logger.info(f"Token usage data not available in standard format for chunk {chunk_idx}")
                # Add a basic estimate of token usage based on response text length
                if hasattr(response, 'text'):
                    # Rough estimate: 1 token ≈ 4 characters
                    estimated_tokens = len(response.text) // 4
                    logger.info(f"Estimated response tokens for chunk {chunk_idx}: ~{estimated_tokens}")
        except Exception as e:
            # Don't let token tracking issues disrupt the main flow
            logger.warning(f"Error tracking token usage for chunk {chunk_idx}: {e}")
    
    async def extract_data(self, html_chunk: str, chunk_idx: int = 0) -> List[Dict[str, Any]]:
        """Extract structured data from HTML using Gemini API."""
        self.metrics['calls'] += 1
        self.metrics['chunks_processed'] += 1
        
        # Log chunk processing start at INFO level
        logger.info(f"Processing chunk {chunk_idx} (size: {len(html_chunk)} bytes)")
        
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
                        logger.info(f"Processing sub-chunk {chunk_idx}.{i} (size: {len(sub_chunk)} bytes)")
                        sub_results = await self._process_html_chunk(sub_chunk, f"{chunk_idx}.{i}")
                        if sub_results:
                            logger.info(f"Extracted {len(sub_results)} events from sub-chunk {chunk_idx}.{i}")
                            all_results.extend(sub_results)
                        else:
                            logger.warning(f"No events extracted from sub-chunk {chunk_idx}.{i}")
                    except Exception as e:
                        logger.error(f"Error processing sub-chunk {chunk_idx}.{i}: {e}")
                        # Continue with other chunks even if one fails
                
                if all_results:
                    # Map fields to match database schema
                    mapped_results = self._map_fields(all_results)
                    logger.info(f"Extracted and mapped a total of {len(mapped_results)} events from chunk {chunk_idx}")
                    return mapped_results
                else:
                    raise AIError("Gemini", f"Failed to extract data from all sub-chunks of chunk {chunk_idx}")
        
        # If not too large, process directly
        try:
            results = await self._process_html_chunk(html_chunk, chunk_idx)
            if results:
                # Map fields to match database schema
                mapped_results = self._map_fields(results)
                logger.info(f"Extracted and mapped {len(mapped_results)} events from chunk {chunk_idx}")
                return mapped_results
            else:
                raise AIError("Gemini", f"No data extracted from chunk {chunk_idx}")
        except Exception as e:
            logger.error(f"Error processing chunk {chunk_idx}: {str(e)}")
            raise AIError("Gemini", f"Failed to extract data from chunk {chunk_idx}: {str(e)}")
    
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
        """Map fields from the extracted data to the expected schema."""
        if not events_data:
            return []
        
        mapped_events = []
        
        for event in events_data:
            try:
                # Map basic fields with fallbacks for different field names
                name = event.get('rideName') or event.get('name') or event.get('title') or "Unknown Event"
                
                # Check if event is canceled
                is_canceled = False
                
                # Check in name using regex (detects both US/UK spelling)
                if re.search(r'cancel(?:l)?ed', name, re.IGNORECASE) or any(keyword in name.lower() for keyword in ['cancel', 'cancelled', 'canceled', 'postponed', 'reschedule']):
                    is_canceled = True
                    logger.info(f"Detected canceled event from name: {name}")
                
                # Check if it was directly identified by Gemini (either spelling)
                if event.get('is_canceled') is True or event.get('is_cancelled') is True:
                    is_canceled = True
                    logger.info(f"Detected canceled event from Gemini metadata: {name}")
                
                # Extract date information
                date_start = event.get('date') or event.get('dateStart') or event.get('startDate')
                date_end = event.get('dateEnd') or event.get('endDate')
                
                # Extract location information
                location = event.get('location') or event.get('venue') or "Unknown Location"
                
                # Extract region information
                region = event.get('region') or event.get('state') or ""
                
                # Extract ride manager information
                ride_manager = event.get('rideManager') or event.get('manager') or event.get('organizer') or ""
                
                # Extract contact information
                manager_contact = ""
                manager_email = None
                manager_phone = None
                
                if event.get('rideManagerContact'):
                    contact = event['rideManagerContact']
                    contact_parts = []
                    
                    if isinstance(contact, dict):
                        if contact.get('name'):
                            contact_parts.append(f"Name: {contact['name']}")
                        if contact.get('email'):
                            manager_email = contact['email']
                            contact_parts.append(f"Email: {contact['email']}")
                        if contact.get('phone'):
                            manager_phone = contact['phone']
                            contact_parts.append(f"Phone: {contact['phone']}")
                    
                    manager_contact = "\n".join(contact_parts)
                
                # Extract individual contact fields if they exist
                if event.get('managerEmail'):
                    manager_email = event['managerEmail']
                if event.get('managerPhone'):
                    manager_phone = event['managerPhone']
                
                # Extract control judges
                judges = []
                if event.get('controlJudges'):
                    judges_data = event['controlJudges']
                    if isinstance(judges_data, list):
                        for judge in judges_data:
                            if isinstance(judge, dict) and judge.get('name'):
                                role = judge.get('role', 'Judge')
                                judges.append(f"{role}: {judge['name']}")
                            elif isinstance(judge, str):
                                judges.append(judge)
                
                # Extract distances
                distances = []
                if event.get('distances'):
                    if isinstance(event['distances'], list):
                        for distance in event['distances']:
                            if isinstance(distance, dict) and distance.get('distance'):
                                distances.append(distance['distance'])
                            elif isinstance(distance, str):
                                distances.append(distance)
                    elif isinstance(event['distances'], str):
                        distances = [event['distances']]
                
                # Determine end date from distances if available
                if not date_end and event.get('distances') and isinstance(event['distances'], list):
                    latest_date = None
                    for distance in event['distances']:
                        if isinstance(distance, dict) and distance.get('date'):
                            if latest_date is None or distance['date'] > latest_date:
                                latest_date = distance['date']
                    
                    if latest_date:
                        date_end = latest_date
                
                # Map other fields
                map_url = event.get('mapLink') or event.get('mapUrl')
                has_intro_ride = event.get('hasIntroRide', False) or event.get('introRide', False)
                external_id = str(event.get('tag') or event.get('id') or event.get('external_id') or "")
                
                # Create mapped event
                mapped_event = {
                    'name': name,
                    'date_start': date_start,
                    'location': location,
                    'region': region,
                    'ride_manager': ride_manager,
                    'manager_contact': manager_contact,
                    'manager_email': manager_email,
                    'manager_phone': manager_phone,
                    'judges': judges,
                    'distances': distances,
                    'map_link': map_url,
                    'has_intro_ride': has_intro_ride,
                    'external_id': external_id if external_id else None,
                    'event_type': 'endurance',
                    'source': 'AERC',
                    'is_canceled': is_canceled
                }
                
                # Add end date if available
                if date_end:
                    mapped_event['date_end'] = date_end
                
                # Store original event details for reference
                mapped_event['event_details'] = event
                
                mapped_events.append(mapped_event)
                
            except Exception as e:
                logger.error(f"Error mapping event fields: {e}")
                logger.error(f"Event data: {event}")
                continue
        
        return mapped_events

class GeminiClientStream(GeminiClient):
    """Gemini API client for streaming content."""

    async def generate_content_stream(self, prompt):
        """Generate content from Gemini API with streaming."""
        retries = 0
        while retries <= self.max_retries:
            try:
                response = await self.model.generate_content_async(prompt)
                # Since response is a coroutine, not a stream, we need to await it
                # and then return the result, not try to iterate it
                return await response
            except Exception as e:
                if retries == self.max_retries:
                    logger.error(f"Failed to generate content after {retries} retries: {str(e)}")
                    raise
                retries += 1
                logger.warning(f"Error generating content (retry {retries}/{self.max_retries}): {str(e)}")
                # Exponential backoff
                await asyncio.sleep(2 ** retries)

    async def extract_events_stream(self, chunk, chunk_index=0):
        """Extract events from HTML chunk using streaming API."""
        prompt = self._create_structured_prompt(chunk, chunk_index)
        
        try:
            # Use non-streaming method since streaming is problematic
            response = await self.generate_content_stream(prompt)
            return self._process_response(response, chunk_index)
        except Exception as e:
            logger.error(f"Error extracting events with streaming API for chunk {chunk_index}: {str(e)}")
            return []

    async def extract_events(self, chunk: str) -> List[Dict[str, Any]]:
        """Extract events from HTML chunk using Gemini."""
        try:
            # Log start of extraction
            logger.info("Starting event extraction from chunk")
            
            # Create prompt and schema
            prompt_data = self._create_prompt(chunk)
            prompt = prompt_data["prompt"]
            schema = prompt_data["schema"]
            
            # Log prompt details
            logger.debug(f"Created prompt with schema: {json.dumps(schema, indent=2)}")
            
            # Make API call
            response = await self._make_api_call(prompt, schema)
            
            # Log response
            if response:
                logger.info(f"Successfully extracted {len(response)} events from chunk")
                logger.debug(f"Extracted events: {json.dumps(response, indent=2)}")
            else:
                logger.warning("No events extracted from chunk")
            
            return response or []
            
        except Exception as e:
            logger.error(f"Error extracting events from chunk: {str(e)}")
            return []