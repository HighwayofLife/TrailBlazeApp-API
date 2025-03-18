#!/usr/bin/env python3
"""
Test runner for AERC scraper tests.
This script discovers and runs all tests in the tests directory.
"""

import pytest
import sys
import os
import time
from pathlib import Path

# Add project root to path
project_root = str(Path(__file__).parents[3])
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def run_tests(test_path=None, verbosity=None):
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
    
    print(f"🏇 Running AERC scraper tests from {test_path}")
    
    # List of test modules to prioritize in the display
    important_tests = [
        "test_html_to_database_integration.py", # Comprehensive HTML-to-database pipeline test (highest priority)
        "test_parser_with_samples.py",          # HTML parser test with real samples
        "test_special_cases.py",                # Special cases tests
        "test_html_parser.py",                  # Basic HTML parser tests
        "test_distance_handling.py",            # Distance handling tests
        "test_data_handler.py",                 # Data transformation tests
        "test_utils.py",                        # Utility function tests
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
    
    # List available test files
    print("\n📋 Available test files:")
    for file in test_files:
        category = "Other"
        emoji = "🔍"
        
        if "html_to_database" in file:
            category = "Database Pipeline"
            emoji = "🔄"
        elif "parser" in file:
            category = "HTML Parsing"
            emoji = "🔎"
        elif "database" in file:
            category = "Database"
            emoji = "💾"
        elif "distance" in file:
            category = "Data Processing"
            emoji = "📏"
        elif "utils" in file:
            category = "Utilities"
            emoji = "🛠️"
        elif "handler" in file or "data" in file:
            category = "Data Transformation"
            emoji = "🧰"
        
        print(f"  {emoji} [{category:18}] {file}")
    
    print(f"\n🚀 Running tests from {test_path}\n")
    print("-" * 80)
    
    # Start time
    start_time = time.time()
    
    # Build pytest arguments
    pytest_args = [test_path]
    
    # Add verbosity
    if verbosity:
        if verbosity == 2:
            pytest_args.append("-v")
        elif verbosity > 2:
            pytest_args.append("-vv")
    else:
        pytest_args.append("-v")
    
    # Run tests with pytest
    result = pytest.main(pytest_args)
    
    # End time
    end_time = time.time()
    duration = end_time - start_time
    
    # Print a summary with emojis
    print("-" * 80)
    print("📊 Test Results Summary:")
    print(f"  ⏱️  Time: {duration:.2f} seconds")
    
    # Final result
    if result == 0:
        print("\n🎉 All tests passed successfully! 🎉")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above. ⚠️")
    
    # Return appropriate exit code
    return result

if __name__ == "__main__":
    # Use command line arguments for test path if provided
    test_path = sys.argv[1] if len(sys.argv) > 1 else None
    verbosity = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    
    sys.exit(run_tests(test_path, verbosity)) 