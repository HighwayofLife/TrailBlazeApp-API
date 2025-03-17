#!/usr/bin/env python3
"""
Run tests sequentially to avoid event loop issues.

This script runs each test in the test_events.py file one by one
to avoid issues with the event loop when running multiple tests.
"""
import subprocess
import sys
import os

def run_test(test_name):
    """Run a specific test using make test-dev."""
    print(f"\n\n{'='*80}")
    print(f"Running test: {test_name}")
    print(f"{'='*80}\n")
    
    cmd = f"make test-dev PYTEST_ARGS=\"-xvs tests/api/test_events.py::{test_name}\""
    result = subprocess.run(cmd, shell=True)
    
    if result.returncode != 0:
        print(f"\n\nTest {test_name} FAILED with exit code {result.returncode}")
        return False
    else:
        print(f"\n\nTest {test_name} PASSED")
        return True

def main():
    """Run all tests in test_events.py sequentially."""
    tests = [
        "test_read_events",
        "test_create_event",
        "test_read_event",
        "test_update_event",
        "test_delete_event"
    ]
    
    failed_tests = []
    
    for test in tests:
        if not run_test(test):
            failed_tests.append(test)
    
    print("\n\n")
    print(f"{'='*80}")
    print("Test Summary")
    print(f"{'='*80}")
    print(f"Total tests: {len(tests)}")
    print(f"Passed: {len(tests) - len(failed_tests)}")
    print(f"Failed: {len(failed_tests)}")
    
    if failed_tests:
        print("\nFailed tests:")
        for test in failed_tests:
            print(f"  - {test}")
        return 1
    else:
        print("\nAll tests passed!")
        return 0

if __name__ == "__main__":
    sys.exit(main()) 