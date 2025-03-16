# TrailBlaze Makefile
# 
# This Makefile provides commands for building, running, and testing
# the TrailBlaze application. All commands execute within Docker containers.

# Common variables
DOCKER_COMPOSE := docker-compose
PROJECT_NAME := trailblaze

.PHONY: help build up down restart status logs test test-api test-unit test-integration test-scraper check-db clean docs version check-env health setup-local

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

db-shell: ## Open a PostgreSQL shell
	$(DOCKER_COMPOSE) exec db psql -U postgres -d $(PROJECT_NAME)

# Testing Commands
test: ## Run all tests
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

test-api: ## Run API tests against running services
	$(DOCKER_COMPOSE) exec api python test_api.py

test-unit: ## Run unit tests only
	$(DOCKER_COMPOSE) run --rm \
		-e PYTHONPATH=/app \
		-e LOG_LEVEL=DEBUG \
		test pytest tests/api
	
test-integration: ## Run integration tests only
	$(DOCKER_COMPOSE) run --rm \
		-e PYTHONPATH=/app \
		-e LOG_LEVEL=DEBUG \
		test pytest tests/integration

test-scraper: ## Run scraper tests
	$(DOCKER_COMPOSE) run --rm \
		-e PYTHONPATH=/app \
		-e AERC_GEMINI_API_KEY=test_key \
		-e AERC_DEBUG_MODE=true \
		-e AERC_REFRESH_CACHE=true \
		-e AERC_VALIDATE=true \
		-e LOG_LEVEL=DEBUG \
		test pytest tests/scrapers

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
ci-test: ## Run tests for CI environment
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