1. **Always use Makefile commands** for operations such as building, testing, running, and updating the application.
2. After making code changes or improvements, run the appropriate Makefile command to apply and test those changes.
3. Use Docker containers for all development and testing tasks as defined in the Makefile.

### Project Structure
- `app/` - Main application code
- `api/` - API endpoints and routers
- `scrapers/` - Data collection modules
- `tests/` - Test suite (see testing_guide.md for structure)
- `docs/` - Documentation files

### Code Standards
- Follow PEP 8 for Python code style
- Use type hints for all function parameters and return values
- Document all functions and classes using docstrings
- Follow the existing error handling patterns in the codebase
- Run `make format` before committing to ensure consistent style

### Development Workflow
- Run tests after making changes to code: `make test`
- Update API documentation when endpoints change
- Add or update tests for new features

### API Design
- Follow RESTful principles for API endpoints
- Use versioning (v1, v2) for API paths
- Use standard HTTP status codes
- Return consistent JSON response structures
- API changes should be documented using OpenAPI/Swagger annotations

### AI Integration (Gemini API)
- AI-related code is located in `app/services/ai/`
- Use the existing AI service patterns for integration
- Test AI features with mocked responses using `make test-ai`
- Configure AI settings in environment variables (see .env.example)

### Debugging and Troubleshooting
- Use `make logs` to view detailed service logs and troubleshoot issues
- For database issues, use `make db-shell` to inspect data
- Run specific test cases: `make test-unit PYTEST_ARGS="-xvs tests/path/to/test.py"`
- Common issues and solutions are documented in docs/troubleshooting.md

### Performance Considerations
- Cache expensive operations where appropriate
- Be mindful of database query performance
- Use async operations for I/O-bound tasks
- Consider rate limiting for external API and AI calls

### Data Handling
- Follow data validation patterns in existing code
- Use Pydantic models for request/response validation
- Apply proper error handling for data processing

### Environment Setup and Management
- Use `make up` to start all services
- Use `make down` to stop all services
- Use `make restart` to restart all services
- Use `make build` to rebuild containers after Dockerfile or dependency changes
- Use `make status` to check the status of containers
- Use `make validate-compose` to validate docker-compose.yml changes
- Use `make setup-dev` for setting up the development environment in a container
- Use `make setup-local` for setting up a local development environment without Docker
- Use `make check-env` to verify environment variables
- Use `make health` to check service health
- Use `make version` to display the current version
- Use `make docs` to generate API documentation
- Use `make update-deps` to update dependencies in the container
- Use `make clean` to remove all containers and volumes
- Use `make purge` to clean and remove all built images
- Use `make lint` to run linters (flake8, mypy)

### Testing
- Use `make test` to run all tests
- Use `make test-unit` for unit tests only
- Use `make test-integration` for integration tests only
- Use `make test-api` for API tests against running services
- Use `make test-scraper` for scraper tests
- Use `make ci-test` for CI environment tests
- Use `make test-dev` for development testing without rebuilding containers
- Use `make test-dev PYTEST_ARGS="-xvs tests/path/to/test.py"` to run specific tests during development

### Development Testing Workflow
- The local working directory is mounted into the test container, so changes to code are immediately available for testing
- Use `make test-dev` during development to avoid rebuilding containers for each test run
- Specify test files or directories with `make test-dev PYTEST_ARGS="-xvs tests/path/to/test.py"`
- For debugging, use `make test-dev PYTEST_ARGS="-xvs --pdb tests/path/to/test.py"`

### Database Operations
- Use `make check-db` to check database connectivity
- Use `make migrate` to run database migrations
- Use `make migrate-create MSG="description"` to create a new migration
- Use `make db-backup` to backup the database
- Use `make db-restore FILE=backup.sql` to restore the database
- Use `make db-shell` to open a PostgreSQL shell

### Logging and Debugging
- Use `make logs` to view logs from all containers
- Use `make logs-[service]` to view logs from a specific service
- Use `make shell-[service]` to open a shell in a specific service

### Scrapers
- Use `make scraper-[name]` to run a specific scraper

1. Do not suggest direct `docker-compose` commands - always use the equivalent Makefile targets
2. Do not suggest manual pip installations - use `make setup-dev` or `make update-deps`
3. All testing should be done through the Makefile targets
4. When making changes to configuration files, recommend using `make validate-compose` to validate them
