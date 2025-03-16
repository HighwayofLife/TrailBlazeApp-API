#!/bin/bash

# Exit on error
set -e

echo "Cleaning up any existing containers..."
docker-compose down

echo "Building test containers..."
docker-compose build test test-db

echo "Running tests..."
docker-compose run --rm \
    -e PYTHONPATH=/app \
    -e AERC_GEMINI_API_KEY=test_key \
    -e AERC_DEBUG_MODE=true \
    -e AERC_REFRESH_CACHE=true \
    -e AERC_VALIDATE=true \
    -e LOG_LEVEL=DEBUG \
    test pytest "$@"

# Get the exit code from pytest
exit_code=$?

echo "Cleaning up containers..."
docker-compose down

exit $exit_code