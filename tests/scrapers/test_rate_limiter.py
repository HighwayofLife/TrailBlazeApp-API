"""Tests for rate limiting module."""

import pytest
import asyncio
from datetime import datetime, timedelta
from scrapers.rate_limiter import TokenBucket, RateLimiter

@pytest.fixture
def token_bucket():
    """Create token bucket instance."""
    return TokenBucket(rate=10.0, capacity=10)

@pytest.fixture
def rate_limiter():
    """Create rate limiter instance."""
    return RateLimiter(requests_per_second=10.0, max_burst=10)

@pytest.mark.asyncio
async def test_token_bucket_initial_state(token_bucket):
    """Test initial state of token bucket."""
    assert token_bucket.tokens == token_bucket.capacity
    assert token_bucket.rate == 10.0

@pytest.mark.asyncio
async def test_token_bucket_acquire(token_bucket):
    """Test acquiring tokens."""
    # Should get tokens immediately
    wait_time = await token_bucket.acquire(5)
    assert wait_time == 0.0
    assert token_bucket.tokens == 5

@pytest.mark.asyncio
async def test_token_bucket_refill(token_bucket):
    """Test token refill behavior."""
    # Use all tokens
    await token_bucket.acquire(10)
    assert token_bucket.tokens == 0
    
    # Wait for refill
    await asyncio.sleep(0.2)  # Should get 2 tokens back
    token_bucket._refill()
    assert 1.9 <= token_bucket.tokens <= 2.1

@pytest.mark.asyncio
async def test_token_bucket_exceed_capacity(token_bucket):
    """Test requesting more tokens than capacity."""
    with pytest.raises(ValueError):
        await token_bucket.acquire(11)

@pytest.mark.asyncio
async def test_rate_limiter_basic_operation(rate_limiter):
    """Test basic rate limiter operation."""
    async def test_request():
        return "success"
    
    result = await rate_limiter.execute_with_retry(test_request)
    assert result == "success"
    
    metrics = rate_limiter.get_metrics()
    assert metrics['requests'] == 1
    assert metrics['backoffs'] == 0
    assert metrics['success_rate'] == 100.0

@pytest.mark.asyncio
async def test_rate_limiter_throttling(rate_limiter):
    """Test rate limiting throttling."""
    # Make many requests quickly
    start_time = asyncio.get_event_loop().time()
    
    for _ in range(15):  # More than burst size
        await rate_limiter.acquire()
    
    end_time = asyncio.get_event_loop().time()
    duration = end_time - start_time
    
    # Should take at least 0.5 seconds due to rate limiting
    assert duration >= 0.5
    assert rate_limiter.metrics['throttled'] > 0

@pytest.mark.asyncio
async def test_rate_limiter_retries(rate_limiter):
    """Test retry behavior."""
    attempt_count = 0
    
    async def failing_request():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
            raise Exception("Temporary failure")
        return "success"
    
    result = await rate_limiter.execute_with_retry(failing_request)
    assert result == "success"
    assert attempt_count == 3
    assert rate_limiter.metrics['backoffs'] == 2

@pytest.mark.asyncio
async def test_rate_limiter_adaptive_backoff(rate_limiter):
    """Test adaptive backoff behavior."""
    # Simulate several failed requests
    for _ in range(5):
        rate_limiter.update_metrics(False)
    
    # Should trigger backoff
    assert rate_limiter._should_backoff()
    
    # Add some successful requests
    for _ in range(10):
        rate_limiter.update_metrics(True)
    
    # Should no longer need backoff
    assert not rate_limiter._should_backoff()

@pytest.mark.asyncio
async def test_rate_limiter_request_history_cleanup(rate_limiter):
    """Test request history cleanup."""
    # Add some old entries
    old_time = datetime.now() - timedelta(minutes=10)
    rate_limiter.request_history[old_time] = True
    
    # Add some recent entries
    rate_limiter.request_history[datetime.now()] = True
    
    # Check backoff (triggers cleanup)
    rate_limiter._should_backoff()
    
    # Old entries should be removed
    assert old_time not in rate_limiter.request_history

@pytest.mark.asyncio
async def test_rate_limiter_metrics(rate_limiter):
    """Test metrics collection."""
    # Mix of successful and failed requests
    rate_limiter.update_metrics(True)
    rate_limiter.update_metrics(True)
    rate_limiter.update_metrics(False)
    
    metrics = rate_limiter.get_metrics()
    assert metrics['requests'] == 0  # Only tracks actual acquire() calls
    assert metrics['backoffs'] == 1
    assert 'success_rate' in metrics

@pytest.mark.asyncio
async def test_rate_limiter_reset(rate_limiter):
    """Test resetting rate limiter state."""
    # Add some metrics
    await rate_limiter.acquire()
    rate_limiter.update_metrics(False)
    
    # Reset
    rate_limiter.reset()
    
    # Check metrics are cleared
    metrics = rate_limiter.get_metrics()
    assert metrics['requests'] == 0
    assert metrics['backoffs'] == 0
    assert metrics['throttled'] == 0
    assert len(rate_limiter.request_history) == 0