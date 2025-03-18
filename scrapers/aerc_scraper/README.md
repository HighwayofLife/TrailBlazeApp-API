# AERC Calendar Scraper

A modular scraper for extracting endurance ride events from the AERC calendar. This scraper uses direct HTML parsing for data extraction.

## Architecture

The scraper follows a modular architecture with clear separation of concerns:

```
aerc_scraper/
├── __init__.py          # Package exports
├── parser_v2/           # Active HTML Parser implementation
│   ├── __init__.py
│   ├── html_parser.py   # HTML parsing logic
│   └── main_v2.py       # Main implementation (AERCScraperV2)
├── network.py           # Network request handling
├── html_cleaner.py      # HTML cleaning and preprocessing
├── database.py          # Database operations
├── cache.py             # Caching with TTL support
├── metrics.py           # Metrics collection
├── config.py            # Configuration settings
└── exceptions.py        # Custom exceptions

tests/
└── scrapers/
    └── aerc_scraper/
        ├── conftest.py          # Test configuration
        ├── test_*.py            # Test modules
        └── fixtures/            # Test fixtures
```

## Features

- Modular architecture with clear separation of concerns
- Robust error handling and recovery
- Caching with TTL support
- Comprehensive metrics collection
- Efficient HTML processing with lxml
- Validation using Pydantic models
- Comprehensive test coverage

## Usage

```python
from scrapers.aerc_scraper import AERCScraperV2

# Using the class directly
scraper = AERCScraperV2(settings, db_session)
result = await scraper.scrape()
```

## Configuration

Configure the scraper using environment variables:

```env
SCRAPER_DEBUG=true
SCRAPER_REFRESH=false
```

Or using the settings class:

```python
from scrapers.aerc_scraper import ScraperSettings

settings = ScraperSettings(
    debug_mode=True,
    refresh_cache=False,
    cache_ttl=3600
)
scraper = AERCScraperV2(settings, db_session)
```

## Running the Scraper

Use the dedicated runner script:

```bash
# Using Make
make scraper-aerc-v2

# Or directly
python -m scrapers.run_aerc_v2
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
result = await scraper.scrape()
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