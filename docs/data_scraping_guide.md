# Data Scraping Guide

## Overview

The TrailBlazeApp-API uses a modular scraping system to collect endurance riding event data from various sources. The system is designed for reliability, maintainability, and extensibility.

## Architecture

### Component Overview

```
scrapers/
├── __init__.py           # Package exports
├── base_scraper.py      # Abstract base class
├── config.py            # Shared configuration
├── exceptions.py        # Custom exceptions
├── scheduler.py         # Scheduling system
├── run_scrapers.py      # CLI entry point
└── aerc_scraper/        # AERC Calendar scraper
    ├── __init__.py     # Package exports
    ├── scraper.py      # Main scraper class
    ├── config.py       # AERC-specific settings
    ├── network.py      # Network handling
    ├── html_cleaner.py # HTML preprocessing
    ├── chunking.py     # Content chunking
    ├── gemini_client.py # Gemini API client
    ├── validator.py    # Data validation
    ├── converter.py    # Schema conversion
    ├── database.py     # Database operations
    ├── cache.py        # Caching system
    └── metrics.py      # Metrics collection
```

### Key Components

1. **Scraper Manager**: Coordinates scraper execution
2. **Base Scraper**: Abstract class defining common interface
3. **Configuration**: Environment-based settings
4. **Scheduler**: Async job scheduling
5. **Individual Scrapers**: Source-specific implementations

## AERC Calendar Scraper

### Features

- Modular architecture with clear separation of concerns
- Intelligent HTML chunking for large responses
- AI-powered data extraction using Google's Gemini API
- Robust error handling and recovery
- Comprehensive metrics collection
- Caching with TTL and validation
- Rate limiting and polite scraping

### Configuration

```env
# Required settings
AERC_GEMINI_API_KEY=your_api_key
AERC_DATABASE_URL=postgresql://user:pass@host/db

# Optional settings
AERC_DEBUG_MODE=true           # Enable debug logging
AERC_REFRESH_CACHE=false       # Force cache refresh
AERC_CACHE_TTL=3600           # Cache TTL in seconds
AERC_REQUESTS_PER_SECOND=1.0   # Rate limiting
```

### Execution Flow

1. Extract season IDs from calendar page
2. Fetch calendar HTML using season IDs
3. Clean and preprocess HTML
4. Split HTML into manageable chunks
5. Extract structured data using Gemini API
6. Validate extracted data
7. Convert to database schema
8. Store in database with deduplication

### Error Handling

- Network errors: Automatic retry with backoff
- API failures: Fallback to secondary model
- Validation errors: Detailed error reporting
- Cache issues: Automatic invalidation
- Database errors: Transaction rollback

### Cache Management

The scraper implements a sophisticated caching system:

1. **Cache Levels**:
   - Raw HTML responses
   - Structured JSON data
   - Processed event data

2. **Cache Validation**:
   - TTL-based expiration
   - Data consistency checks
   - Row count validation

3. **Force Refresh Conditions**:
   - Manual trigger (SCRAPER_REFRESH=true)
   - Validation failure 
   - Schedule changes
   - Data format changes

### Metrics Collection

Comprehensive metrics are collected from all components:

- Network: requests, retries, errors
- HTML: rows found, cleaning time
- API: calls, success rate, latency
- Validation: events found/valid/invalid
- Cache: hits, misses, invalidations
- Database: inserts, updates, conflicts
- Performance: memory usage, duration

## Adding New Scrapers

1. Create new module:
```
scrapers/
└── new_scraper/
    ├── __init__.py
    ├── scraper.py
    ├── config.py
    └── ...
```

2. Implement BaseScraper interface:
```python
class NewScraper(BaseScraper):
    async def run(self, db: AsyncSession) -> Dict[str, Any]:
        # Implementation
        pass
```

3. Register in ScraperManager:
```python
SCRAPERS = {
    "aerc_calendar": AERCScraper,
    "new_source": NewScraper
}
```

4. Add configuration:
```python
class NewScraperSettings(ScraperBaseSettings):
    base_url: str
    update_frequency: int
    # etc.
```

5. Create tests:
```
tests/scrapers/new_scraper/
├── conftest.py
├── test_scraper.py
└── fixtures/
```

## Running Scrapers

### Manual Execution

```bash
# Run all scrapers
python -m scrapers.run_scrapers

# Run specific scraper
python -m scrapers.run_scrapers aerc_calendar

# Run with options
python -m scrapers.run_scrapers aerc_calendar \
    --refresh-cache \
    --debug \
    --validate
```

### Scheduled Execution

The ScraperScheduler handles automated runs:

```python
scheduler = ScraperScheduler()

# Daily at midnight
scheduler.schedule_scraper(
    scraper_func=run_aerc_scraper,
    name="aerc_daily",
    cron="0 0 * * *"
)

# Weekly on Monday
scheduler.schedule_scraper(
    scraper_func=run_pner_scraper,
    name="pner_weekly",
    cron="0 0 * * 1"
)
```

## Maintenance

### Daily Tasks
- Monitor scraper logs
- Check event counts
- Verify data quality

### Weekly Tasks
- Review error patterns
- Check source websites
- Update cached data

### Monthly Tasks
- Analyze performance metrics
- Review/adjust schedules
- Update documentation

## Troubleshooting

### Common Issues

1. **Scraper Failures**:
   - Check source website accessibility
   - Verify HTML structure hasn't changed
   - Review error logs
   - Clear cache and retry

2. **API Issues**:
   - Verify API key validity
   - Check rate limits
   - Review model configuration

3. **Cache Issues**:
   - Clear specific cache: `rm cache/aerc_*.json`
   - Force refresh: `SCRAPER_REFRESH=true`
   - Check cache validation logs

4. **Database Issues**:
   - Check connection
   - Verify schema compatibility
   - Review transaction logs
