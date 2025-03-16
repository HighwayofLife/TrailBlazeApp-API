#!/bin/bash

# Enable error handling
set -e

# Set up environment variables for testing
export AERC_GEMINI_API_KEY=test_key
export AERC_DEBUG_MODE=true
export AERC_REFRESH_CACHE=true

# Create required test directories
mkdir -p tests/temp_cache tests/metrics

# Clean up any leftover test files
cleanup() {
    echo "Cleaning up test directories..."
    rm -rf tests/temp_cache/* tests/metrics/*
}
trap cleanup EXIT

# Run pytest with coverage
echo "Running AERC scraper tests..."
pytest tests/scrapers/aerc_scraper \
    --cov=scrapers.aerc_scraper \
    --cov-report=term-missing \
    --cov-report=html:coverage \
    -v \
    "$@"

# Run integration tests separately if specified
if [[ "$*" == *"--integration"* ]]; then
    echo "Running integration tests..."
    pytest tests/scrapers/aerc_scraper/test_integration.py -v
fi

# Report test coverage
echo "Test coverage report generated in ./coverage directory"