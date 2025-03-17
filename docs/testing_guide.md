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

### Quick Start

```bash
# Run all tests
make test

# Run specific test suites
make test-unit        # Unit tests only
make test-api         # API tests only
make test-integration # Integration tests
make test-scraper    # Scraper tests

# Run tests with coverage
make test            # Includes coverage report
```

### Test Categories

| Command | Description |
|---------|-------------|
| `make test` | Run all tests with coverage |
| `make test-unit` | Run unit tests |
| `make test-api` | Run API endpoint tests |
| `make test-integration` | Run integration tests |
| `make test-scraper` | Run scraper tests |
| `make ci-test` | Run tests for CI environment |

### Test Environment

Tests run in a containerized environment to ensure consistency. The test containers include:
- PostgreSQL test database
- Redis for caching
- Mock external services

## Writing Tests

### Directory Structure

```
tests/
├── conftest.py        # Shared fixtures
├── unit/             # Unit tests
├── api/              # API tests
└── scrapers/         # Scraper tests
```

### Test Examples

1. Unit Test:
```python
@pytest.mark.unit
async def test_create_event(db_session):
    event = await create_event(db_session, test_data)
    assert event.name == test_data["name"]
```

2. API Test:
```python
@pytest.mark.api
async def test_get_events(client):
    response = await client.get("/v1/events")
    assert response.status_code == 200
```

## Test Coverage

Coverage reports are generated automatically with `make test`. View the report in:
- Terminal output
- `coverage/` directory (HTML report)

## Continuous Integration

Tests run automatically on:
- Pull requests
- Pushes to main branch
- Daily scheduled runs

Use `make ci-test` to run tests as they would run in CI.

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
