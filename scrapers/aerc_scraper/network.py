"""
Network handling module for making HTTP requests with retry logic.
"""

import asyncio
import logging
from typing import Dict, Optional, Any
import aiohttp
from ..config import ScraperBaseSettings
from ..exceptions import NetworkError
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class NetworkHandler:
    """Handles HTTP requests with retry logic."""
    
    def __init__(self, settings: ScraperBaseSettings):
        self.settings = settings
        self.metrics = {
            'requests': 0,
            'success': 0,
            'errors': 0,
            'retries': 0,
            'cached': 0,
            'total_bytes': 0,
            'total_time': 0
        }
        
        # Set default values for required properties if not in settings
        self.request_timeout = getattr(settings, 'request_timeout', 30)
        self.retry_delay = getattr(settings, 'retry_delay', 2)
    
    async def make_request(
        self, 
        url: str, 
        method: str = "GET", 
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        retry_count: int = 0
    ) -> Optional[str]:
        """Make an HTTP request with retry logic."""
        start_time = asyncio.get_event_loop().time()
        self.metrics['requests'] += 1
        
        if retry_count >= self.settings.max_retries:
            self.metrics['errors'] += 1
            error_msg = (
                f"Max retries ({self.settings.max_retries}) exceeded for {url}. "
                f"Last error occurred after {retry_count} attempts."
            )
            logger.error(error_msg)
            raise NetworkError(error_msg)
            
        try:
            timeout = aiohttp.ClientTimeout(total=self.request_timeout)
            request_headers = {**self.settings.default_headers, **(headers or {})}
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                request_func = session.post if method == "POST" else session.get
                async with request_func(url, data=data, headers=request_headers) as response:
                    if response.status == 429:  # Too Many Requests
                        retry_after = int(response.headers.get('Retry-After', self.retry_delay))
                        logger.warning(
                            f"Rate limited by {url}. Waiting {retry_after} seconds before retry. "
                            f"Attempt {retry_count + 1}/{self.settings.max_retries}"
                        )
                        await asyncio.sleep(retry_after)
                        self.metrics['retries'] += 1
                        return await self.make_request(url, method, data, headers, retry_count + 1)
                        
                    elif response.status >= 500:  # Server errors
                        logger.warning(
                            f"Server error {response.status} from {url}. "
                            f"Retrying in {self.retry_delay} seconds. "
                            f"Attempt {retry_count + 1}/{self.settings.max_retries}"
                        )
                        await asyncio.sleep(self.retry_delay)
                        self.metrics['retries'] += 1
                        return await self.make_request(url, method, data, headers, retry_count + 1)
                        
                    elif response.status != 200:
                        self.metrics['errors'] += 1
                        error_msg = (
                            f"HTTP {response.status} error for {url}. "
                            f"Headers: {dict(response.headers)}. "
                            f"Response: {await response.text()[:200]}..."
                        )
                        logger.error(error_msg)
                        raise NetworkError(error_msg)
                    
                    content = await response.text()
                    self.metrics['success'] += 1
                    self.metrics['total_bytes'] += len(content.encode('utf-8'))
                    self.metrics['total_time'] += asyncio.get_event_loop().time() - start_time
                    
                    logger.debug(
                        f"Request to {url} succeeded. "
                        f"Status: {response.status}, "
                        f"Size: {len(content)} chars, "
                        f"Time: {asyncio.get_event_loop().time() - start_time:.2f}s"
                    )
                    
                    return content
                    
        except asyncio.TimeoutError:
            logger.warning(
                f"Request timeout to {url}. "
                f"Retrying in {self.retry_delay} seconds. "
                f"Attempt {retry_count + 1}/{self.settings.max_retries}"
            )
            await asyncio.sleep(self.retry_delay)
            self.metrics['retries'] += 1
            return await self.make_request(url, method, data, headers, retry_count + 1)
            
        except aiohttp.ClientError as e:
            logger.error(f"Network error for {url}: {str(e)}")
            self.metrics['errors'] += 1
            if retry_count < self.settings.max_retries:
                self.metrics['retries'] += 1
                await asyncio.sleep(self.retry_delay)
                return await self.make_request(url, method, data, headers, retry_count + 1)
            raise NetworkError(f"Network request failed: {str(e)}")
            
        except Exception as e:
            logger.exception(f"Unexpected error for {url}: {str(e)}")
            self.metrics['errors'] += 1
            if retry_count < self.settings.max_retries:
                self.metrics['retries'] += 1
                await asyncio.sleep(self.retry_delay)
                return await self.make_request(url, method, data, headers, retry_count + 1)
            raise NetworkError(f"Request failed: {str(e)}")
    
    def get_metrics(self) -> Dict[str, int]:
        """Get network metrics."""
        # Calculate average request time if we have successful requests
        if self.metrics['success'] > 0:
            self.metrics['avg_request_time'] = self.metrics['total_time'] / self.metrics['success']
        
        return self.metrics.copy()
        
    async def fetch_calendar(self) -> str:
        """Fetch the AERC calendar HTML."""
        logger.info("Fetching AERC calendar HTML")
        
        # First, get the calendar page to extract season IDs
        try:
            # Get the main calendar page
            calendar_html = await self.make_request(
                url=self.settings.calendar_url,
                method="GET"
            )
            
            if not calendar_html:
                raise NetworkError("Empty HTML content received from AERC calendar page")
            
            # Parse HTML to extract season IDs
            soup = BeautifulSoup(calendar_html, 'lxml')
            
            # Extract season IDs
            season_inputs = soup.select('input[name="season[]"]')
            season_ids = []
            
            for input_tag in season_inputs:
                season_id = input_tag.get('value')
                if season_id:
                    season_ids.append(season_id)
            
            if not season_ids:
                raise NetworkError("Failed to extract season IDs from calendar page")
                
            # Use only current and next year IDs
            season_ids = season_ids[:2]
            logger.info(f"Extracted season IDs: {season_ids}")
            
            # Prepare data for the POST request
            data = {
                'action': 'aerc_calendar_form',
                'calendar': 'calendar',
                'country[]': ['United States', 'Canada'],
                'within': '',
                'zip': '',
                'span[]': '#cal-span-season',
                'season[]': season_ids,
                'daterangefrom': '',
                'daterangeto': '',
                'distance[]': 'any',
            }
            
            # Make POST request to get calendar HTML
            response_text = await self.make_request(
                url=self.settings.base_url, 
                method="POST",
                data=data
            )
            
            if not response_text:
                raise NetworkError("Empty response received from calendar API")
            
            # Parse JSON response
            import json
            try:
                json_data = json.loads(response_text)
                if 'html' in json_data:
                    html_content = json_data['html']
                    logger.info(f"Successfully fetched AERC calendar HTML ({len(html_content)} bytes)")
                    return html_content
                else:
                    raise NetworkError("JSON response missing 'html' field")
            except json.JSONDecodeError:
                # If not JSON, might be direct HTML
                logger.info(f"Response is not JSON, assuming direct HTML ({len(response_text)} bytes)")
                return response_text
                
        except Exception as e:
            logger.error(f"Failed to fetch AERC calendar: {str(e)}")
            raise NetworkError(f"Failed to fetch AERC calendar: {str(e)}")