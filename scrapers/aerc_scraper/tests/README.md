# AERC Scraper Tests

This directory contains tests for the AERC scraper component. The tests are structured to validate the entire pipeline:

1. Parsing HTML from AERC ride listings
2. Extracting structured data
3. Transforming the data into database-compatible models
4. Storing the data in the database

## Test Organization

The tests are organized into several categories:

### HTML Parsing Tests
- `test_html_parser.py`: Unit tests for the HTML parser
- `test_parser_with_samples.py`: Tests with real HTML samples
- `test_special_cases.py`: Tests for edge cases and special parsing scenarios

### Data Transformation Tests
- `test_data_handler.py`: Tests for data transformation
- `test_distance_handling.py`: Tests for handling distance data

### Database Integration Tests
- `test_html_to_database_integration.py`: Comprehensive HTML-to-database pipeline test

### Utility Scripts
- `debug_parser.py`: Helper for debugging parsing issues
- `debug_date_parsing.py`: Helper for debugging date parsing
- `run_html_to_database_test.py`: Runner for the comprehensive database test

## HTML Samples

The `html_samples/` directory contains real HTML files for testing:

- `old_pueblo_event.html`: Standard endurance event
- `biltmore_cancelled_event.html`: Cancelled event
- `tevis_cup_event.html`: Famous 100-mile event
- `belair_forest_event.html`: Canadian event with coordinates
- `cuyama_pioneer_event.html`: Multi-day pioneer ride

## Expected Test Data

The `expected_test_data.py` file contains the reference data for validating parsing results.

## Running Tests

### Using Make Commands

```bash
# Run all AERC scraper tests
make test-aerc-scraper

# Run HTML parser tests only
make test-aerc-parser

# Run database integration tests
make test-aerc-database

# Run a specific test file
make test-aerc-specific TEST_FILE=test_parser_with_samples.py
```

### Running Tests Directly

```bash
# From project root
python -m scrapers.aerc_scraper.tests.run_html_to_database_test

# Run with debug output
python -m scrapers.aerc_scraper.tests.run_html_to_database_test --debug
```

## Database Integration Test

The `test_html_to_database_integration.py` file contains our comprehensive pipeline test that:

1. Parses HTML from sample files
2. Transforms the data into structured formats
3. Converts to database models
4. Simulates database insertion
5. Validates that the inserted data matches expected values

This single test replaces multiple previous database-related tests by testing the entire pipeline at once. 