# Architecture Overview

## Summary

This document describes the architectural design of the TrailBlazeApp-API, explaining the system's components, their interactions, and the design principles behind them. The architecture is designed for scalability, maintainability, and performance to support the mobile application's requirements.

## Table of Contents

- [System Components](#system-components)
- [Data Flow](#data-flow)
- [Database Schema](#database-schema)
- [API Structure](#api-structure)
- [Authentication and Authorization](#authentication-and-authorization)
- [Integration Points](#integration-points)
- [Scalability Considerations](#scalability-considerations)

## System Components

The TrailBlazeApp-API consists of the following major components:

### 1. FastAPI Application

The core of the system is a FastAPI application that provides RESTful API endpoints. This component handles:
- HTTP request processing
- Input validation using Pydantic models
- Business logic execution
- Response formatting
- Documentation generation (OpenAPI/Swagger)

### 2. Database Layer

PostgreSQL database with SQLAlchemy ORM for data persistence:
- Event data (rides, competitions, etc.)
- User data (if applicable in the future)
- Cached AI responses (for frequently asked questions)

### 3. Data Scraping Service

Python-based scraping services built with Scrapy and Beautiful Soup that:
- Collect event data from various sources (PNER website, ride managers' websites, etc.)
- Parse and standardize the data
- Store it in the PostgreSQL database

### 4. AI Assistant Service

Integration with Google Gemini 2.0 Flash API to:
- Process natural language questions
- Provide relevant answers based on event data
- Handle general knowledge queries about trail riding

### 5. Middleware Components

Various middleware for:
- Logging
- Error handling
- CORS
- Authentication (for future use)

## Data Flow

The system's data flow follows these patterns:

1. **Event Data Flow:**
   ```
   External Sources → Scraping Service → Database → API → Mobile App
   ```

2. **Q&A Flow:**
   ```
   User Question → Mobile App → API → AI Service → API → Mobile App
   ```

3. **Authentication Flow (future):**
   ```
   User Credentials → Mobile App → API → Authentication Service → JWT → Mobile App
   ```

## Database Schema

The primary database entities include:

### Events

```
events
├── id (UUID, primary key)
├── name (string)
├── description (text)
├── location (string)
├── coordinates (lat/long)
├── date_start (datetime)
├── date_end (datetime)
├── organizer (string)
├── website (string, optional)
├── flyer_url (string, optional)
├── region (string)
├── distances (array of strings)
├── created_at (datetime)
├── updated_at (datetime)
```

Additional entities will be added as the application evolves to support features like user accounts, ride results, etc.

## API Structure

The API follows a versioned, resource-based structure:

```
/v1
├── /events
│   ├── GET / - List events
│   ├── GET /{id} - Get event details
│   ├── POST / - Create event (admin)
│   ├── PUT /{id} - Update event (admin)
│   └── DELETE /{id} - Delete event (admin)
├── /assistant
│   └── POST /ask - Ask the AI assistant a question
```

## Authentication and Authorization

The current MVP implementation doesn't include user authentication. For future implementations:

- JWT-based authentication
- Role-based access control (admin, user)
- OAuth integration for social logins

## Integration Points

### External Services

1. **Gemini API**
   - Used for: AI-powered Q&A assistant
   - Integration method: REST API
   - Configuration: API key in environment variables

2. **Weather APIs (planned)**
   - Used for: Weather forecasts for ride locations
   - Integration method: REST API
   - Configuration: API key in environment variables

### Data Sources

1. **PNER Website**
   - Used for: Scraping event listings
   - Method: HTML scraping

2. **Ride Managers' Websites**
   - Used for: Detailed event information
   - Method: HTML scraping, PDF parsing

## Scalability Considerations

The architecture supports horizontal scaling:

- Stateless API design
- Database connection pooling
- Containerization for easy deployment and scaling
- Asynchronous request handling with FastAPI

Future enhancements might include:
- Caching layer (Redis)
- Load balancing
- Read replicas for the database
