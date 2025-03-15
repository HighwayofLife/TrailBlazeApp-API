#!/bin/bash

echo "Starting TrailBlaze API containers..."
docker-compose up -d

echo "Waiting for services to initialize..."
sleep 5

echo "Running API tests..."
python test_api.py

TEST_EXIT_CODE=$?

echo "Tests completed with exit code: $TEST_EXIT_CODE"

echo "To stop the containers, run: docker-compose down"

exit $TEST_EXIT_CODE