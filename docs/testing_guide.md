# Testing Guide

## Summary

This document outlines the testing strategy and procedures for the TrailBlazeApp-API. It covers unit testing, integration testing, end-to-end testing, and performance testing. The guide includes instructions on how to run tests, write new tests, and interpret test results.

## Table of Contents

- [Testing Philosophy](#testing-philosophy)
- [Testing Infrastructure](#testing-infrastructure)
- [Running Tests](#running-tests)
- [Writing Tests](#writing-tests)
- [Test Coverage](#test-coverage)
- [Mocking External Dependencies](#mocking-external-dependencies)
- [Continuous Integration](#continuous-integration)
- [Performance Testing](#performance-testing)
- [Troubleshooting Common Test Issues](#troubleshooting-common-test-issues)

## Testing Philosophy

The TrailBlazeApp-API follows a comprehensive testing approach to ensure reliability and maintainability:

1. **Unit Tests**: Test individual components in isolation
2. **Integration Tests**: Test interactions between components
3. **API Tests**: Test the API endpoints from an external perspective
4. **Performance Tests**: Ensure the API meets performance requirements

We aim for high test coverage while focusing on testing business-critical paths thoroughly.

## Testing Infrastructure

### Tools and Libraries

- **pytest**: Main testing framework
- **pytest-asyncio**: For testing asynchronous code
- **httpx**: For testing HTTP endpoints
- **pytest-cov**: For measuring test coverage
- **unittest.mock**: For mocking dependencies

### Test Directory Structure

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── pytest.ini              # Pytest configuration
├── unit/                   # Unit tests
├── api/                    # API integration tests
│   └── v1/                # Tests for API v1 endpoints
└── scrapers/              # Tests for data scrapers
    └── aerc_scraper/      # AERC scraper specific tests
        ├── conftest.py    # Scraper test fixtures
        ├── fixtures/      # Test data files
        ├── test_*.py     # Test modules
```

## Running Tests

### Running All Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=app --cov-report=term --cov-report=html
```

### Running Specific Test Categories

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run scraper tests with coverage
./tests/run_scraper_tests.sh

# Run scraper integration tests
./tests/run_scraper_tests.sh --integration
```

### Test Markers

Available pytest markers:
- `asyncio`: Mark a test as an async test
- `integration`: Mark a test as an integration test
- `unit`: Mark a test as a unit test

## Writing Tests

### Unit Test Example

```python
@pytest.mark.unit
async def test_create_event(db_session):
    event_data = EventCreate(
        name="Test Event",
        date_start=datetime.now(),
        location="Test Location"
    )
    event = await events.create_event(db_session, event_data)
    assert event.name == "Test Event"
```

### Integration Test Example

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_scraper_workflow(scraper, mock_db, test_html):
    with patch('scrapers.aerc_scraper.network.NetworkHandler.make_request') as mock_request:
        mock_request.return_value = test_html
        result = await scraper.run(mock_db)
        assert result['status'] == 'success'
```

### Test Fixtures

Common test fixtures are in `tests/conftest.py`. Specialized fixtures for scrapers are in `tests/scrapers/aerc_scraper/conftest.py`.

Key fixtures include:
- `db_session`: Provides test database session
- `async_client`: Configured test client
- `mock_db`: Mock database for scraper tests
- `test_html`: Sample HTML for scraper tests
- `sample_events`: Sample event data

## Test Coverage

Our coverage requirements:
- Minimum 80% overall coverage
- 90%+ for critical components (auth, data validation, scrapers)
- 100% for business logic and data models

Coverage is checked during CI/CD and tracked in the `/coverage` directory.

## Mocking External Dependencies

We use pytest's monkeypatch and unittest.mock for mocking:

```python
@pytest.fixture
def scraper(settings, mock_session):
    """Create scraper with mocked components."""
    with patch('scrapers.aerc_scraper.main.NetworkHandler') as mock_network:
        mock_network.return_value.fetch_calendar = AsyncMock()
        yield scraper
```

## Continuous Integration

Tests run automatically on:
- Pull requests
- Pushes to main branch
- Daily scheduled runs

Failed tests block merging until fixed.

## Performance Testing

Performance tests use locust:

```python
from locust import HttpUser, task, between

class ApiUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def get_events(self):
        self.client.get("/v1/events")
```

Run with:
```bash
locust -f performance/locustfile.py
```

## Troubleshooting Common Test Issues

### Database Connection Issues
- Check PostgreSQL is running
- Verify test database URL
- Run migrations

### Async Test Failures
- Use @pytest.mark.asyncio
- Await async functions
- Check fixture definitions

### Cache-Related Issues
- Clear test cache: `rm -rf tests/temp_cache/*`
- Set SCRAPER_REFRESH=true
- Check cache TTL settings
