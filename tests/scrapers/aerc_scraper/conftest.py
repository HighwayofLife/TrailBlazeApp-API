"""Test configuration and fixtures for AERC scraper tests."""

import pytest
import asyncio
from pathlib import Path
import os
from scrapers.aerc_scraper.config import ScraperSettings

@pytest.fixture
def test_settings():
    """Create test settings with test-specific values."""
    return ScraperSettings(
        gemini_api_key="test_key",
        cache_dir="tests/cache",
        max_retries=2,
        retry_delay=1,
        request_timeout=5,
        cache_ttl=60,
        debug_mode=True,
        refresh_cache=True
    )

@pytest.fixture
def test_html():
    """Load test HTML fixture."""
    fixture_path = Path(__file__).parent / "fixtures" / "calendar.html"
    with fixture_path.open('r') as f:
        return f.read()

@pytest.fixture
def sample_events():
    """Return sample event data for testing."""
    return [
        {
            "rideName": "Test Ride 1",
            "date": "2024-03-15",
            "region": "W",
            "location": "Test Location 1",
            "distances": [
                {
                    "distance": "50",
                    "date": "2024-03-15",
                    "startTime": "6:30 AM"
                }
            ],
            "rideManager": "Test Manager",
            "rideManagerContact": {
                "name": "Test Manager",
                "email": "test@example.com",
                "phone": "123-456-7890"
            },
            "controlJudges": [
                {
                    "role": "Head Control Judge",
                    "name": "Test Judge"
                }
            ],
            "mapLink": "https://maps.google.com/test1",
            "hasIntroRide": True,
            "tag": 12345
        },
        {
            "rideName": "Test Ride 2",
            "date": "2024-03-16",
            "region": "W",
            "location": "Test Location 2",
            "distances": [
                {
                    "distance": "100",
                    "date": "2024-03-16",
                    "startTime": "5:30 AM"
                }
            ],
            "rideManager": "Test Manager 2",
            "mapLink": "https://maps.google.com/test2",
            "hasIntroRide": False,
            "tag": 67890
        }
    ]

@pytest.fixture
def mock_gemini_response():
    """Return mock Gemini API response."""
    return {
        "text": '[{"rideName": "Test Ride", "date": "2024-03-15"}]',
        "candidates": [{"content": {"text": '[{"rideName": "Test Ride", "date": "2024-03-15"}]'}}]
    }

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    """Set up test environment variables."""
    monkeypatch.setenv("AERC_GEMINI_API_KEY", "test_key")
    monkeypatch.setenv("AERC_DEBUG_MODE", "true")
    monkeypatch.setenv("AERC_REFRESH_CACHE", "true")