# TrailBlaze Data Scrapers

This directory contains the data scrapers used to collect event information from various sources for the TrailBlaze API.

## Available Scrapers

- **AERC Calendar Scraper**: Extracts endurance ride events from the AERC calendar using direct HTML parsing

## Architecture

Scrapers follow a modular architecture with clear separation of concerns:

```
scrapers/
├── aerc_scraper/           # AERC Calendar Scraper
│   ├── parser_v2/          # HTML parsing implementation
│   ├── database.py         # Database operations
│   ├── data_handler.py     # Data transformation
│   ├── network.py          # Network requests
│   ├── cache.py            # Caching with TTL
│   └── tests/              # Tests directory
└── run_scrapers.py         # Main runner for all scrapers
```

## Running Scrapers

Scrapers can be run individually or all at once:

```bash
# Run all scrapers
make scraper-all

# Run AERC scraper specifically
make scraper-aerc-v2
```

## Testing

Tests follow a structured approach to validate the entire pipeline from HTML parsing to database storage.

### Test Structure

```
tests/
├── test_html_parser.py          # Tests HTML parsing functionality
├── test_parser_with_samples.py  # Tests parser with real HTML samples
├── test_data_handler.py         # Tests data transformation
├── test_database_integration.py # Tests HTML to database integration
└── html_samples/                # Sample HTML files for testing
```

### Running Tests

Use the Makefile commands for running tests:

```bash
# Run all AERC scraper tests
make test-aerc-scraper

# Run specific AERC test file
make test-aerc-specific TEST_FILE=test_parser_with_samples.py

# Run the comprehensive HTML to database pipeline test
make test-aerc-html-db-pipeline
```

### Key Test Files

- **HTML Parser Tests**: Validate extraction of structured data from HTML
- **Data Handler Tests**: Validate transformation to database models
- **Database Integration Tests**: Validate the full pipeline from HTML to database

### HTML to Database Pipeline Test

The most comprehensive test is the HTML-to-database pipeline test, which validates:

1. Parsing HTML from sample files
2. Transforming raw data to structured data
3. Converting to database models
4. Database insertion
5. Verification against expected data

## Configuration

Configure scrapers using environment variables or settings objects:

```bash
# Environment variables
SCRAPER_DEBUG=true         # Enable debug mode
SCRAPER_REFRESH=false      # Refresh cache
AERC_VALIDATE=true         # Enable validation
```

## Adding New Scrapers

To add a new scraper:

1. Create a new directory in `scrapers/`
2. Implement the scraper using the modular architecture
3. Add tests in a `tests/` subdirectory
4. Update the `run_scrapers.py` script to include the new scraper
5. Add Makefile commands for running and testing the scraper

## Documentation

Each scraper should include documentation on:

- Architecture and components
- Configuration options
- Testing strategy
- Expected data format
- Database integration details
