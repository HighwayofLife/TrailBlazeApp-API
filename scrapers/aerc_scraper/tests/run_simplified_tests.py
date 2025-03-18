#!/usr/bin/env python
"""
Simple runner for the simplified HTML to Database tests.
"""

import sys
import pytest
from pathlib import Path

# Add parent directory to path to ensure imports work
parent_dir = str(Path(__file__).parents[3])
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

if __name__ == "__main__":
    print("\n===== Running Simplified AERC HTML to Database Tests =====\n")
    
    # Get the path to the test file
    test_file = "test_html_to_database_integration_simplified.py"
    test_path = str(Path(__file__).parent / test_file)
    
    # Run tests with pytest
    sys.exit(pytest.main([test_path, "-v"])) 