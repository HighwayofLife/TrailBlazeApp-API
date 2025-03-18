"""
Comprehensive integration test for the AERC scraper.

This test validates the entire flow from HTML parsing to database insertion and verification:
1. Parse HTML files from samples
2. Transform raw data to structured data
3. Insert data into database
4. Validate that database content matches expected data
"""

import sys
import os
import asyncio
import pytest
from pathlib import Path
from typing import Dict, Any, List, Optional
from unittest.mock import patch, MagicMock, AsyncMock

# Add project root to path
project_root = str(Path(__file__).parents[3])
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the components we need to test
from scrapers.aerc_scraper.parser_v2.html_parser import HTMLParser
from scrapers.aerc_scraper.data_handler import DataHandler
from scrapers.aerc_scraper.database import DatabaseHandler
from app.schemas.event import EventCreate
from scrapers.aerc_scraper.tests.expected_test_data import EXPECTED_DATA, EVENT_SAMPLES

# Import app models and schemas
from app.models.event import Event as DBEvent

# Path to HTML samples
HTML_SAMPLES_DIR = Path(__file__).parent / "html_samples"

def load_html_sample(filename: str) -> str:
    """Load HTML sample from a file."""
    file_path = HTML_SAMPLES_DIR / filename
    if not file_path.exists():
        raise FileNotFoundError(f"Sample file not found: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

@pytest.fixture
def parser():
    """Return an instance of the HTML parser."""
    return HTMLParser(debug_mode=True)

@pytest.fixture
def data_handler():
    """Return an instance of the data handler."""
    return DataHandler()

@pytest.fixture
def db_handler():
    """Return an instance of the database handler."""
    return DatabaseHandler()

@pytest.fixture
def mock_db():
    """Create a mock database."""
    mock_db = AsyncMock()
    
    # Add execute method to mock database
    async def mock_execute(query):
        mock_result = AsyncMock()
        mock_result.scalar.return_value = 1
        mock_result.all.return_value = []
        return mock_result
    
    mock_db.execute = mock_execute
    mock_db.commit = AsyncMock()
    
    return mock_db

@pytest.fixture
def html_samples():
    """Load all HTML samples."""
    samples = {}
    for filename in EVENT_SAMPLES:
        samples[filename] = load_html_sample(filename)
    return samples

@pytest.fixture
def stored_events():
    """Track events that get stored in the database."""
    return {}

@pytest.mark.parametrize("mock_get_events,mock_create_event", [
    (
        AsyncMock(return_value=[]),  # No existing events
        None  # Will be created in the function
    )
], indirect=False)
@pytest.mark.asyncio
async def test_html_to_database_pipeline(parser, data_handler, db_handler, mock_db, html_samples, stored_events, mock_get_events, mock_create_event):
    """
    Test the complete HTML to database pipeline.
    
    This test verifies:
    1. HTML parsing works correctly
    2. Data transformation preserves all required fields
    3. Database storage operations work as expected
    4. Stored data matches the expected reference data
    """
    # Configure capture_event to store events being created
    if mock_create_event is None:
        async def capture_event(db, event_create, perform_geocoding=True):
            # Convert to dict for easier assertions
            event_dict = event_create.model_dump(exclude_unset=True)
            
            # Create a mock DB object with ID and data from the event
            mock_evt = MagicMock(spec=DBEvent)
            mock_evt.id = len(stored_events) + 1
            mock_evt.name = event_dict["name"]
            
            # Store the event with its name as key for later verification
            stored_events[event_dict["name"]] = event_dict
            
            # Copy all attributes to the mock object for return
            for field, value in event_dict.items():
                setattr(mock_evt, field, value)
            
            return mock_evt
        
        mock_create_event = AsyncMock(side_effect=capture_event)
    
    # Apply patches to the CRUD functions
    with patch("app.crud.event.get_events", mock_get_events), \
         patch("app.crud.event.create_event", mock_create_event):
    
        # Process each HTML sample
        processed_samples = 0
        for filename, html_content in html_samples.items():
            expected_data = EXPECTED_DATA[filename]
            
            print(f"\nProcessing sample: {filename}")
            
            # STEP 1: Parse HTML
            raw_events = parser.parse_html(html_content)
            assert len(raw_events) > 0, f"Failed to parse any events from {filename}"
            raw_event = raw_events[0]
            
            print(f"✅ Parsed HTML for: {raw_event.get('name', 'Unknown Event')}")
            
            # STEP 2: Transform to structured data
            aerc_event = data_handler.transform_and_validate(raw_event)
            assert aerc_event is not None, f"Failed to transform event data for {filename}"
            
            print(f"✅ Transformed data for: {aerc_event.name}")
            
            # STEP 3: Convert to database model
            event_create = data_handler.to_event_create(aerc_event)
            assert event_create is not None, f"Failed to create database model for {filename}"
            
            print(f"✅ Created database model for: {event_create.name}")
            
            # STEP 4: Store in database
            result = await db_handler.store_events([event_create], mock_db)
            assert result.get("added", 0) == 1, f"Failed to add event from {filename} to database"
            
            print(f"✅ Stored in database with result: {result}")
            
            processed_samples += 1
        
        assert processed_samples == len(EVENT_SAMPLES), "Not all samples were processed"
        print(f"\nAll {processed_samples} samples were successfully processed!")
        
        # STEP 5: Verify the stored data against expected data
        for filename, expected in EXPECTED_DATA.items():
            event_name = expected["name"]
            
            # Check if the event was stored
            assert event_name in stored_events, f"Event {event_name} was not stored in the database"
            
            stored_event = stored_events[event_name]
            
            # Validate core fields
            assert stored_event["name"] == expected["name"], "Event name mismatch"
            assert stored_event["source"] == expected["source"], "Event source mismatch"
            assert stored_event["event_type"] == expected["event_type"], "Event type mismatch"
            
            # Date may be stored in different formats, so normalize for comparison
            if isinstance(stored_event["date_start"], str):
                stored_date = stored_event["date_start"].split("T")[0]  # ISO format
            else:
                # If it's a datetime object
                stored_date = stored_event["date_start"].strftime("%Y-%m-%d")
            
            assert stored_date == expected["date_start"], "Event date mismatch"
            assert stored_event["location"] == expected["location"], "Event location mismatch"
            assert stored_event["region"] == expected["region"], "Event region mismatch"
            assert stored_event["is_canceled"] == expected["is_canceled"], "Event cancellation status mismatch"
            
            # Validate manager information
            assert stored_event.get("ride_manager") == expected["ride_manager"], "Ride manager mismatch"
            assert stored_event.get("manager_phone") == expected["manager_phone"], "Manager phone mismatch"
            assert stored_event.get("manager_email") == expected["manager_email"], "Manager email mismatch"
            
            # Validate URLs if present
            if "website" in expected:
                assert stored_event.get("website") == expected["website"], "Website URL mismatch"
            if "flyer_url" in expected:
                assert stored_event.get("flyer_url") == expected["flyer_url"], "Flyer URL mismatch"
            
            # Validate event_details contents
            assert "event_details" in stored_event, "Event details missing"
            event_details = stored_event["event_details"]
            
            # Location details
            if "location_details" in expected:
                assert "location_details" in event_details, "Location details missing"
                location_details = event_details["location_details"]
                expected_location = expected["location_details"]
                
                assert location_details.get("city") == expected_location.get("city"), "City mismatch"
                assert location_details.get("state") == expected_location.get("state"), "State mismatch"
                assert location_details.get("country") == expected_location.get("country"), "Country mismatch"
            
            # Check coordinates if expected
            if "coordinates" in expected:
                assert "coordinates" in event_details, "Coordinates missing"
                coords = event_details["coordinates"]
                expected_coords = expected["coordinates"]
                
                assert coords.get("latitude") == expected_coords.get("latitude"), "Latitude mismatch"
                assert coords.get("longitude") == expected_coords.get("longitude"), "Longitude mismatch"
            
            # Check map link if expected
            if "map_link" in expected:
                assert "map_link" in event_details, "Map link missing"
                assert event_details["map_link"] == expected["map_link"], "Map link mismatch"
            
            # Check has_intro_ride flag
            assert event_details.get("has_intro_ride") == expected["has_intro_ride"], "Intro ride flag mismatch"
            
            # Check pioneer ride flag
            assert event_details.get("is_pioneer_ride") == expected["is_pioneer_ride"], "Pioneer ride flag mismatch"
            
            # Check multi-day event flag
            assert event_details.get("is_multi_day_event") == expected["is_multi_day_event"], "Multi-day event flag mismatch"
            
            # Check ride days count
            assert event_details.get("ride_days") == expected["ride_days"], "Ride days count mismatch"
            
            # Check control judges if expected
            if "control_judges" in expected:
                assert "control_judges" in event_details, "Control judges missing"
                judges = event_details["control_judges"]
                expected_judges = expected["control_judges"]
                
                assert len(judges) == len(expected_judges), "Control judge count mismatch"
                for i, judge in enumerate(expected_judges):
                    assert judges[i]["name"] == judge["name"], f"Judge name mismatch for judge {i}"
                    assert judges[i]["role"] == judge["role"], f"Judge role mismatch for judge {i}"
            
            # Check distances
            if "distances" in expected:
                assert "distances" in event_details, "Distances missing"
                distances = event_details["distances"]
                expected_distances = expected["distances"]
                
                assert len(distances) == len(expected_distances), "Distance count mismatch"
                for i, distance in enumerate(expected_distances):
                    assert distances[i]["distance"] == distance["distance"], f"Distance mismatch for entry {i}"
                    assert distances[i]["date"] == distance["date"], f"Date mismatch for distance entry {i}"
                    assert distances[i]["start_time"] == distance["start_time"], f"Start time mismatch for distance entry {i}"
            
            # Check description fields if expected
            if "description" in expected:
                assert "description" in event_details, "Description missing"
                assert event_details["description"] == expected["description"], "Description mismatch"
            
            if "directions" in expected:
                assert "directions" in event_details, "Directions missing"
                assert event_details["directions"] == expected["directions"], "Directions mismatch"
            
            print(f"✅ Validated {event_name} successfully!")
            
        print("\nAll events have been successfully validated against expected data!")

@pytest.mark.parametrize("mock_get_events,mock_update_event", [
    (
        # Mock for an existing event in database
        AsyncMock(return_value=[
            MagicMock(
                spec=DBEvent,
                id=999,
                name="Original Old Pueblo",
                location="Tucson, AZ", 
                is_canceled=False
            )
        ]),
        None  # Will be created in the test
    )
], indirect=False)
@pytest.mark.asyncio
async def test_html_to_database_with_existing_events(parser, data_handler, db_handler, mock_db, html_samples, stored_events, mock_get_events, mock_update_event):
    """Test the database handler with existing events."""
    # Setup mock for update_event to capture updates
    if mock_update_event is None:
        async def capture_update(db, event_id, event_update, perform_geocoding=True):
            # Store the update for verification
            event_dict = event_update.model_dump(exclude_unset=True)
            stored_events[event_update.name] = event_dict
            
            # Return a properly mocked updated event
            mock_updated = MagicMock(spec=DBEvent)
            mock_updated.id = event_id
            mock_updated.name = event_update.name
            return mock_updated
            
        mock_update_event = AsyncMock(side_effect=capture_update)
    
    # Apply patches to the CRUD functions
    with patch("app.crud.event.get_events", mock_get_events), \
         patch("app.crud.event.create_event", AsyncMock()), \
         patch("app.crud.event.update_event", mock_update_event):
    
        # We'll test with the Old Pueblo event
        filename = "old_pueblo_event.html"
        html_content = html_samples[filename]
        
        # Parse HTML to get the event data
        raw_events = parser.parse_html(html_content)
        assert len(raw_events) > 0
        raw_event = raw_events[0]
        
        # Transform the data
        aerc_event = data_handler.transform_and_validate(raw_event)
        assert aerc_event is not None
        
        # Convert to database model
        event_create = data_handler.to_event_create(aerc_event)
        assert event_create is not None
        
        # Store in database - should update, not add
        result = await db_handler.store_events([event_create], mock_db)
        assert result.get("updated", 0) == 1, "Event should have been updated, not added"
        assert result.get("added", 0) == 0, "Event should not have been added as new"
        
        # Verify the stored data
        event_name = event_create.name
        assert event_name in stored_events, f"Event {event_name} was not stored/updated" 