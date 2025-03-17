# TrailBlazeApp-API

Backend API for the TrailBlaze application, a mobile app for distance, trail, and endurance and riders to help them plan, and get information about upcoming events, ride locations, and more.

![TrailBlazeApp Banner](./assets/trailblaze_banner_sm.png)

## Overview

TrailBlazeApp-API is the backend service that powers the TrailBlaze mobile application. It provides event data, AI-powered Q&A capabilities, and other essential services for endurance and trail riders.

## Features

- RESTful API for event data, user management, directions, and more.
- AI-powered Q&A assistant using Google Gemini 2.0 Flash API to easily answer user questions related to events, trails, training, and more.
- Automated data retrieval from multiple sources to keep event data up-to-date.
- PostgreSQL database for data storage

## Technology Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Testing**: pytest
- **Documentation**: OpenAPI (Swagger)
- **Scraping**: Beautiful Soup, Scrapy
- **AI Integration**: Google Gemini 2.0 Flash API
- **Containerization**: Docker

## Quick Start

### Prerequisites

- Python 3.9+ 
- Docker and Docker Compose (for containerized setup)
- Make (for using Makefile commands)

### Setup and Development

```bash
# Clone the repository
git clone https://github.com/highwayoflife/TrailBlazeApp-API.git
cd TrailBlazeApp-API

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Local Development (with Docker)
make build      # Build all containers
make up         # Start all services
make logs       # View logs

# Local Development (without Docker)
make setup-local  # Set up Python environment
make migrate      # Run database migrations
make docs         # Generate API documentation

# Testing
make test       # Run all tests
make test-api   # Run API tests only

# Maintenance
make health     # Check service health
make db-backup  # Backup database
```

Visit [http://localhost:8000/docs](http://localhost:8000/docs) to view the interactive API documentation.

### Common Makefile Commands

```bash
# View all available commands and descriptions
make help

# Development
make up         # Start services
make down       # Stop services
make restart    # Restart services
make logs       # View logs

# Database
make db-shell   # Open database shell
make migrate    # Run migrations

# Testing
make test       # Run all tests
make lint       # Run linters
make format     # Format code
```

For a complete list of Makefile commands and their descriptions, see the [Development Guide](docs/development_guide.md).

## Documentation

For detailed documentation, please see the [docs folder](docs/README.md):

- [Architecture Overview](docs/architecture.md)
- [API Reference](docs/api_reference.md)
- [Development Guide](docs/development_guide.md)
- [Testing Guide](docs/testing_guide.md)
- [Deployment Guide](docs/deployment_guide.md)
- [Maintenance Guide](docs/maintenance_guide.md)
- [Data Scraping Guide](docs/data_scraping_guide.md)

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Commit your changes: `git commit` (uses our commit message template)
5. Push to the branch: `git push origin feature-name`
6. Submit a pull request

See the [Development Guide](docs/development_guide.md) for our commit message format and coding standards.

## License

This project is licensed under the [Apache License 2.0](LICENSE).
