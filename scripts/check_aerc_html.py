#!/usr/bin/env python
"""
Script to fetch and examine the AERC HTML structure
"""

import asyncio
import logging
from bs4 import BeautifulSoup

from scrapers.aerc_scraper.network import NetworkHandler
from scrapers.aerc_scraper.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("check_aerc_html")

async def main():
    """Fetch and examine the AERC HTML"""
    logger.info("Fetching AERC calendar HTML")
    
    # Get settings and create network handler
    settings = get_settings()
    handler = NetworkHandler(settings)
    
    # Fetch the HTML
    html = await handler.fetch_calendar()
    logger.info(f"Got HTML content of size: {len(html)} bytes")
    
    # Parse with BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    
    # Find a few calendar rows to examine their structure
    ride_rows = soup.find_all('div', class_='calendarRow')
    logger.info(f"Found {len(ride_rows)} calendar rows")
    
    # Examine the first 3 rows in detail
    for i, row in enumerate(ride_rows[:3]):
        logger.info(f"\n--- Row {i+1} Structure ---")
        
        # Get ride name
        name_elem = row.select_one('span.rideName')
        name = name_elem.text.strip() if name_elem else "Unknown"
        logger.info(f"Ride Name: {name}")
        
        # Get ride ID if available
        ride_id = None
        if name_elem and name_elem.has_attr('tag'):
            ride_id = name_elem['tag']
            logger.info(f"Ride ID: {ride_id}")
        
        # Check for title attributes on the row and name element
        if row.has_attr('title'):
            logger.info(f"Row title: {row['title']}")
        
        if name_elem and name_elem.has_attr('title'):
            logger.info(f"Name elem title: {name_elem['title']}")
        
        # Get location info
        location_elem = row.select_one('td.rideLocation')
        if location_elem:
            logger.info(f"Location text: '{location_elem.text.strip()}'")
            # Print the HTML of the location element to see its structure
            logger.info(f"Location HTML: {location_elem}")
        else:
            logger.info("No location element found")
        
        # Check all elements with title attributes in the row
        title_elems = row.select('[title]')
        for j, elem in enumerate(title_elems):
            logger.info(f"Element {j+1} with title: '{elem['title']}'")
            logger.info(f"  Tag: {elem.name}")
            logger.info(f"  Text: '{elem.text.strip()}'")
        
        # Display the HTML of the entire row for inspection
        logger.info(f"Full row HTML:\n{row}")
        
    # Print a summary
    logger.info(f"\nTotal rows: {len(ride_rows)}")
    
    # Count how many rows have title attributes
    rows_with_title = sum(1 for row in ride_rows if row.has_attr('title'))
    logger.info(f"Rows with title attribute: {rows_with_title}")
    
    # Count how many ride name elements have title attributes
    name_elems_with_title = sum(1 for row in ride_rows 
                              if row.select_one('span.rideName') and 
                              row.select_one('span.rideName').has_attr('title'))
    logger.info(f"Ride name elements with title attribute: {name_elems_with_title}")

if __name__ == "__main__":
    asyncio.run(main()) 