#!/usr/bin/env python3
"""
Test runner for AERC scraper tests.
This script discovers and runs all tests in the tests directory.
"""

import unittest
import sys
import os
from pathlib import Path

# Add project root to path
project_root = str(Path(__file__).parents[3])
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def run_tests(test_path=None, verbosity=2):
    """
    Run all tests in the specified path, or current directory if None.
    
    Args:
        test_path: Path to the test files or directories
        verbosity: Verbosity level for test output
        
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    # If no path specified, use the current directory
    if test_path is None:
        test_path = os.path.dirname(os.path.abspath(__file__))
    
    print(f"Running AERC scraper tests from {test_path}")
    
    # List of test modules to prioritize in the display
    important_tests = [
        "test_special_cases.py",  # Special cases tests (flyer links, cancelled events, coordinates)
        "test_html_parser.py",    # HTML parser tests
        "test_distance_handling.py",  # Distance handling tests
        "test_database_insertion.py"  # Database tests
    ]
    
    # Find all test modules in the test directory
    test_files = []
    for file in os.listdir(test_path):
        if file.startswith("test_") and file.endswith(".py"):
            # Prioritize important tests
            if file in important_tests:
                test_files.insert(important_tests.index(file), file)
            else:
                test_files.append(file)
    
    # Remove duplicates while preserving order
    test_files = list(dict.fromkeys(test_files))
    
    # Count total tests and print information
    total_tests = 0
    for file in test_files:
        test_loader = unittest.TestLoader()
        tests = test_loader.discover(test_path, pattern=file)
        test_count = tests.countTestCases()
        if test_count > 0:
            print(f"Found {test_count} tests in {file}")
            total_tests += test_count
    
    print(f"\nRunning {total_tests} total tests\n")
    print("-" * 80)
    
    # Create and run a test suite with all tests
    loader = unittest.TestLoader()
    suite = loader.discover(test_path, pattern="test_*.py")
    
    runner = unittest.TextTestRunner(verbosity=verbosity)
    results = runner.run(suite)
    
    # Print a summary
    print("-" * 80)
    print(f"Tests run: {results.testsRun}")
    print(f"Errors: {len(results.errors)}")
    print(f"Failures: {len(results.failures)}")
    print(f"Skipped: {len(results.skipped)}")
    
    # Return appropriate exit code
    return 0 if results.wasSuccessful() else 1

if __name__ == "__main__":
    # Use command line arguments for test path if provided
    test_path = sys.argv[1] if len(sys.argv) > 1 else None
    verbosity = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    
    sys.exit(run_tests(test_path, verbosity)) 