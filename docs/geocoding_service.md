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