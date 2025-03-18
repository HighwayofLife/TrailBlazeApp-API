#!/usr/bin/env python

"""
Debug script to trace URL data through the AERC scraper pipeline.
This is a temporary script for diagnostic purposes.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict

from scrapers.aerc_scraper.parser_v2.html_parser import HTMLParser
from scrapers.aerc_scraper.validator import DataValidator
from scrapers.aerc_scraper.converter import DataConverter

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("debug_script")

class DateTimeEncoder(json.JSONEncoder):
    """JSON encoder that can handle datetime objects."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

def inspect_event_pipeline():
    """Test the AERC scraper pipeline with a sample HTML chunk."""
    # Sample chunk with a calendar row containing links
    sample_html = """
    <div class="calendarRow">
        <span class="rideName">Test Event</span>
        <span class="rideDate">2024-05-15</span>
        <span class="rideLocation">Test Location, CA</span>
        <div class="rideLinks">
            <a href="https://example.com/event">Website</a>
            <a href="https://example.com/flyer.pdf">Flyer</a>
            <a href="https://maps.google.com/location">Map</a>
        </div>
    </div>
    """

    # 1. Parse HTML
    logger.info("Step 1: Parsing HTML")
    parser = HTMLParser(debug_mode=True)
    events_from_html = parser.parse_html(sample_html)
    
    # Print extracted event
    logger.info("HTML Parser output:")
    for i, event in enumerate(events_from_html):
        print(f"\nEvent {i+1} from HTML:")
        print(f"  Name: {event.get('name')}")
        print(f"  Date: {event.get('date_start')}")
        print(f"  Location: {event.get('location')}")
        print(f"  Website: {event.get('website')}")
        print(f"  Flyer URL: {event.get('flyer_url')}")
        print(f"  Map Link: {event.get('map_link')}")
    
    # 2. Validate events
    logger.info("\nStep 2: Validating events")
    validator = DataValidator(debug_mode=True)
    validated_events = validator.validate_events(events_from_html)
    
    # Print validated event
    logger.info("Validator output:")
    for i, event in enumerate(validated_events):
        print(f"\nEvent {i+1} after validation:")
        print(f"  Name: {event.get('name')}")
        print(f"  Date: {event.get('date_start')}")
        print(f"  Location: {event.get('location')}")
        print(f"  Website: {event.get('website')}")
        print(f"  Flyer URL: {event.get('flyer_url')}")
        print(f"  Map Link: {event.get('map_link')}")
    
    # 3. Convert events to database schema
    logger.info("\nStep 3: Converting to database schema")
    converter = DataConverter()
    db_events = converter.convert_to_db_events(validated_events)
    
    # Print converted event
    logger.info("Converter output:")
    for i, event in enumerate(db_events):
        print(f"\nEvent {i+1} after conversion:")
        print(f"  Name: {event.name}")
        print(f"  Date: {event.date_start}")
        print(f"  Location: {event.location}")
        print(f"  Website: {event.website}")
        print(f"  Flyer URL: {event.flyer_url}")
        print(f"  Map Link: {event.map_link}")
        
        # Print full event data for debugging
        print("\nFull event data (fields and values):")
        for field, value in event.model_dump().items():
            print(f"  {field}: {value}")

if __name__ == "__main__":
    inspect_event_pipeline() 