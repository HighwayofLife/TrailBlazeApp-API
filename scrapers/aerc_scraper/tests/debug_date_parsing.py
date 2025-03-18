#!/usr/bin/env python
"""
Debug script to help diagnose date parsing issues in the HTML parser.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from datetime import datetime

# Add project root to path
project_root = str(Path(__file__).parents[3])
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the parser
from scrapers.aerc_scraper.parser_v2.html_parser import HTMLParser

def debug_extract_date(html_file: str):
    """
    Debug the date extraction functionality.
    
    Args:
        html_file: Path to the HTML file to parse
    """
    print(f"Debugging date extraction for {html_file}")
    
    # Load the sample HTML
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Create parser instance
    parser = HTMLParser(debug_mode=True)
    
    # Parse the HTML
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        # Find all ride rows
        rows = soup.select('div.calendarRow')
        
        print(f"Found {len(rows)} calendar rows")
        
        for i, row in enumerate(rows):
            print(f"\nRow {i+1}:")
            
            # Extract date elements
            date_elem = row.select_one('span.rideDate')
            if date_elem:
                print(f"  span.rideDate: {date_elem.text.strip()}")
            else:
                print("  No span.rideDate found")
                
            # Try fallback date extraction
            date_cell = row.select_one('td.bold')
            if date_cell:
                print(f"  td.bold: {date_cell.text.strip()}")
            else:
                print("  No td.bold found")
            
            # Try to extract the date using the parser's method
            date_str = parser._extract_date(row)
            print(f"  Extracted date: {date_str}")
            
            # If date was extracted, try to parse it as a datetime object
            if date_str:
                try:
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    print(f"  Parsed date: {date_obj.isoformat()}")
                except ValueError as e:
                    print(f"  Error parsing date: {e}")
    
    except Exception as e:
        print(f"Error parsing HTML: {e}")

if __name__ == "__main__":
    # Get the sample files directory
    samples_dir = os.path.join(os.path.dirname(__file__), 'html_samples')
    
    # Debug all sample files or a specific one
    if len(sys.argv) > 1:
        # Debug a specific file
        file_path = os.path.join(samples_dir, sys.argv[1])
        if os.path.exists(file_path):
            debug_extract_date(file_path)
        else:
            print(f"File not found: {file_path}")
    else:
        # Debug all sample files
        for filename in os.listdir(samples_dir):
            if filename.endswith('.html'):
                file_path = os.path.join(samples_dir, filename)
                debug_extract_date(file_path)
                print("\n" + "-" * 80 + "\n") 