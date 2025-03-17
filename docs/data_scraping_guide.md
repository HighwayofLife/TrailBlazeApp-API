# Data Scraping Guide

## Running Scrapers

### Quick Start

```bash
# Run AERC calendar scraper
make scraper-aerc_calendar

# Run scraper tests
make test-scraper
```

### Environment Variables

```bash
# Required
GEMINI_API_KEY=your_api_key

# Optional
SCRAPER_DEBUG=true      # Enable debug logging
SCRAPER_REFRESH=true    # Force cache refresh
SCRAPER_VALIDATE=true   # Enable validation
```

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

1. **Scraper Manager**: Coordinates execution
2. **Base Scraper**: Common interface
3. **Individual Scrapers**: Source implementations

## AERC Calendar Scraper

### Features

- HTML chunking for large responses
- AI-powered data extraction (Gemini)
- Error handling and recovery
- Metrics collection

### Running the Scraper

```bash
# Run with default settings
make scraper-aerc_calendar

# Run with options (set in .env)
SCRAPER_DEBUG=true make scraper-aerc_calendar
```

### Monitoring

```bash
# View scraper logs
make logs-scraper

# Check scraper health
make health
```

## Adding New Scrapers

1. Create scraper module:
```
scrapers/new_scraper/
├── __init__.py
├── scraper.py
└── config.py
```

2. Implement BaseScraper:
```python
class NewScraper(BaseScraper):
    async def run(self):
        # Implementation
```

3. Add tests:
```bash
# Create tests
touch tests/scrapers/new_scraper/test_scraper.py

# Run tests
make test-scraper
```

4. Run scraper:
```bash
make scraper-new_scraper
```

## Maintenance

### Common Tasks

```bash
# Check scraper logs
make logs-scraper

# Run scraper tests
make test-scraper

# Validate scraper output
SCRAPER_VALIDATE=true make scraper-aerc_calendar

# Clear cache and rerun
SCRAPER_REFRESH=true make scraper-aerc_calendar
```

### Troubleshooting

1. Check logs:
```bash
make logs-scraper
```

2. Run with debug:
```bash
SCRAPER_DEBUG=true make scraper-aerc_calendar
```

3. Validate data:
```bash
SCRAPER_VALIDATE=true make scraper-aerc_calendar
```

## Database Queries

### Checking Event Counts

```bash
# Open database shell
make db-shell

# Once in the PostgreSQL shell, you can run queries:
# Count all AERC events
SELECT COUNT(*) FROM events WHERE source = 'AERC';

# Count events by status
SELECT is_canceled, COUNT(*) 
FROM events 
WHERE source = 'AERC' 
GROUP BY is_canceled;

# Count events by date range
SELECT COUNT(*) 
FROM events 
WHERE source = 'AERC' 
AND date_start >= '2024-01-01' 
AND date_start < '2025-01-01';

# View recent events
SELECT name, date_start, location, is_canceled 
FROM events 
WHERE source = 'AERC' 
ORDER BY date_start DESC 
LIMIT 5;
```

### Common Queries

```sql
-- Find duplicate events
SELECT name, date_start, COUNT(*) 
FROM events 
WHERE source = 'AERC' 
GROUP BY name, date_start 
HAVING COUNT(*) > 1;

-- Check for missing required fields
SELECT name, date_start, location 
FROM events 
WHERE source = 'AERC' 
AND (name IS NULL OR date_start IS NULL OR location IS NULL);

-- View events with specific criteria
SELECT name, date_start, location, is_canceled 
FROM events 
WHERE source = 'AERC' 
AND name ILIKE '%cancelled%';
```

### Troubleshooting Tips

1. Always verify event counts directly in the database
2. Check for duplicate entries if numbers don't match
3. Look for missing required fields
4. Verify date ranges and event statuses
5. Use the database shell for direct inspection
