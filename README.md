# TrailBlazeApp-API

Backend API for the TrailBlaze application, a mobile app for endurance and trail riders, focusing initially on the PNER (Pacific Northwest Endurance Rides) region.

## Features

- RESTful API for event data
- AI-powered Q&A assistant using Gemini API
- Automated data scraping from multiple sources
- PostgreSQL database for data storage

## Technology Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Testing**: pytest
- **Documentation**: OpenAPI (Swagger)
- **Scraping**: Beautiful Soup, Scrapy
- **AI Integration**: Google Gemini 2.0 Flash API
- **Containerization**: Docker

## Setup

### Prerequisites

- Python 3.9+ 
- Docker and Docker Compose (for containerized setup)
- PostgreSQL (if running locally)

### Environment Variables

Create a `.env` file in the root directory with the following variables:

```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost/trailblaze
GEMINI_API_KEY=your_gemini_api_key
DEBUG=false
LOG_LEVEL=INFO
```

### Local Development Setup

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

4. Set up the database:
   ```
   alembic upgrade head
   ```

5. Run the server:
   ```
   uvicorn app.main:app --reload
   ```

6. Visit http://localhost:8000/docs for the API documentation

### Docker Setup

1. Build and run the containers:
   ```
   docker-compose up -d
   ```

2. The API will be available at http://localhost:8000

## Project Structure

```
TrailBlazeApp-API/
├── app/                      # Main application package
│   ├── api/                  # API endpoints
│   │   ├── openapi/         # OpenAPI schemas
│   │   └── v1/              # API version 1 endpoints
│   ├── crud/                 # Database CRUD operations
│   ├── models/               # SQLAlchemy ORM models
│   ├── schemas/              # Pydantic schemas
│   ├── services/             # Business logic services
│   ├── config.py             # Application configuration
│   ├── database.py           # Database connection
│   ├── logging_config.py     # Logging configuration
│   ├── middleware.py         # FastAPI middleware
│   └── main.py               # FastAPI application entry point
├── alembic/                  # Database migrations
├── docs/                     # Documentation
├── logs/                     # Application logs
├── scrapers/                 # Data scraping scripts
├── tests/                    # Test suite
├── .dockerignore             # Files to exclude from Docker
├── .env.example              # Example environment variables
├── alembic.ini               # Alembic configuration
├── docker-compose.yml        # Docker Compose configuration
├── Dockerfile                # Docker configuration
└── requirements.txt          # Python dependencies
```

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

## Testing

Run tests with pytest:

```
pytest
```

For coverage report:

```
pytest --cov=app
```

## Deployment

The API is designed to be deployed as a containerized application. The `Dockerfile` and `docker-compose.yml` files provide the necessary configuration.

For production deployments, consider:
- Setting up CI/CD pipelines
- Using managed database services
- Implementing proper monitoring and alerting
- Setting up a reverse proxy (e.g., Nginx) with HTTPS

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit your changes: `git commit -am 'Add feature'`
4. Push to the branch: `git push origin feature-name`
5. Submit a pull request

## License

[MIT License](LICENSE)
