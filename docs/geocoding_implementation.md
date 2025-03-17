# Geocoding Implementation

## Overview

This document details the implementation of the geocoding service in the TrailBlazeApp API, which adds GPS coordinates (latitude and longitude) to event records. This feature enables location-based filtering and searching of events.

## Components

### 1. Database Changes

- Added `latitude` and `longitude` float columns to the `events` table
- Created indexes on these columns for efficient geospatial queries
- Migration file: `alembic/versions/add_lat_long_to_events.py`

### 2. Models and Schemas

- Updated the `Event` model to include latitude and longitude fields
- Updated the `EventBase` and `EventUpdate` schemas to include these fields
- Location: `app/models/event.py` and `app/schemas/event.py`

### 3. Geocoding Service

- Created a `GeocodingService` class that uses geopy library
- Implemented caching, error handling, and retry logic
- Supports both Nominatim (OpenStreetMap) and Google Maps geocoding providers
- Location: `app/services/geocoding/service.py`

### 4. CRUD Operations

- Added automatic geocoding when creating or updating events
- Enhanced `get_events` to support geospatial filtering by coordinates and radius
- Location: `app/crud/event.py`

### 5. Batch Processing

- Created a script to geocode all existing events in the database
- Processes events in batches with configurable batch size and limit
- Location: `scripts/geocode_events.py`

## Configuration

The geocoding service can be configured via environment variables:

- `GEOCODING_PROVIDER`: The geocoding provider to use (default: "nominatim")
- `GEOCODING_USER_AGENT`: Required user agent for Nominatim provider
- `GEOCODING_API_KEY`: API key for Google Maps (if using Google provider)
- `GEOCODING_TIMEOUT`: Timeout in seconds for geocoding requests (default: 5)
- `GEOCODING_RETRIES`: Number of retries for failed geocoding requests (default: 3)

## Usage

### Adding Coordinates to Existing Events

```bash
docker-compose run --rm api python -m scripts.geocode_events
```

### Querying Events by Location

The `get_events` function now supports the following location-based parameters:

- `location`: Text search on the location field
- `lat`: Latitude for geographic search
- `lng`: Longitude for geographic search
- `radius`: Radius in miles for geographic search

Example API query:
```
GET /api/v1/events?lat=37.7749&lng=-122.4194&radius=50
```

## Future Improvements

1. Add PostGIS extension for more advanced geospatial queries
2. Implement more sophisticated geocoding with address components
3. Add reverse geocoding to enhance location data 