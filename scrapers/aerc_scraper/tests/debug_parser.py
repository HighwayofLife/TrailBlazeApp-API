#!/usr/bin/env python
"""
Debug script to help diagnose parsing issues in the HTML parser.
"""

import os
import sys
from pathlib import Path
import traceback
import json
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from datetime import datetime

# Add project root to path
project_root = str(Path(__file__).parents[3])
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the parser
from scrapers.aerc_scraper.parser_v2.html_parser import HTMLParser

def pretty_print(data):
    """Print data in a readable format."""
    print(json.dumps(data, indent=2, default=str))

def debug_parser(html_file: str):
    """
    Debug the full parsing process.
    
    Args:
        html_file: Path to the HTML file to parse
    """
    print(f"Debugging parser for {html_file}")
    
    # Load the sample HTML
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Create parser instance with debug mode enabled
    parser = HTMLParser(debug_mode=True)
    
    try:
        # First test the date extraction for each row
        soup = BeautifulSoup(html_content, 'html.parser')
        rows = soup.select('div.calendarRow')
        
        print(f"Found {len(rows)} calendar rows")
        
        # Track all extracted events for combining later
        raw_events = []
        
        for i, row in enumerate(rows):
            print(f"\n--- Row {i+1} ---")
            
            # Extract ride name
            name_elem = row.select_one('span.rideName')
            if name_elem:
                print(f"Name: {name_elem.text.strip()}")
                if name_elem.has_attr('tag'):
                    print(f"Ride ID: {name_elem['tag']}")
            
            # Extract date
            date_str = parser._extract_date(row)
            print(f"Date: {date_str}")
            
            # Now try to extract the full event data
            try:
                event_data = parser._extract_event_data(row, i)
                if event_data:
                    print("Extracted event data successfully")
                    raw_events.append(event_data)
                else:
                    print("Failed to extract event data")
            except Exception as e:
                print(f"Error extracting event data: {e}")
                traceback.print_exc()
                
        print("\n=== Raw Events ===")
        for i, event in enumerate(raw_events):
            print(f"\nEvent {i+1}:")
            pretty_print(event)
        
        # Now try to combine events with the same ride_id
        print("\n=== Combining Events ===")
        try:
            combined_events = parser._combine_events_with_same_ride_id(raw_events)
            print(f"Combined into {len(combined_events)} events")
            
            for i, event in enumerate(combined_events):
                print(f"\nCombined Event {i+1}:")
                pretty_print(event)
                
        except Exception as e:
            print(f"Error combining events: {e}")
            traceback.print_exc()
        
        # Finally try the full parsing flow
        print("\n=== Full Parsing Flow ===")
        try:
            parsed_events = parser.parse_html(html_content)
            print(f"Parsed {len(parsed_events)} events from full flow")
            
            for i, event in enumerate(parsed_events):
                print(f"\nParsed Event {i+1}:")
                pretty_print(event)
                
        except Exception as e:
            print(f"Error in full parsing flow: {e}")
            traceback.print_exc()
    
    except Exception as e:
        print(f"Error parsing HTML: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    # Get the sample files directory
    samples_dir = os.path.join(os.path.dirname(__file__), 'html_samples')
    
    # Debug a specific file
    if len(sys.argv) > 1:
        file_name = sys.argv[1]
        file_path = os.path.join(samples_dir, file_name)
        if os.path.exists(file_path):
            debug_parser(file_path)
        else:
            print(f"File not found: {file_path}")
    else:
        # Default to debugging the multi-day event
        file_path = os.path.join(samples_dir, "cuyama_pioneer_event.html")
        if os.path.exists(file_path):
            debug_parser(file_path)
        else:
            print(f"Default file not found: {file_path}") 