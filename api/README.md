# TrailBlaze App API Specifications

This directory contains the OpenAPI 3.0 specifications for the TrailBlaze App's backend services. These specifications define the contract between the mobile application and the backend services.

## API Overview

The TrailBlaze API is organized into several domain-specific APIs:

1. **Authentication API** (`auth_api.yaml`): Handles user authentication, registration, and account management.
2. **Events API** (`events_api.yaml`): Provides access to endurance riding events, including listings and details.
3. **Users API** (`users_api.yaml`): Manages user profiles and user-specific data.
4. **Horses API** (`horses_api.yaml`): Handles horse profiles, records, and related data.
5. **Registrations API** (`registrations_api.yaml`): Manages event registrations and payments.
6. **Results API** (`results_api.yaml`): Provides access to event results, leaderboards, and statistics.
7. **Location API** (`location_api.yaml`): Provides navigation and location services for ride events.
8. **Assistant API** (`assistant_api.yaml`): Powers the AI Q&A and ride assistance features.
9. **Weather API** (`weather_api.yaml`): Delivers weather forecasts and trail conditions for ride locations.
10. **Notifications API** (`notifications_api.yaml`): Manages user notifications and preferences.
11. **Media API** (`media_api.yaml`): Handles photos, videos, and GPS track uploads/retrieval.
12. **Social API** (`social_api.yaml`): Manages social interactions between users.
13. **Feedback API** (`feedback_api.yaml`): Handles user feedback and issue reporting.

## Authentication

All authenticated endpoints use Bearer token authentication. The authentication flow is as follows:

1. User logs in via the `/auth/login` endpoint
2. Backend returns an access token and refresh token
3. Client includes the access token in the `Authorization` header as `Bearer {token}` for authenticated requests
4. When the access token expires, use the refresh token to obtain a new access token via `/auth/refresh`

## Common Models

The API specifications share several common models across different domains. The most frequently used ones include:

- User representations (basic, detailed)
- Horse representations (basic, detailed)
- Event representations (basic, detailed)
- Registration and result data
- Location and weather data

## Using These Specifications

These OpenAPI specifications can be used with various tools:

- **Code Generation**: Generate API clients for Flutter using tools like OpenAPI Generator
- **API Testing**: Use tools like Postman to import the specifications for testing
- **Documentation**: Generate interactive documentation using Swagger UI or ReDoc

## Development Workflow

When making changes to the API:

1. Update the relevant OpenAPI specification file
2. Validate the specification using an OpenAPI validator
3. Update the backend implementation to match the specification
4. Update the mobile app's API client to match the specification

## Versioning

The API uses URL versioning (e.g., `/v1/events`). When making breaking changes, increment the version number and maintain backward compatibility for a reasonable period.
