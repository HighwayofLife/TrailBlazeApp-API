# Development Guide

## Summary

This document provides comprehensive instructions for developers working on the TrailBlazeApp-API. It covers setting up a development environment, code organization, coding standards, development workflow, and common tasks that developers need to perform.

## Table of Contents

- [Development Guide](#development-guide)
  - [Summary](#summary)
  - [Table of Contents](#table-of-contents)
  - [Development Environment Setup](#development-environment-setup)
    - [Prerequisites](#prerequisites)
    - [Initial Setup](#initial-setup)
    - [Development Workflow](#development-workflow)
  - [Project Structure](#project-structure)
  - [Code Style and Standards](#code-style-and-standards)
  - [Adding New Features](#adding-new-features)
  - [Database Management](#database-management)
  - [Working with the Gemini API](#working-with-the-gemini-api)
  - [Common Development Tasks](#common-development-tasks)

## Development Environment Setup

### Prerequisites

- Python 3.9+
- Git
- Docker and Docker Compose
- Make

### Initial Setup

1. Clone the repository:
```bash
git clone https://github.com/highwayoflife/TrailBlazeApp-API.git
cd TrailBlazeApp-API
```

2. Set up environment:
```bash
cp .env.example .env   # Copy environment template
# Edit .env with your configuration
```

3. Choose your development mode:

**With Docker (recommended):**
```bash
make build            # Build containers
make up              # Start services
make logs            # View logs
```

**Without Docker:**
```bash
make setup-local     # Set up Python environment
make migrate         # Run migrations
```

### Development Workflow

The project uses a Makefile to standardize common tasks. View all commands with:
```bash
make help
```

#### Core Development Commands

| Category | Command | Description |
|----------|---------|-------------|
| **Services** |
| | `make up` | Start all services |
| | `make down` | Stop all services |
| | `make restart` | Restart all services |
| | `make logs` | View all logs |
| | `make logs-api` | View API logs |
| **Development** |
| | `make format` | Format code (black, isort) |
| | `make lint` | Run linters |
| | `make docs` | Generate API docs |
| | `make health` | Check service health |
| **Database** |
| | `make migrate` | Run migrations |
| | `make migrate-create MSG="..."` | Create migration |
| | `make db-shell` | Open database shell |
| | `make db-backup` | Backup database |
| | `make db-restore FILE=backup.sql` | Restore database |
| **Testing** |
| | `make test` | Run all tests |
| | `make test-api` | Run API tests |
| | `make test-unit` | Run unit tests |
| | `make test-integration` | Run integration tests |
| **Scraping** |
| | `make scraper-aerc_calendar` | Run AERC scraper |

#### Typical Development Cycle

1. Start services:
```bash
make up
make logs     # Monitor logs
```

2. Make changes and test:
```bash
make format   # Format code
make lint     # Check style
make test     # Run tests
```

3. Database changes:
```bash
make migrate-create MSG="add user table"
make migrate
```

4. Check health:
```bash
make health   # Verify services
```

5. Stop services:
```bash
make down
```

## Project Structure

```
TrailBlazeApp-API/
├── app/                    # Main application
│   ├── api/               # API endpoints
│   ├── crud/              # Database operations
│   ├── models/            # SQLAlchemy models
│   ├── schemas/           # Pydantic schemas
│   └── services/          # Business logic
├── docs/                  # Documentation
├── scrapers/             # Data scrapers
├── tests/                # Test suite
└── Makefile             # Development commands
```

## Code Style and Standards

We enforce code style using automated tools:

```bash
make format   # Run black and isort
make lint     # Run flake8 and mypy
```

Standards:
- PEP 8 guidelines
- 88 character line length (Black)
- Type hints required
- Docstrings for public interfaces

## Adding New Features

1. Create feature branch:
```bash
git checkout -b feature/name
```

2. Implement changes following this order:
   - Update OpenAPI spec
   - Add/update models
   - Implement CRUD
   - Add endpoints
   - Write tests

3. Verify changes:
```bash
make format
make lint
make test
make docs
```

4. Commit changes:
```bash
git add .
git commit    # Uses our template
```

## Database Management

Database operations are managed through the Makefile:

```bash
make migrate-create MSG="..."  # Create migration
make migrate                   # Apply migrations
make db-backup                # Backup database
make db-restore FILE=...      # Restore backup
make db-shell                 # Open psql shell
```

## Working with the Gemini API

1. Add your API key to `.env`:
```
GEMINI_API_KEY=your_key_here
```

2. Use the AI service:
```python
from app.services.ai_service import ask_question

async def get_answer(question: str) -> str:
    return await ask_question(question)
```

## Common Development Tasks

### Adding a New Endpoint

1. Define endpoint in `app/api/v1/`
2. Add schemas in `app/schemas/`
3. Implement logic in `app/services/`
4. Add tests in `tests/api/`
5. Update OpenAPI documentation

### Adding a New Scraper

1. Create scraper in `scrapers/`
2. Add to scheduler
3. Add tests in `tests/scrapers/`
4. Run with `make scraper-name`
