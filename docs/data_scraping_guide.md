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
