# TrailBlaze Data Scrapers

This directory contains the data scrapers used to collect event information from various sources.

## Available Scrapers

- **AERC Calendar Scraper**: Scraper using direct HTML parsing to extract event information.

## Running Scrapers

Scrapers can be run individually or all at once using the `run_scrapers.py` script:

```bash
# Run all scrapers
python -m scrapers.run_scrapers

# Run a specific scraper
python -m scrapers.run_scrapers aerc
```

For the improved AERC scraper (v2) specifically:

```bash
# Using the dedicated runner
python -m scrapers.run_aerc_v2

# Using Make
make scraper-aerc-v2
```

## AERC Calendar Scraper

The AERC Calendar Scraper extracts data directly from the AERC calendar website's HTML.

### Current Implementation

The current implementation uses direct HTML parsing via the `parser_v2` module and can be found in `scrapers/aerc_scraper/parser_v2/`. This implementation is more reliable, maintainable, and efficient than the previous version.

## Adding New Scrapers

To add a new scraper:

1. Create a new module in the `scrapers` directory
2. Implement the scraper interface
3. Add the scraper to the `run_scraper` function in `app/services/scraper_service.py`
4. Add the scraper ID to the `scraper_ids` list in `scrapers/run_scrapers.py`
