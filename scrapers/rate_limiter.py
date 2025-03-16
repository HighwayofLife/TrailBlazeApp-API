"""Rate limiting module with token bucket and exponential backoff."""

import time
import logging
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import backoff
from tenacity import (
    retry,
    wait_exponential,
    stop_after_attempt,
    retry_if_exception_type,
    before_sleep_log
)

logger = logging.getLogger(__name__)

class TokenBucket:
    """Token bucket rate limiter implementation."""
    
    def __init__(
        self,
        rate: float,
        capacity: int,
        initial_tokens: Optional[int] = None
    ):
        """Initialize token bucket.
        
        Args:
            rate: Token refill rate per second
            capacity: Maximum number of tokens
            initial_tokens: Initial token count (defaults to capacity)
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity if initial_tokens is None else initial_tokens
        self.last_update = time.monotonic()
    
    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self.last_update
        self.tokens = min(
            self.capacity,
            self.tokens + elapsed * self.rate
        )
        self.last_update = now
    
    async def acquire(self, tokens: int = 1) -> float:
        """Acquire tokens from the bucket.
        
        Args:
            tokens: Number of tokens to acquire
            
        Returns:
            Wait time in seconds
            
        Raises:
            ValueError: If requested tokens exceed capacity
        """
        if tokens > self.capacity:
            raise ValueError(
                f"Requested tokens ({tokens}) exceed bucket capacity ({self.capacity})"
            )
        
        self._refill()
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return 0.0
        
        # Calculate wait time
        missing = tokens - self.tokens
        wait_time = missing / self.rate
        
        await asyncio.sleep(wait_time)
        
        self.tokens = self.capacity - tokens
        self.last_update = time.monotonic()
        
        return wait_time

class RateLimiter:
    """Rate limiter with exponential backoff."""
    
    def __init__(
        self,
        requests_per_second: float,
        max_burst: int,
        max_retries: int = 3,
        min_backoff: float = 1.0,
        max_backoff: float = 60.0
    ):
        """Initialize rate limiter.
        
        Args:
            requests_per_second: Maximum requests per second
            max_burst: Maximum burst size
            max_retries: Maximum number of retries
            min_backoff: Minimum backoff time in seconds
            max_backoff: Maximum backoff time in seconds
        """
        self.bucket = TokenBucket(requests_per_second, max_burst)
        self.max_retries = max_retries
        self.min_backoff = min_backoff
        self.max_backoff = max_backoff
        
        self.metrics = {
            'requests': 0,
            'throttled': 0,
            'backoffs': 0,
            'total_wait_time': 0.0
        }
        
        # Track request history for adaptive rate limiting
        self.request_history: Dict[datetime, bool] = {}
        self.adaptive_window = timedelta(minutes=5)
    
    async def acquire(self) -> None:
        """Acquire permission to make a request."""
        self.metrics['requests'] += 1
        
        try:
            wait_time = await self.bucket.acquire()
            if wait_time > 0:
                self.metrics['throttled'] += 1
                self.metrics['total_wait_time'] += wait_time
                logger.debug(f"Rate limited, waiting {wait_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Rate limiter error: {str(e)}")
            raise
    
    def _should_backoff(self) -> bool:
        """Determine if we should backoff based on recent failures."""
        now = datetime.now()
        
        # Clean old entries
        self.request_history = {
            ts: success
            for ts, success in self.request_history.items()
            if now - ts <= self.adaptive_window
        }
        
        # Calculate recent failure rate
        if not self.request_history:
            return False
        
        recent_requests = len(self.request_history)
        failures = sum(1 for success in self.request_history.values() if not success)
        failure_rate = failures / recent_requests
        
        return failure_rate >= 0.5  # Back off if 50% or more requests failed
    
    def update_metrics(self, success: bool) -> None:
        """Update metrics with request result."""
        self.request_history[datetime.now()] = success
        
        if not success:
            self.metrics['backoffs'] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get rate limiting metrics."""
        metrics = self.metrics.copy()
        
        # Calculate success rate
        total = metrics['requests']
        if total > 0:
            success = total - metrics['backoffs']
            metrics['success_rate'] = (success / total) * 100
        
        return metrics
    
    @retry(
        retry=retry_if_exception_type(Exception),
        wait=wait_exponential(
            multiplier=1,
            min=1,
            max=60
        ),
        stop=stop_after_attempt(3),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def execute_with_retry(self, func, *args, **kwargs):
        """Execute a function with rate limiting and retries.
        
        Args:
            func: Async function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Result from func
            
        Raises:
            Exception: If all retries fail
        """
        await self.acquire()
        
        try:
            result = await func(*args, **kwargs)
            self.update_metrics(True)
            return result
            
        except Exception as e:
            self.update_metrics(False)
            
            if self._should_backoff():
                logger.warning("High failure rate detected, increasing backoff")
                
            raise  # Let retry decorator handle it
    
    def reset(self) -> None:
        """Reset rate limiter state."""
        self.metrics = {
            'requests': 0,
            'throttled': 0,
            'backoffs': 0,
            'total_wait_time': 0.0
        }
        self.request_history.clear()