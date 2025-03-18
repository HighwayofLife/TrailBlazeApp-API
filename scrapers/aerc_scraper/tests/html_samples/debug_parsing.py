#!/usr/bin/env python
"""
Debug script to test location parsing from the data_handler.
"""

import sys
from pathlib import Path
import json

# Add project root to path
project_root = str(Path(__file__).parents[4])
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scrapers.aerc_scraper.data_handler import DataHandler

# Test cases
test_locations = [
    "Empire Ranch, Empire Ranch Rd, Sonoita, AZ 85637",
    "Biltmore Equestrian Center, 1 Biltmore Estate Dr., Asheville NC 28803",
    "Robie Park, Truckee, CA to Auburn, CA",
    "Belair Provincial Forest, Hwy 44 at Hwy 302, Stead MB"
]

def test_location_parsing():
    """Test the location parsing function with various inputs."""
    print("Testing DataHandler._parse_location...")
    
    for i, location in enumerate(test_locations):
        parts = DataHandler._parse_location(location)
        print(f"\nTest {i+1}: {location}")
        print(f"  Name: {parts.get('name')}")
        print(f"  City: {parts.get('city')}")
        print(f"  State: {parts.get('state')}")
        
        # Build the location string back using the parsed parts
        location_str = parts.get('name', '')
        if parts.get('city'):
            if location_str:
                location_str += f", {parts.get('city')}"
            else:
                location_str = parts.get('city')
                
        if parts.get('state'):
            location_str += f", {parts.get('state')}"
        
        print(f"  Formatted: {location_str}")
        print(f"  Matches original: {location_str == location}")

if __name__ == "__main__":
    test_location_parsing() 