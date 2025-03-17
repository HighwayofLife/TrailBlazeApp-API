# Development Guide

## Summary

This document provides comprehensive instructions for developers working on the TrailBlazeApp-API. It covers setting up a development environment, code organization, coding standards, development workflow, and common tasks that developers need to perform.

## Table of Contents

- [Development Guide](#development-guide)
  - [Summary](#summary)
  - [Table of Contents](#table-of-contents)
  - [Development Environment Setup](#development-environment-setup)
    - [Prerequisites](#prerequisites)
    - [Local Development](#local-development)
    - [Docker Setup](#docker-setup)
  - [Project Structure](#project-structure)
  - [Code Style and Standards](#code-style-and-standards)
    - [Recommended Tools](#recommended-tools)
  - [Development Workflow](#development-workflow)
  - [Adding New Features](#adding-new-features)
  - [Database Migrations](#database-migrations)
  - [Working with the Gemini API](#working-with-the-gemini-api)
  - [Common Development Tasks](#common-development-tasks)
    - [Adding a New Endpoint](#adding-a-new-endpoint)
    - [Adding a New Scraper](#adding-a-new-scraper)
    - [Debugging Tips](#debugging-tips)

## Development Environment Setup

### Prerequisites

- Python 3.9+
- Git
- Docker and Docker Compose (optional, for containerized development)
- PostgreSQL (if running locally)

### Local Development

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

### Docker Setup

```bash
docker-compose up -d
```

Ensure that the following services are running:
- `db`: PostgreSQL database
- `api`: FastAPI application
- `scraper`: Scraper service
- `manage`: Management tasks

### Using the Makefile

The project includes a comprehensive Makefile that simplifies common development tasks. To see all available commands:

```bash
make help
```

#### Common Makefile Commands

| Command | Description |
|---------|-------------|
| `make build` | Build all Docker containers |
| `make up` | Start all services |
| `make down` | Stop all services |
| `make restart` | Restart all services |
| `make logs` | View logs from all containers |
| `make logs-api` | View logs from the API service |
| `make shell-api` | Open a shell in the API container |
| `make db-shell` | Open a PostgreSQL shell |
| `make test` | Run all tests |
| `make test-api` | Run API tests only |
| `make test-unit` | Run unit tests only |
| `make test-integration` | Run integration tests only |
| `make test-scraper` | Run scraper tests only |
| `make migrate` | Run database migrations |
| `make migrate-create MSG="message"` | Create a new migration |
| `make scraper-aerc_calendar` | Run a specific scraper |
| `make docs` | Generate API documentation |
| `make lint` | Run linters (flake8, mypy) |
| `make format` | Format code with black and isort |
| `make health` | Check health of services |
| `make db-backup` | Backup database to file |
| `make db-restore FILE=backup.sql` | Restore database from file |

#### Development Workflow with Makefile

A typical development workflow using the Makefile might look like:

```bash
# Start the services
make up

# View logs
make logs

# Run tests
make test

# Format code
make format

# Check linting
make lint

# Create a database migration
make migrate-create MSG="add user table"

# Apply migrations
make migrate

# Stop services when done
make down
```

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

## Code Style and Standards

We follow PEP 8 guidelines for Python code style. Additionally:

- Use 4 spaces for indentation (no tabs)
- Maximum line length of 88 characters (following Black formatter conventions)
- Docstrings for all public functions, classes, and methods
- Type hints for function parameters and return values
- Descriptive variable and function names

### Recommended Tools

- **Black**: For code formatting
- **isort**: For import sorting
- **flake8**: For linting
- **mypy**: For type checking

You can install these tools with:

```bash
pip install black isort flake8 mypy
```

And run them with:

```bash
black app/ tests/
isort app/ tests/
flake8 app/ tests/
mypy app/
```

## Development Workflow

We use a feature branch workflow:

1. **Create a feature branch:**

```bash
git checkout -b feature/your-feature-name
```

2. **Make changes and commit them:**

```bash
git add .
git commit -m "Descriptive commit message"
```

3. **Push your branch and create a pull request:**

```bash
git push origin feature/your-feature-name
```

4. **Code review and merge:**
   - Have at least one team member review your code
   - Make any requested changes
   - Once approved, merge into the main branch

## Adding New Features

When adding a new feature to the API:

1. **Update the API specification:**
   - Define new endpoints in the appropriate OpenAPI file in `app/api/openapi/`
   - Validate the specification using an OpenAPI validator

2. **Create Pydantic models:**
   - Define request and response models in `app/schemas/`
   - Include validation rules and examples

3. **Create or update database models:**
   - Define SQLAlchemy models in `app/models/`
   - Create migrations if needed

4. **Implement CRUD operations:**
   - Add necessary functions in `app/crud/`

5. **Implement business logic:**
   - Add service functions in `app/services/`

6. **Create API endpoints:**
   - Implement FastAPI routes in `app/api/v1/`

7. **Write tests:**
   - Unit tests for services and CRUD operations
   - Integration tests for API endpoints

8. **Update documentation:**
   - Update relevant documentation files

## Database Migrations

We use Alembic for database migrations:

1. **Create a new migration:**

```bash
alembic revision --autogenerate -m "Description of the change"
```

2. **Apply migrations:**

```bash
alembic upgrade head
```

3. **Downgrade if needed:**

```bash
alembic downgrade -1  # Go back one revision
```

## Working with the Gemini API

The application integrates with Google's Gemini API for AI-powered Q&A. Here's how to work with it:

1. **Get an API key:**
   - Sign up for Google AI Platform
   - Create a project and generate an API key
   - Add it to your `.env` file as `GEMINI_API_KEY`

2. **Use the service in your code:**

```python
from app.services.ai_service import ask_question

async def get_answer(question: str) -> str:
    context = "Information about endurance riding events"
    return await ask_question(question, context)
```

3. **Testing with mock responses:**
   - For tests, use the mock implementation in `tests/mocks/ai_service.py`

## Common Development Tasks

### Adding a New Endpoint

1. Define the endpoint in the appropriate file in `app/api/v1/`
2. Create any needed schemas in `app/schemas/`
3. Implement business logic in `app/services/`
4. Add tests in `tests/api/`

### Adding a New Scraper

1. Create a new scraper in the `scrapers/` directory
2. Implement the scraper logic using Scrapy or Beautiful Soup
3. Add the scraper to the scheduler in `scrapers/run_scrapers.py`
4. Add tests for the scraper in `tests/scrapers/`

### Debugging Tips

1. **Enable debug mode:**
   - Set `DEBUG=true` in your `.env` file
   - Set `LOG_LEVEL=DEBUG` for more detailed logs

2. **Use the interactive debugger:**
   - If using VS Code, use the provided launch configurations
   - Set breakpoints in your code

3. **Check the logs:**
   - Application logs are stored in the `logs/` directory
   - You can also view logs in the console when running with `--reload`
