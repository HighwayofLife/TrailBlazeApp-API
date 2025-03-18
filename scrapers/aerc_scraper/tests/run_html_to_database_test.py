#!/usr/bin/env python
"""
Comprehensive HTML to Database Integration Test Runner

This script runs the HTML-to-database pipeline tests for the AERC scraper,
validating the entire data flow from HTML parsing to database validation.
"""

import os
import sys
import pytest
from pathlib import Path

# Add project root to the Python path
project_root = str(Path(__file__).parents[3])
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the HTML samples data
from scrapers.aerc_scraper.tests.expected_test_data import EVENT_SAMPLES

if __name__ == "__main__":
    # Enable debug output if requested
    debug_mode = False
    if "--debug" in sys.argv:
        os.environ["DEBUG"] = "1"
        debug_mode = True
        sys.argv.remove("--debug")
    
    print("\n" + "="*80)
    print(" AERC HTML to Database Integration Tests ".center(80, "="))
    print("="*80)
    
    # Print summary of what will be tested
    print(f"\nTesting HTML-to-database pipeline with {len(EVENT_SAMPLES)} sample events:")
    for i, sample in enumerate(EVENT_SAMPLES, 1):
        print(f"  {i}. {sample}")
    
    print("\nValidation steps:")
    print("  1. Parse HTML → Extract structured data")
    print("  2. Transform data → Validate data structure")
    print("  3. Convert to database models → Prepare for storage")
    print("  4. Store in database → Verify database operations")
    print("  5. Validate stored data → Match against expected reference")
    
    print("\nRunning tests...\n")
    
    # Get the path to the test file
    test_file = "test_html_to_database_integration.py"
    test_path = str(Path(__file__).parent / test_file)
    
    # Run with pytest
    exit_code = pytest.main([test_path, "-v"])
    
    # Exit based on test results
    if exit_code == 0:
        print("\n" + "="*80)
        print(" RESULTS SUMMARY ".center(80, "="))
        print("="*80)
        print(f"\n✅ All tests passed successfully!")
        print(f"   - Processed {len(EVENT_SAMPLES)} HTML samples")
        print(f"   - Validated complete HTML-to-database pipeline")
        print(f"   - Verified update handling for existing events")
        print("\n" + "="*80)
        sys.exit(0)
    else:
        print("\n" + "="*80)
        print(" TEST FAILURES ".center(80, "="))
        print("="*80)
        print(f"\n❌ Tests failed. Please check the output above for details.")
        print("\n" + "="*80)
        sys.exit(1) 