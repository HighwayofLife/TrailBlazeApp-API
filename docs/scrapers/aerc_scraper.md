# AERC Scraper

## Status

**In Progress**

The AERC scraper is currently under development. It extracts ride calendar data from the AERC website and stores it in a structured format.

## Current Features

*   Fetches HTML from the AERC calendar page.
*   Cleans and preprocesses the HTML.
*   Splits the HTML into manageable chunks.
*   Extracts event data from HTML using a direct HTML parser (BeautifulSoup).
*   Optionally uses Gemini API as a fallback.
*   Transforms and validates extracted data against Pydantic models.
*   Stores validated events in the database.
*   Handles updates to existing events.
*   Skips canceled events.
*   Provides detailed logging and metrics.
*   Supports chunk-by-chunk processing.
*   Extracts location data (city, state, country, Canadian provinces).
*   Extracts and validates URLs (website, flyer, Google Maps).
*   Extracts coordinates from Google Maps links.
*   Extracts ride manager contact information.
*   Extracts distances and start times.
*   Detects intro rides.
*   Detects canceled events.
*   Extracts control judge information.

## Testing

The scraper has unit and integration tests.

### Unit Tests

*   `scrapers/aerc_scraper/tests/test_html_parser.py`: Tests HTML parsing.
*   `scrapers/aerc_scraper/tests/test_special_cases.py`: Tests specific scenarios.
*  `scrapers/aerc_scraper/tests/test_distance_extraction.py`: Tests distance extraction.

### Integration Tests
*   `scrapers/aerc_scraper/tests/test_integration_parser_database.py`: Verifies HTML parsing to database storage.

### Running Tests

*   `make test`: Run all unit tests.
*   `make test-all`: Run all tests.
*   `make test-scrapers`: Run all scraper tests.
*   `make test-aerc-scraper`: Run AERC scraper tests.

## Geocoding

Geocoding (determining latitude and longitude from the event location) is performed **selectively**.  The scraper will:

1.  **Query the database:**  Check for existing events that *do not* have latitude/longitude coordinates.
2.  **Attempt Geocoding:** For events missing coordinates, attempt to determine them based on the `location` field (which contains the location string).
3.  **Store Results:** If geocoding is successful, store the latitude and longitude.
4.  **`geocoding_attempted` Flag:**  A boolean field, `geocoding_attempted`, is added to the database schema. This field indicates whether an attempt was made to geocode the location.
    *   `geocoding_attempted = True` and coordinates are present: Geocoding was successful.
    *   `geocoding_attempted = True` and coordinates are *not* present: Geocoding was attempted but failed.  This allows the application to display an "Approximate Location" message, indicating that the location might need manual verification (e.g., by checking the event flyer or website).
    *   `geocoding_attempted = False`:  No geocoding attempt has been made yet (e.g., for newly added events).

This approach avoids unnecessary geocoding requests for events that already have coordinates and provides a way to track the status of geocoding attempts.

## Next Steps

*   Validate inserted data into the database matches the expected data structure.
* Implement selective geocoding as described above. 