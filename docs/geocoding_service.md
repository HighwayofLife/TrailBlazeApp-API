# Geocoding Service

## Overview
This document outlines the design and implementation of the geocoding service for TrailBlazeApp-API. The service will add GPS coordinates (latitude and longitude) to event records in the database.

## Requirements
1. Add latitude and longitude fields to the events table
2. Implement a geocoding service using an appropriate library
3. Update existing events with GPS coordinates
4. Ensure new events are automatically geocoded when added

## Design

### Database Changes
- Add latitude and longitude columns to the `events` table
- Create a migration script to update the database schema

### Geocoding Service
- Implement a `GeocodingService` class in `app/services/geocoding`
- Use the `geopy` library for geocoding
- Implement error handling and rate limiting
- Add caching to avoid redundant API calls

### Integration Points
- Create a utility function to process all existing events
- Integrate geocoding into the event creation/update workflow
- Add hooks in the appropriate CRUD operations

## Implementation Plan

### Phase 1: Setup and Database Migration
1. Add geopy to requirements.txt
2. Create database migration for latitude and longitude columns
3. Update event model and schemas

### Phase 2: Geocoding Service Implementation
1. Create GeocodingService class
2. Implement geocoding functions
3. Add caching mechanism
4. Implement error handling and retry logic

### Phase 3: Integration
1. Create utility to process existing events
2. Integrate with event creation/update workflow
3. Add configuration options

### Phase 4: Testing
1. Write unit tests for geocoding service
2. Write integration tests
3. Validate results on existing data

## Configuration
- Add geocoding service configuration to environment variables:
  - GEOCODING_PROVIDER (default: "nominatim")
  - GEOCODING_USER_AGENT (required for Nominatim)
  - GEOCODING_API_KEY (if using a service that requires an API key)
  - GEOCODING_TIMEOUT (default: 5 seconds)
  - GEOCODING_RETRIES (default: 3) 

## Error Handling

### Failed Geocoding Attempts

The geocoding service may fail to find coordinates for some event locations due to several reasons:

1. **Invalid or vague address**: The location provided may be too vague, incomplete, or contain errors
2. **Geocoding service limitations**: The service may have trouble with certain types of addresses or locations
3. **Rate limiting**: The geocoding API may have hit usage limits
4. **Network issues**: Temporary connectivity problems with the geocoding service

### Handling Geocoding Failures

When the geocoding service fails to geocode an address, it follows these steps:

1. **Logging**: The failure is logged with details about the event and location
2. **Retries**: For temporary issues like timeouts, the service uses automatic retries (configurable via the GEOCODING_RETRIES setting)
3. **Leaving fields empty**: If geocoding ultimately fails, the latitude and longitude fields remain NULL in the database

### Manual Resolution Options

For events that cannot be automatically geocoded, consider these manual resolution approaches:

1. **Address correction**:
   - Review the problematic addresses from the logs
   - Edit the event's location field with a more geocoder-friendly format
   - Re-run the geocoding script for those specific events

2. **Manual coordinate assignment**:
   - For important events with known locations that still fail geocoding
   - Use map services (Google Maps, OpenStreetMap) to find coordinates manually
   - Update the database records directly using a database tool or API

3. **Bulk address correction**:
   - If many similar addresses fail, consider creating patterns for fixing them
   - Use database queries to identify and update similar problematic addresses
   - Create a script to clean and standardize addresses before geocoding

4. **Alternative geocoding providers**:
   - If one geocoding provider consistently fails for certain addresses, try another
   - Configure the service to fall back to alternative providers when the primary fails

### Testing Geocoding 

When implementing or testing the geocoding service:

1. **Start small**: Initially process just a few events using:
   ```bash
   # Test with just 3 events (default)
   make enrich-geocode
   
   # Process a specific number of events
   docker-compose run --rm api python -m scripts.geocode_events --limit 10
   
   # Process all events after testing
   docker-compose run --rm api python -m scripts.geocode_events --all
   ```

2. **Monitor failures**: Review the logs for geocoding failures and identify patterns
   - Check if failures are related to specific event types or location formats
   - Consider preprocessing address strings before sending to the geocoder

3. **Test with diverse addresses**: Include events from various countries, rural and urban areas
   - Geocoding success rates may vary significantly by region
   - Different address formats may require different handling

4. **Iterative improvements**: Use the results from initial tests to:
   - Improve address parsing/cleaning
   - Adjust geocoding parameters
   - Handle specific edge cases 