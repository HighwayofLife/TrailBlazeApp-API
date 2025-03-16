"""
Network handling module for making HTTP requests with retry logic.
"""

import asyncio
import logging
from typing import Dict, Optional, Any
import aiohttp
from .config import ScraperSettings
from .exceptions import NetworkError

logger = logging.getLogger(__name__)

class NetworkHandler:
    """Handles HTTP requests with retry logic."""
    
    def __init__(self, settings: ScraperSettings):
        self.settings = settings
        self.metrics = {
            'requests': 0,
            'errors': 0,
            'retries': 0
        }
    
    async def make_request(
        self, 
        url: str, 
        method: str = "GET", 
        data: Optional[Dict[str, Any]] = None,
        retry_count: int = 0
    ) -> Optional[str]:
        """Make an HTTP request with retry logic."""
        self.metrics['requests'] += 1
        
        if retry_count >= self.settings.max_retries:
            self.metrics['errors'] += 1
            error_msg = f"Max retries ({self.settings.max_retries}) exceeded for {url}"
            logger.error(error_msg)
            raise NetworkError(error_msg)
            
        try:
            timeout = aiohttp.ClientTimeout(total=self.settings.request_timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                request_func = session.post if method == "POST" else session.get
                async with request_func(url, data=data, headers=self.settings.default_headers) as response:
                    if response.status == 429:  # Too Many Requests
                        retry_after = int(response.headers.get('Retry-After', self.settings.retry_delay))
                        logger.warning(f"Rate limited. Waiting {retry_after} seconds before retry")
                        await asyncio.sleep(retry_after)
                        self.metrics['retries'] += 1
                        return await self.make_request(url, method, data, retry_count + 1)
                        
                    elif response.status >= 500:  # Server errors
                        logger.warning(f"Server error {response.status}. Retrying in {self.settings.retry_delay} seconds")
                        await asyncio.sleep(self.settings.retry_delay)
                        self.metrics['retries'] += 1
                        return await self.make_request(url, method, data, retry_count + 1)
                        
                    elif response.status != 200:
                        self.metrics['errors'] += 1
                        error_msg = f"HTTP {response.status} error for {url}"
                        logger.error(error_msg)
                        raise NetworkError(error_msg)
                        
                    return await response.text()
                    
        except asyncio.TimeoutError:
            logger.warning(f"Request timeout. Retrying in {self.settings.retry_delay} seconds")
            await asyncio.sleep(self.settings.retry_delay)
            self.metrics['retries'] += 1
            return await self.make_request(url, method, data, retry_count + 1)
            
        except Exception as e:
            self.metrics['errors'] += 1
            logger.error(f"Request error: {e}")
            if retry_count < self.settings.max_retries:
                self.metrics['retries'] += 1
                await asyncio.sleep(self.settings.retry_delay)
                return await self.make_request(url, method, data, retry_count + 1)
            raise NetworkError(f"Request failed: {str(e)}")
    
    def get_metrics(self) -> Dict[str, int]:
        """Get network metrics."""
        return self.metrics.copy()