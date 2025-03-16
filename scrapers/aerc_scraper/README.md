# AERC Calendar Scraper

A modular scraper for extracting endurance ride events from the AERC calendar.

## Architecture

The scraper follows a modular architecture with clear separation of concerns:

```
aerc_scraper/
├── __init__.py          # Package exports
├── scraper.py           # Main scraper class
├── network.py           # Network request handling
├── html_cleaner.py      # HTML cleaning and preprocessing
├── gemini_client.py     # Gemini API integration
├── validator.py         # Data validation
├── converter.py         # Data conversion to DB schema
├── database.py          # Database operations
├── cache.py            # Caching with TTL support
├── metrics.py          # Metrics collection
├── config.py           # Configuration settings
└── exceptions.py       # Custom exceptions

tests/
└── scrapers/
    └── aerc_scraper/
        ├── conftest.py          # Test configuration
        ├── test_*.py           # Test modules
        └── fixtures/           # Test fixtures
```

## Features

- Modular architecture with clear separation of concerns
- Robust error handling and recovery
- Caching with TTL support
- Comprehensive metrics collection
- AI-powered data extraction using Google's Gemini
- Efficient HTML processing with lxml
- Validation using Pydantic models
- Comprehensive test coverage

## Usage

```python
from scrapers.aerc_scraper import AERCScraper, run_aerc_scraper

# Using the async function
result = await run_aerc_scraper(db_session)

# Or using the class directly
scraper = AERCScraper()
result = await scraper.run(db_session)
```

## Configuration

Configure the scraper using environment variables:

```env
AERC_GEMINI_API_KEY=your_api_key
AERC_DEBUG_MODE=true
AERC_REFRESH_CACHE=false
AERC_CACHE_TTL=3600
```

Or using the settings class:

```python
from scrapers.aerc_scraper import ScraperSettings

settings = ScraperSettings(
    gemini_api_key="your_api_key",
    debug_mode=True,
    refresh_cache=False,
    cache_ttl=3600
)
scraper = AERCScraper(settings=settings)
```

## Testing

Run the test suite:

```bash
# Run all tests with coverage
./tests/run_scraper_tests.sh

# Run specific test categories
./tests/run_scraper_tests.sh -m unit
./tests/run_scraper_tests.sh -m integration
```

## Metrics

The scraper collects comprehensive metrics during operation:

- Network metrics (requests, retries, errors)
- HTML processing metrics (rows found, cleaning time)
- Data extraction metrics (API calls, success rate)
- Validation metrics (events found, valid, errors)
- Cache metrics (hits, misses, expired)
- Performance metrics (memory usage, duration)

Access metrics through component interfaces:

```python
# Component-specific metrics
network_metrics = scraper.network.get_metrics()
cache_metrics = scraper.cache.get_metrics()

# Or get combined metrics from the run result
result = await scraper.run(db_session)
print(result['success_rate'])
```

Historical metrics are saved to JSON files in the `logs/metrics` directory.

## Error Handling

The scraper implements comprehensive error handling:

- Network errors with automatic retry
- Rate limiting compliance
- Data validation errors
- Cache errors
- Database errors
- API errors with fallback options

## Dependencies

See `requirements.txt` for the complete list of dependencies.

## Contributing

1. Ensure all tests pass before submitting changes
2. Add tests for new functionality
3. Follow the existing modular architecture
4. Update documentation as needed

## License

MIT License