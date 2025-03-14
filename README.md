# TrailBlazeApp-API

Backend API and services for the TrailBlaze mobile application - a comprehensive platform for endurance and trail riders.

## Overview

TrailBlazeApp-API provides the server-side components that power the TrailBlaze mobile application. It includes a RESTful API for accessing event data, an AI-powered Q&A assistant, data scraping services, and other backend functionality essential for the mobile app.

This API serves as the central hub for data aggregation from various sources (PNER website, ride managers' websites, Facebook pages, etc.) and provides structured access to this information for the TrailBlaze mobile app.

## Features

- **Event Data API**: Comprehensive endpoints for retrieving event information, including details like ride dates, locations, and requirements
- **AI-powered Q&A Assistant**: Integration with Google's Gemini API to provide intelligent responses to rider questions
- **Data Scraping Services**: Automated collection of event data from various sources
- **Trip Planning Support**: APIs for calculating travel distances and times to ride locations
- **Weather Integration**: Weather data for ride locations
- **Authentication**: User account management and authentication services

## Technology Stack

- **Language**: Python 3.9+
- **Framework**: FastAPI
- **Database**: PostgreSQL
- **AI Integration**: Gemini API (Google AI)
- **Data Scraping**: Scrapy, Beautiful Soup
- **Authentication**: JWT (JSON Web Tokens)
- **Documentation**: OpenAPI 3.0 (Swagger)

## Project Structure

```
TrailBlazeApp-API/
├── api/                  # API specifications and documentation
├── app/                  # Main application code
│   ├── core/             # Core functionality, config, and utilities
│   ├── db/               # Database models and connection management
│   ├── endpoints/        # API route handlers
│   ├── schemas/          # Pydantic models for request/response validation
│   ├── services/         # Business logic services
│   └── main.py           # Application entry point
├── scrapers/             # Data scraping services
│   ├── event_scraper/    # Scripts for scraping event data
│   └── utils/            # Utilities for scraping and data processing
├── tests/                # Test suite
├── alembic/              # Database migration scripts
├── docker/               # Docker configuration files
├── .env.example          # Example environment variables
├── requirements.txt      # Python dependencies
└── README.md             # This file
```

## Getting Started

### Prerequisites

- Python 3.9+
- PostgreSQL 13+
- Docker and Docker Compose (optional, for containerized deployment)
- Google Cloud account (for Gemini API access)

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/highwayoflife/TrailBlazeApp-API.git
   cd TrailBlazeApp-API
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Copy the example environment file and fill in your values:
   ```
   cp .env.example .env
   ```

5. Set up the database:
   ```
   alembic upgrade head
   ```

6. Run the development server:
   ```
   uvicorn app.main:app --reload
   ```

The API will be available at `http://localhost:8000`. API documentation is accessible at `http://localhost:8000/docs`.

## Environment Variables

These environment variables need to be set in your `.env` file:

- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: Secret key for JWT token generation
- `GEMINI_API_KEY`: API key for Google's Gemini AI service
- `ALLOWED_ORIGINS`: Comma-separated list of allowed CORS origins
- `LOG_LEVEL`: Logging level (INFO, DEBUG, etc.)

## API Documentation

The API is documented using OpenAPI/Swagger. When the server is running, you can access:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

API specifications are also available in the `/api` directory as YAML files.

### Key Endpoints

- `/events`: Event calendar and details
- `/assistant/question`: AI Q&A assistant
- `/auth`: User authentication
- `/location`: Navigation and location services
- `/weather`: Weather information for ride locations

## Data Scraping Services

The TrailBlazeApp-API includes automated data scraping services that collect event information from various sources:

- PNER website
- Ride managers' websites
- Facebook pages
- AERC/EDRA listings

These scraping services run on a schedule and update the central database with the latest event information.

To run the scrapers manually:

```
cd scrapers
python run_scrapers.py
```

## Development Workflow

1. Create a new branch for your feature/fix
2. Make your changes
3. Run tests to ensure everything works: `pytest`
4. Update the OpenAPI specifications if you modified the API
5. Submit a pull request

### API Development Guidelines

When developing new API endpoints:

1. Define the endpoint in the appropriate OpenAPI specification file
2. Implement the endpoint in the FastAPI application
3. Write tests for the new endpoint
4. Update documentation as needed

## Deployment

### Docker Deployment

1. Build the Docker image:
   ```
   docker build -t trailblazeapp-api .
   ```

2. Run the container:
   ```
   docker run -p 8000:8000 --env-file .env trailblazeapp-api
   ```

### Cloud Deployment Options

- **Serverless**: Azure Functions, AWS Lambda, or Google Cloud Functions
- **Containerized**: Kubernetes, AWS ECS, or Google Cloud Run
- **PaaS**: Heroku, Fly.io, or similar platforms

## Monitoring

The API includes monitoring and logging to track:

- API usage statistics
- Error rates and exceptions
- AI usage (to keep within budgeted limits)
- Data scraping effectiveness

Logs are formatted for easy integration with cloud monitoring solutions.

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin feature-name`
5. Submit a pull request

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Contact

For questions or support, please contact the project maintainers.

---

TrailBlaze – Your Next Ride Starts Here.
