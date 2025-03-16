1. **Always use Makefile commands** for operations such as building, testing, running, and updating the application.
2. After making code changes or improvements, run the appropriate Makefile command to apply and test those changes.
3. Use Docker containers for all development and testing tasks as defined in the Makefile.

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
- Use `make format` to format code with black and isort

### Testing
- Use `make test` to run all tests
- Use `make test-unit` for unit tests only
- Use `make test-integration` for integration tests only
- Use `make test-api` for API tests against running services
- Use `make test-scraper` for scraper tests
- Use `make ci-test` for CI environment tests

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
