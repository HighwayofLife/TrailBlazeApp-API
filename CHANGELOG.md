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

### Bug Fixes

- **Fixed Linter Errors**: Corrected linter errors in `app/schemas/event.py` by adding `self` to validator methods.

### Testing

- **Verified Imports**: Confirmed that all schema imports work as expected by running tests.
