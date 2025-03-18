# Changelog

## [Unreleased]

### Schema Refactoring - Core Changes

- **Centralized Event Schemas**: Consolidated all event-related schemas into `app/schemas/event.py` to establish a single source of truth.
- **Introduced Inheritance**: Implemented inheritance for source-specific schemas (AERC, SERA, UMECRA) to promote extensibility and reduce redundancy.
- **Modernized Pydantic Usage**: Updated schema definitions to utilize `ConfigDict` for configuration and `field_validator` for custom validation.
- **Enhanced Documentation**: Added comprehensive documentation, including field descriptions and examples, to improve schema clarity.

### Scraper Schema Updates

- **Removed Duplication**: Eliminated redundant schema definitions in scraper modules by referencing centralized schemas.
- **Implemented Conversion Functions**: Created conversion functions in scraper modules to map scraper-specific data to the core event schema.
- **Updated Imports**: Modified scraper modules to import schemas from `app/schemas` instead of defining their own.

### General Schema Improvements

- **Improved Organization**: Organized schemas into logical groupings (core, components, source-specific) for better maintainability.
- **Added Utility Functions**: Created source-specific validation functions and data conversion helpers.
- **Ensured Backward Compatibility**: Maintained compatibility with existing code by carefully managing schema changes and providing conversion utilities.

### app/schemas/\_\_init\_\_.py

- **Updated Imports and Exports**: Modified `__init__.py` to import and expose all schema components, simplifying imports throughout the application.

### app/schemas/README.md

- **Created Documentation**: Added a `README.md` file to the `app/schemas` directory to document the schema architecture, design principles, and usage examples.

### Testing Improvements

- **Consolidated Tests**: Added new comprehensive test in `test_parser_with_samples.py` that combines HTML parsing with schema validation.
- **Test Runner Prioritization**: Updated `run_tests.py` to prioritize the new consolidated test for faster feedback during development.
- **Fixed Database Integration Tests**: Updated database integration tests to properly handle the new structured data formats.
- **Improved Test Robustness**: Enhanced location checking in tests to handle variations in location formatting and address structures.
- **Added Structure Validation**: Implemented tests to verify that event details are correctly preserved through the entire pipeline.

### Database Schema Updates

- **Added ride_id Field**: Added a new `ride_id` column to the events table to store external source system identifiers.
- **Added has_intro_ride Flag**: Added a new boolean field to indicate events with introductory rides.
- **Improved Field Documentation**: Enhanced column comments to describe expected formats for structured data.

### Bug Fixes

- **Fixed Linter Errors**: Corrected linter errors in `app/schemas/event.py` by adding `self` to validator methods.
- **Fixed Test Assertions**: Updated test assertions to safely handle different types of event_details objects.

### HTML Parser Improvements

- **Enhanced Canadian Location Detection**: Updated the `_parse_location` method in the HTML parser to accurately identify Canadian provinces and set the country to 'Canada' when applicable.
- **Improved Event Data Extraction**: Refined the extraction logic to handle various location formats and ensure accurate parsing of event details.
- **Consolidated Event Merging Logic**: Improved the `_combine_events_with_same_ride_id` method to handle multi-day events more effectively, ensuring all relevant data is preserved.

### Testing

- **Verified Imports**: Confirmed that all schema imports work as expected by running tests.

### AERC Scraper Improvements

- **Implemented Multi-Day Event Support**: Enhanced the AERC scraper to correctly identify and process multi-day events, including pioneer rides.
    - Fixed date parsing in the `_merge_events` method to handle string dates correctly by converting them to datetime objects before subtraction.
    - Ensured correct setting of `is_multi_day_event`, `is_pioneer_ride`, and `ride_days` flags during event merging.
- **Improved Test Coverage**:
    - Added a new test method `test_multi_day_event_detection` to verify the detection of multi-day events and pioneer rides.
    - Updated the `test_full_parsing_flow` method to validate the correct setting of new fields (`is_multi_day_event`, `is_pioneer_ride`, and `ride_days`).
- **Fixed Schema Validation**:
    - Updated schema tests to correctly validate the `location` field as a string.
    - Explicitly set `is_multi_day_event`, `is_pioneer_ride`, and `ride_days` flags in tests to ensure correct validation.

### Migration to Pytest

- **Migrated Test Framework**: Converted all tests in the `scrapers/aerc_scraper/tests` directory from `unittest` to `pytest` for improved test management and reporting.
- **Updated Test Runner**: Refactored `run_tests.py` to utilize pytest's test discovery and execution capabilities, allowing for more flexible test runs.
- **Consolidated Fixtures**: Created a `conftest.py` file to define common fixtures used across multiple test files, promoting code reuse and reducing redundancy.
- **Enhanced Test Output**: Improved the output of test runs to provide clearer information about which tests are being executed and their results.

### Bug Fixes and Improvements

- **Fixed Linter Errors**: Addressed linter errors related to missing imports for pytest and SQLAlchemy in the test files.
- **Improved Test Robustness**: Enhanced existing tests to handle variations in data formats and ensure compatibility with the latest schema changes.
- **Updated Test Assertions**: Modified assertions in tests to align with the new data structures and validation logic introduced in the recent schema refactoring.

### General Improvements

- **Enhanced Documentation**: Updated documentation for tests to reflect the new pytest structure and usage.
