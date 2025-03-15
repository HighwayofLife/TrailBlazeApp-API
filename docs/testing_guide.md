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
├── unit/                    # Unit tests
│   ├── crud/                # Tests for CRUD operations
│   ├── models/              # Tests for database models
│   └── services/            # Tests for business logic services
├── api/                     # API integration tests
│   └── v1/                  # Tests for API v1 endpoints
├── scrapers/                # Tests for data scrapers
└── performance/             # Performance tests
```

## Running Tests

### Running All Tests

```bash
pytest
```

### Running Specific Test Categories

```bash
# Run only unit tests
pytest tests/unit/

# Run only API tests
pytest tests/api/

# Run tests with specific marks
pytest -m "not slow"
```

### Test Coverage Report

```bash
pytest --cov=app --cov-report=term --cov-report=html
```

After running this command, open `htmlcov/index.html` in your browser to view the detailed coverage report.

## Writing Tests

### Unit Test Example

Here's an example of a unit test for a CRUD function:

```python
# tests/unit/crud/test_events.py
import pytest
from datetime import datetime
from app.crud import events
from app.schemas.event import EventCreate

async def test_create_event(db_session):
    # Arrange
    event_data = EventCreate(
        name="Test Event",
        description="Test Description",
        location="Test Location",
        coordinates={"lat": 45.123, "lng": -122.456},
        date_start=datetime(2023, 7, 15, 8, 0, 0),
        date_end=datetime(2023, 7, 16, 18, 0, 0),
        organizer="Test Organizer",
        region="Northwest",
        distances=["25", "50"]
    )
    
    # Act
    event = await events.create_event(db_session, event_data)
    
    # Assert
    assert event.name == "Test Event"
    assert event.organizer == "Test Organizer"
    assert len(event.distances) == 2
```

### API Test Example

Here's an example of an API test:

```python
# tests/api/v1/test_events_api.py
import pytest
from httpx import AsyncClient
from app.main import app

async def test_get_events(async_client: AsyncClient, test_events):
    # Act
    response = await async_client.get("/v1/events")
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert "name" in data[0]
    assert "location" in data[0]
```

### Test Fixtures

Common test fixtures are defined in `tests/conftest.py`:

```python
# Example fixtures
@pytest.fixture
async def db_session():
    # Set up a test database session
    ...
    yield session
    # Teardown code here

@pytest.fixture
async def async_client():
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
async def test_events(db_session):
    # Create test events in the database
    ...
    return events
```

## Test Coverage

Our goal is to maintain at least 80% test coverage for the codebase. Critical components like authentication, data validation, and business logic should aim for near 100% coverage.

Coverage is checked as part of the CI process, and pull requests that decrease coverage significantly may be rejected.

## Mocking External Dependencies

For tests, we mock external dependencies like the Gemini API and database:

```python
# Example of mocking the Gemini API
from unittest.mock import patch

@patch("app.services.ai_service.gemini_client")
async def test_ask_question(mock_gemini_client):
    # Configure the mock
    mock_gemini_client.generate_content.return_value.text = "Test answer"
    
    # Call the function
    result = await ask_question("Test question", "context")
    
    # Assert
    assert result == "Test answer"
    mock_gemini_client.generate_content.assert_called_once()
```

## Continuous Integration

Tests are automatically run on every pull request and push to the main branch using GitHub Actions. The workflow includes:

1. Setting up the test environment
2. Running tests
3. Measuring coverage
4. Reporting results

If tests fail, the pull request cannot be merged until the issues are fixed.

## Performance Testing

We use locust for performance testing:

1. **Install locust:**

```bash
pip install locust
```

2. **Create a locustfile.py:**

```python
from locust import HttpUser, task, between

class ApiUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def get_events(self):
        self.client.get("/v1/events")
        
    @task
    def ask_question(self):
        self.client.post("/v1/assistant/ask", 
                        json={"question": "When is the next ride?"})
```

3. **Run performance tests:**

```bash
locust -f performance/locustfile.py
```

4. **View results:**

Open http://localhost:8089 in your browser to see the locust UI.

## Troubleshooting Common Test Issues

### Database Connection Issues

If tests fail due to database connection issues:

1. Check that PostgreSQL is running
2. Verify the test database URL in `conftest.py`
3. Ensure migrations are up to date

### Async Test Failures

For async test failures:

1. Make sure you're using the `pytest.mark.asyncio` decorator
2. Check that your fixtures are properly defined as async
3. Verify that you're awaiting async functions

### Slow Tests

If tests are running too slowly:

1. Mark slow tests with `@pytest.mark.slow`
2. Run only fast tests during development: `pytest -m "not slow"`
3. Consider using more focused fixtures that set up only what's needed
