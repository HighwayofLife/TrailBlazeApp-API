#!/usr/bin/env python
"""
Run the database validation tests for AERC scraper.

This script runs the comprehensive validation tests that verify
data inserted into the database matches the expected structured data.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add project root to the Python path
project_root = str(Path(__file__).parents[3])
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the test functions
from scrapers.aerc_scraper.tests.test_database_validation import TestDatabaseValidation

async def run_tests():
    """Run all tests and return the results."""
    test_class = TestDatabaseValidation()
    test_class.setUp()
    
    # Run first test (synchronous)
    print("Running test_event_create_structure_validation...")
    await asyncio.sleep(0)  # Just to make it part of the async flow
    try:
        test_class.test_event_create_structure_validation()
        print("✅ Structure validation test passed")
    except Exception as e:
        print(f"❌ Structure validation test failed: {str(e)}")
        raise
    
    # Run second test (async)
    print("\nRunning test_database_field_validation...")
    try:
        await test_class.test_database_field_validation()
        print("✅ Database field validation test passed")
    except Exception as e:
        print(f"❌ Database field validation test failed: {str(e)}")
        raise
    
    # Run third test (async)
    print("\nRunning test_geocoding_fields...")
    try:
        await test_class.test_geocoding_fields()
        print("✅ Geocoding fields test passed")
    except Exception as e:
        print(f"❌ Geocoding fields test failed: {str(e)}")
        raise
    
    return True

if __name__ == "__main__":
    # Enable debug output if requested
    if "--debug" in sys.argv:
        os.environ["DEBUG"] = "1"
        sys.argv.remove("--debug")
    
    print("Running database validation tests...")
    try:
        asyncio.run(run_tests())
        print("\nAll tests passed! ✅")
        sys.exit(0)
    except Exception as e:
        print(f"\nTests failed: {str(e)} ❌")
        sys.exit(1) 