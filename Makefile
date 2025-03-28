# TrailBlaze Makefile
# 
# This Makefile provides commands for building, running, and testing
# the TrailBlaze application. All commands execute within Docker containers.

# Common variables
DOCKER_COMPOSE := docker-compose
PROJECT_NAME := trailblaze

.PHONY: help build up down restart status logs test test-api test-unit test-integration test-scraper check-db clean docs version check-env health setup-local setup-test-db clean-test-db test-sequential enrich-geocode enrich-website test-aerc-scraper test-aerc-specific test-aerc-parser test-aerc-database

# Colors for terminal output
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

# Default target
.DEFAULT_GOAL := help

# Try to extract version from version file if it exists
VERSION := $(shell if [ -f app/version.py ]; then grep -m1 version app/version.py | cut -d'"' -f2; else echo "development"; fi)

help: ## Show this help message
	@echo "${BLUE}TrailBlaze${NC} - Makefile commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  ${GREEN}%-20s${NC} %s\n", $$1, $$2}'

# Build and Run
build: ## Build all containers
	$(DOCKER_COMPOSE) build

up: ## Start all services
	$(DOCKER_COMPOSE) up -d
	@echo "${GREEN}Services started!${NC}"
	@echo "API will be available at http://localhost:8000"
	@echo "API docs at http://localhost:8000/docs"

down: ## Stop all services
	$(DOCKER_COMPOSE) down
	@echo "${GREEN}Services stopped!${NC}"

restart: down up ## Restart all services

status: ## Check status of containers
	$(DOCKER_COMPOSE) ps

logs: ## View logs from all containers
	$(DOCKER_COMPOSE) logs --tail=100 -f

logs-%: ## View logs from a specific service (e.g. make logs-api)
	$(DOCKER_COMPOSE) logs --tail=100 -f $*

# Development Helpers
shell-%: ## Open a shell in a specific service (e.g. make shell-api)
	$(DOCKER_COMPOSE) exec $* bash

db-shell: ## Open a PostgreSQL interactive shell. Note: Use docker-compose directly to run direct commands on the database and pipe to cat to see the output.
	$(DOCKER_COMPOSE) exec db psql -U postgres -d $(PROJECT_NAME)

# Clean Test Database
clean-test-db: ## Clean all data from the test database
	@echo "${BLUE}Cleaning test database...${NC}"
	$(DOCKER_COMPOSE) up -d test-db
	@echo "Waiting for test database to be ready..."
	@sleep 5
	@echo "Cleaning test database tables..."
	$(DOCKER_COMPOSE) run --rm \
		-e PYTHONPATH=/app \
		test python -m scripts.testing.clean_test_db
	@echo "${GREEN}Test database cleaned!${NC}"

# Setup Test Database
setup-test-db: clean-test-db ## Create tables in the test database
	@echo "${BLUE}Setting up test database...${NC}"
	@echo "Creating tables in test database..."
	$(DOCKER_COMPOSE) run --rm \
		-e PYTHONPATH=/app \
		test python -m scripts.testing.create_tables
	@echo "${GREEN}Test database setup complete!${NC}"

# Testing Commands
test: setup-test-db ## Run all tests
	$(DOCKER_COMPOSE) down
	$(DOCKER_COMPOSE) build test test-db
	$(DOCKER_COMPOSE) run --rm \
		-e PYTHONPATH=/app \
		-e AERC_GEMINI_API_KEY=test_key \
		-e AERC_DEBUG_MODE=true \
		-e AERC_REFRESH_CACHE=true \
		-e AERC_VALIDATE=true \
		-e LOG_LEVEL=DEBUG \
		test pytest
	$(DOCKER_COMPOSE) down

test-sequential: ## Run tests sequentially to avoid event loop issues
	@echo "${BLUE}Running tests sequentially...${NC}"
	python -m scripts.testing.run_tests_sequentially

test-api: ## Run API tests against running services
	$(DOCKER_COMPOSE) exec api python -m scripts.testing.test_api

test-unit: setup-test-db ## Run unit tests only
	$(DOCKER_COMPOSE) run --rm \
		-e PYTHONPATH=/app \
		-e LOG_LEVEL=DEBUG \
		test pytest tests/api

test-dev: setup-test-db ## Run tests in development mode without rebuilding
	$(DOCKER_COMPOSE) run --rm \
		-e PYTHONPATH=/app \
		-e AERC_GEMINI_API_KEY=test_key \
		-e AERC_DEBUG_MODE=true \
		-e AERC_REFRESH_CACHE=true \
		-e AERC_VALIDATE=true \
		-e LOG_LEVEL=DEBUG \
		test pytest $(PYTEST_ARGS)

test-integration: setup-test-db ## Run integration tests only
	$(DOCKER_COMPOSE) run --rm \
		-e PYTHONPATH=/app \
		-e LOG_LEVEL=DEBUG \
		test pytest tests/integration

test-scraper: setup-test-db ## Run scraper tests
	$(DOCKER_COMPOSE) run --rm \
		-e PYTHONPATH=/app \
		-e AERC_GEMINI_API_KEY=test_key \
		-e AERC_DEBUG_MODE=true \
		-e AERC_REFRESH_CACHE=true \
		-e AERC_VALIDATE=true \
		-e LOG_LEVEL=DEBUG \
		test pytest tests/scrapers

test-aerc-scraper: setup-test-db ## Run AERC scraper tests with beautiful output
	@echo "${BLUE}🏇 Running AERC scraper tests...${NC}"
	$(DOCKER_COMPOSE) run --rm \
		-e PYTHONPATH=/app \
		-e AERC_GEMINI_API_KEY=test_key \
		-e AERC_DEBUG_MODE=true \
		-e AERC_REFRESH_CACHE=true \
		-e AERC_VALIDATE=true \
		-e LOG_LEVEL=DEBUG \
		test python -m scrapers.aerc_scraper.tests.run_tests
	@echo "${GREEN}✅ AERC scraper tests complete!${NC}"

test-aerc-specific: setup-test-db ## Run a specific AERC test file (TEST_FILE=test_filename.py)
	@if [ -z "$(TEST_FILE)" ]; then \
		echo "${YELLOW}⚠️ Please specify a test file. Example: make test-aerc-specific TEST_FILE=test_parser_with_samples.py${NC}"; \
		exit 1; \
	fi
	@echo "${BLUE}🔍 Running AERC scraper test: $(TEST_FILE)${NC}"
	$(DOCKER_COMPOSE) run --rm \
		-e PYTHONPATH=/app \
		-e AERC_GEMINI_API_KEY=test_key \
		-e AERC_DEBUG_MODE=true \
		-e AERC_REFRESH_CACHE=true \
		-e AERC_VALIDATE=true \
		-e LOG_LEVEL=DEBUG \
		test python -m scrapers.aerc_scraper.tests.$(TEST_FILE:.py=)
	@echo "${GREEN}✅ AERC scraper test $(TEST_FILE) complete!${NC}"

test-aerc-parser: setup-test-db ## Run AERC parser validation tests
	@echo "${BLUE}🔎 Running AERC parser validation tests...${NC}"
	$(DOCKER_COMPOSE) run --rm \
		-e PYTHONPATH=/app \
		-e AERC_GEMINI_API_KEY=test_key \
		-e AERC_DEBUG_MODE=true \
		-e AERC_REFRESH_CACHE=true \
		-e AERC_VALIDATE=true \
		-e LOG_LEVEL=DEBUG \
		test python -m scrapers.aerc_scraper.tests.test_parser_with_samples
	@echo "${GREEN}✅ AERC parser validation tests complete!${NC}"

test-aerc-database: clean-test-db setup-test-db
	@echo "💾 Running AERC database integration tests... "
	@docker-compose run --rm \
		-e PYTHONPATH=/app \
		-e AERC_GEMINI_API_KEY=test_key \
		-e AERC_DEBUG_MODE=true \
		-e AERC_REFRESH_CACHE=true \
		-e AERC_VALIDATE=true \
		-e LOG_LEVEL=DEBUG \
		test python -m scrapers.aerc_scraper.tests.run_html_to_database_test
	@echo "✅ Tests completed"

# Database Commands
check-db: ## Check database connectivity
	$(DOCKER_COMPOSE) run --rm api python -m scripts.check_database

migrate: ## Run database migrations
	$(DOCKER_COMPOSE) run --rm api alembic upgrade head

migrate-create: ## Create a new migration
	@if [ -z "$(MSG)" ]; then \
		echo "${YELLOW}Please specify a migration message. Example: make migrate-create MSG='add user table'${NC}"; \
		exit 1; \
	fi
	$(DOCKER_COMPOSE) run --rm api alembic revision --autogenerate -m "$(MSG)"

# Scraper Commands
scraper-%: ## Run a specific scraper (e.g. make scraper-aerc_calendar)
	$(DOCKER_COMPOSE) run --rm scraper python -m scrapers.run_scrapers $*

# Improved AERC Scraper Command
scraper-aerc-v2: ## Run the improved AERC scraper with direct HTML parsing
	@echo "${BLUE}Running improved AERC scraper (v2)...${NC}"
	$(DOCKER_COMPOSE) run --rm \
		-e SCRAPER_DEBUG=${SCRAPER_DEBUG:-false} \
		-e SCRAPER_REFRESH=${SCRAPER_REFRESH:-false} \
		-e LOG_LEVEL=${LOG_LEVEL:-INFO} \
		scraper python -m scrapers.run_aerc_v2
	@echo "${GREEN}Improved AERC scraper (v2) complete!${NC}"

# Enrichment Commands
enrich-geocode: ## Run the geocoding enrichment service (default: test with 3 events)
	@echo "${BLUE}Running geocoding enrichment on a test sample of 3 events...${NC}"
	$(DOCKER_COMPOSE) run --rm api python -m scripts.geocode_events
	@echo "${GREEN}Geocoding test enrichment complete!${NC}"
	@echo "To geocode more events, use: make enrich-geocode-more LIMIT=10"
	@echo "To geocode all events, use: make enrich-geocode-all"

enrich-geocode-more: ## Run geocoding on a specific number of events (specify with LIMIT=X)
	@if [ -z "$(LIMIT)" ]; then \
		echo "${YELLOW}Please specify a limit. Example: make enrich-geocode-more LIMIT=10${NC}"; \
		exit 1; \
	fi
	@echo "${BLUE}Running geocoding enrichment on $(LIMIT) events...${NC}"
	$(DOCKER_COMPOSE) run --rm api python -m scripts.geocode_events --limit $(LIMIT)
	@echo "${GREEN}Geocoding enrichment complete!${NC}"

enrich-geocode-all: ## Run geocoding on all events that need coordinates
	@echo "${BLUE}Running geocoding enrichment on all events...${NC}"
	$(DOCKER_COMPOSE) run --rm api python -m scripts.geocode_events --all
	@echo "${GREEN}Geocoding enrichment of all events complete!${NC}"

enrich-website: ## Run the website/flyer enrichment service
	@echo "${BLUE}Running website/flyer enrichment...${NC}"
	$(DOCKER_COMPOSE) run --rm api python -m scripts.enrich_website_flyer
	@echo "${GREEN}Website/flyer enrichment complete!${NC}"

# Documentation
docs: ## Generate API documentation
	$(DOCKER_COMPOSE) run --rm api python -m scripts.generate_docs

# Cleanup Commands
clean: down ## Remove all containers and volumes
	$(DOCKER_COMPOSE) down -v
	@echo "${GREEN}Removed all containers and volumes${NC}"

purge: clean ## Clean and remove all built images
	$(DOCKER_COMPOSE) down --rmi all -v
	@echo "${GREEN}Removed all containers, volumes, and images${NC}"

# Development Setup
setup-dev: ## Set up development environment (in container)
	$(DOCKER_COMPOSE) run --rm api pip install -r requirements-dev.txt
	@echo "${GREEN}Development dependencies installed${NC}"

# CI Commands
ci-test: setup-test-db ## Run tests for CI environment
	$(DOCKER_COMPOSE) -f docker-compose.yml build test test-db
	$(DOCKER_COMPOSE) -f docker-compose.yml run --rm \
		-e PYTHONPATH=/app \
		-e AERC_GEMINI_API_KEY=test_key \
		-e LOG_LEVEL=DEBUG \
		test pytest --junitxml=junit.xml
	$(DOCKER_COMPOSE) -f docker-compose.yml down

# Database Migration Commands
db-backup: ## Backup database to file
	@echo "Creating database backup..."
	$(DOCKER_COMPOSE) exec -T db pg_dump -U postgres $(PROJECT_NAME) > backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "${GREEN}Backup created: backup_$(shell date +%Y%m%d_%H%M%S).sql${NC}"

db-restore: ## Restore database from file (specify FILE=backup.sql)
	@if [ -z "$(FILE)" ]; then \
		echo "${YELLOW}Please specify a backup file. Example: make db-restore FILE=backup.sql${NC}"; \
		exit 1; \
	fi
	@if [ ! -f "$(FILE)" ]; then \
		echo "${YELLOW}File $(FILE) does not exist${NC}"; \
		exit 1; \
	fi
	@echo "Restoring database from $(FILE)..."
	$(DOCKER_COMPOSE) exec -T db psql -U postgres -d $(PROJECT_NAME) < $(FILE)
	@echo "${GREEN}Database restored from $(FILE)${NC}"

# Linting and Formatting
lint: ## Run linters (flake8, mypy)
	$(DOCKER_COMPOSE) run --rm api flake8 app tests
	$(DOCKER_COMPOSE) run --rm api mypy app

format: ## Format code with black and isort
	$(DOCKER_COMPOSE) run --rm api black app tests
	$(DOCKER_COMPOSE) run --rm api isort app tests

# Additional commands as suggested

version: ## Display the current version
	@echo "TrailBlaze API version: ${VERSION}"

check-env: ## Check required environment variables
	@echo "Checking environment variables..."
	@if [ -z "$(GEMINI_API_KEY)" ] && grep -q GEMINI_API_KEY .env; then \
		echo "${YELLOW}Warning: GEMINI_API_KEY is not set in environment but exists in .env file${NC}"; \
	else \
		if [ -z "$(GEMINI_API_KEY)" ]; then \
			echo "${YELLOW}GEMINI_API_KEY is not set${NC}"; \
			exit 1; \
		fi; \
	fi
	@echo "${GREEN}All required environment variables are set${NC}"

health: ## Check health of services
	@echo "Checking service health..."
	@$(DOCKER_COMPOSE) ps | grep -q Up || (echo "${YELLOW}Services are not running${NC}"; exit 1)
	@$(DOCKER_COMPOSE) exec db pg_isready -U postgres >/dev/null 2>&1 || (echo "${YELLOW}Database is not ready${NC}"; exit 1)
	@echo "${GREEN}All services are healthy${NC}"

setup-local: ## Set up local environment (without Docker)
	@echo "Setting up local Python environment..."
	python -m venv venv
	. venv/bin/activate && pip install -r requirements.txt
	@if [ -f requirements-dev.txt ]; then \
		. venv/bin/activate && pip install -r requirements-dev.txt; \
	fi
	@echo "${GREEN}Local development environment set up${NC}"
	@echo "Activate with: source venv/bin/activate"

update-deps: ## Update dependencies in the container
	$(DOCKER_COMPOSE) run --rm api pip install --upgrade -r requirements.txt
	@if [ -f requirements-dev.txt ]; then \
		$(DOCKER_COMPOSE) run --rm api pip install --upgrade -r requirements-dev.txt; \
	fi
	@echo "${GREEN}Dependencies updated${NC}"

validate-compose: ## Validate docker-compose.yml file
	$(DOCKER_COMPOSE) config
	@echo "${GREEN}docker-compose.yml is valid${NC}"