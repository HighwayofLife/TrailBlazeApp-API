# TrailBlazeApp-API Documentation

## Overview

TrailBlazeApp-API is the backend service for the TrailBlaze application, a mobile app for endurance and trail riders focusing initially on the PNER (Pacific Northwest Endurance Rides) region. This API provides event data, AI-powered Q&A capabilities, and other essential services to the mobile application.

## Documentation Index

- [Architecture Overview](architecture.md) - System design, components, and interactions
- [API Reference](api_reference.md) - Detailed documentation of all API endpoints
- [Development Guide](development_guide.md) - Setup, workflow, and best practices for developers
- [Testing Guide](testing_guide.md) - Testing strategies and procedures
- [Deployment Guide](deployment_guide.md) - Instructions for deploying the application
- [Maintenance Guide](maintenance_guide.md) - Information on maintaining and monitoring the application
- [Data Scraping Guide](data_scraping_guide.md) - Details on the event data scraping system

## Quick Start

```bash
# Clone the repository
git clone https://github.com/highwayoflife/TrailBlazeApp-API.git
cd TrailBlazeApp-API

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start the development server
uvicorn app.main:app --reload
```

Visit [http://localhost:8000/docs](http://localhost:8000/docs) to view the interactive API documentation.

## Technology Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Testing**: pytest
- **Documentation**: OpenAPI (Swagger)
- **Scraping**: Beautiful Soup, Scrapy
- **AI Integration**: Google Gemini 2.0 Flash API
- **Containerization**: Docker

## Project Status

This project is currently in active development for the initial launch, focusing on the PNER region.
