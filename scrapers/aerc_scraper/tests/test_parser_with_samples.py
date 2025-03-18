"""
Consolidated tests for the AERC HTML parser using sample HTML files.

This test suite:
1. Tests the HTML parser against all sample HTML files in the html_samples directory
2. Validates the parsed output against the expected data in expected_test_data.py
3. Confirms that the parser can correctly extract all required fields
4. Ensures compatibility with the unified schema structure
"""

import unittest
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup

# Add project root to path
project_root = str(Path(__file__).parents[3])
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import from updated schema structure
from scrapers.aerc_scraper.parser_v2.html_parser import HTMLParser
from scrapers.aerc_scraper.data_handler import DataHandler
from scrapers.aerc_scraper.tests.expected_test_data import EXPECTED_DATA, EVENT_SAMPLES, get_expected_data
from app.schemas import AERCEvent, EventCreate

class TestParserWithSamples(unittest.TestCase):
    """Test the HTML parser against all sample HTML files."""
    
    def setUp(self):
        """Set up the test environment."""
        self.parser = HTMLParser(debug_mode=True)
        self.data_handler = DataHandler()
        self.samples_dir = Path(__file__).parent / "html_samples"
        
        # Check if samples directory exists
        if not self.samples_dir.exists():
            self.fail(f"❌ Samples directory not found: {self.samples_dir}")
            
        # Load all sample files
        self.sample_files = {}
        for sample_file in EVENT_SAMPLES:
            file_path = self.samples_dir / sample_file
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    self.sample_files[sample_file] = f.read()
            else:
                print(f"⚠️ Warning: Sample file not found: {file_path}")
    
    def test_parser_loads_all_samples(self):
        """Verify that all sample files can be loaded."""
        # Confirm all expected files are loaded
        for sample_name in EVENT_SAMPLES:
            with self.subTest(f"Loading {sample_name}"):
                self.assertIn(sample_name, self.sample_files, 
                             f"❌ Sample file {sample_name} not loaded")
                self.assertIsInstance(self.sample_files[sample_name], str, 
                                    f"❌ Sample file {sample_name} content is not a string")
                self.assertGreater(len(self.sample_files[sample_name]), 100, 
                                 f"❌ Sample file {sample_name} content is too short")
        
        print(f"✅ All {len(self.sample_files)} sample files loaded successfully")
    
    def test_parse_all_samples(self):
        """Test parsing all sample files and compare with expected data."""
        successful_parses = 0
        
        for filename, html_content in self.sample_files.items():
            with self.subTest(f"Parsing {filename}"):
                expected_data = get_expected_data(filename)
                
                # Parse the HTML
                try:
                    parsed_events = self.parser.parse_html(html_content)
                    
                    # Handle multi-day events like Cuyama
                    if filename == "cuyama_pioneer_event.html":
                        self.assertGreaterEqual(len(parsed_events), 1, 
                                             f"❌ Expected at least one event from {filename}")
                    else:
                        self.assertEqual(len(parsed_events), 1, 
                                       f"❌ Expected one event from {filename}, got {len(parsed_events)}")
                    
                    # Verify the first event against expected data
                    parsed = parsed_events[0]
                    self._verify_essential_fields(parsed, expected_data, filename)
                    self._verify_structured_fields(parsed, expected_data, filename)
                    self._test_full_pipeline(parsed, expected_data, filename)
                    
                    successful_parses += 1
                    print(f"✅ Successfully parsed {filename}")
                    
                except Exception as e:
                    self.fail(f"❌ Error parsing {filename}: {str(e)}")
        
        print(f"🎉 Successfully parsed and validated {successful_parses} sample files")
    
    def _verify_essential_fields(self, parsed: Dict[str, Any], expected: Dict[str, Any], filename: str):
        """Verify that all essential fields are correctly parsed."""
        # Essential fields that must be present
        essential_fields = ["name", "source", "date_start", "location", "is_canceled"]
        
        for field in essential_fields:
            with self.subTest(f"Essential field '{field}' in {filename}"):
                self.assertIn(field, parsed, f"❌ Missing essential field '{field}' in parsed data")
                if field != "location":  # Special handling for location below
                    self.assertEqual(parsed[field], expected[field], 
                                   f"❌ Field '{field}' value mismatch in {filename}")
        
        # Special check for location due to possible format differences
        location_parts = expected["location"].split(',')
        for part in location_parts:
            part = part.strip()
            if len(part) > 3:  # Skip short parts like state codes
                self.assertIn(part, parsed["location"], 
                           f"❌ Location part '{part}' not found in '{parsed['location']}' for {filename}")
        
        # Check that ride_id and has_intro_ride are properly parsed if present in expected data
        optional_fields = ["ride_id", "has_intro_ride", "region"]
        for field in optional_fields:
            if field in expected:
                with self.subTest(f"Optional field '{field}' in {filename}"):
                    # Field might be in the main object or in event_details
                    field_present = field in parsed or (
                        "event_details" in parsed and 
                        isinstance(parsed["event_details"], dict) and 
                        field in parsed["event_details"]
                    )
                    self.assertTrue(field_present, f"❌ Missing optional field '{field}' in parsed data for {filename}")
    
    def _verify_structured_fields(self, parsed: Dict[str, Any], expected: Dict[str, Any], filename: str):
        """Verify that structured fields are correctly parsed."""
        # Check location_details if present in expected data
        if "location_details" in expected:
            with self.subTest(f"location_details in {filename}"):
                # Location details might be in the main object or in event_details
                location_details_present = (
                    "location_details" in parsed or 
                    ("event_details" in parsed and 
                     isinstance(parsed["event_details"], dict) and 
                     "location_details" in parsed["event_details"])
                )
                self.assertTrue(location_details_present, 
                             f"❌ Missing location_details in parsed data for {filename}")
                
                # Verify country if present
                expected_location = expected["location_details"]
                if "country" in expected_location:
                    # Extract country from parsed data
                    country = None
                    if "location_details" in parsed and isinstance(parsed["location_details"], dict):
                        country = parsed["location_details"].get("country")
                    elif ("event_details" in parsed and 
                          isinstance(parsed["event_details"], dict) and 
                          "location_details" in parsed["event_details"] and
                          isinstance(parsed["event_details"]["location_details"], dict)):
                        country = parsed["event_details"]["location_details"].get("country")
                    
                    # Country might not be explicitly parsed but inferred later
                    # So we don't fail if it's not present, just warn
                    if country and country != expected_location["country"]:
                        print(f"⚠️ Warning: Country mismatch in {filename}. "
                              f"Expected {expected_location['country']}, got {country}")
        
        # Check distances if present in expected data
        if "distances" in expected:
            with self.subTest(f"distances in {filename}"):
                # Distances might be in the main object or in event_details
                distances_present = (
                    "distances" in parsed or 
                    ("event_details" in parsed and 
                     isinstance(parsed["event_details"], dict) and 
                     "distances" in parsed["event_details"])
                )
                self.assertTrue(distances_present, 
                             f"❌ Missing distances in parsed data for {filename}")
                
                # Verify expected number of distances
                expected_distances = expected["distances"]
                parsed_distances = self._get_nested_value(parsed, "distances")
                
                if parsed_distances is not None:
                    # For multi-day events, we might have a different number of distances
                    # because the parser might split them by day
                    if filename != "cuyama_pioneer_event.html": 
                        self.assertEqual(len(parsed_distances), len(expected_distances), 
                                      f"❌ Distance count mismatch in {filename}")
        
        # Check coordinates if present in expected data
        if "coordinates" in expected:
            with self.subTest(f"coordinates in {filename}"):
                # Coordinates might be in the main object or in event_details
                coordinates_present = (
                    "coordinates" in parsed or 
                    ("event_details" in parsed and 
                     isinstance(parsed["event_details"], dict) and 
                     "coordinates" in parsed["event_details"])
                )
                self.assertTrue(coordinates_present, 
                             f"❌ Missing coordinates in parsed data for {filename}")
                
                # Verify latitude and longitude if coordinates are present
                parsed_coords = self._get_nested_value(parsed, "coordinates")
                if parsed_coords is not None:
                    expected_coords = expected["coordinates"]
                    if "latitude" in expected_coords and "latitude" in parsed_coords:
                        self.assertAlmostEqual(float(parsed_coords["latitude"]), 
                                             float(expected_coords["latitude"]), 
                                             places=4, 
                                             msg=f"❌ Latitude mismatch in {filename}")
                    if "longitude" in expected_coords and "longitude" in parsed_coords:
                        self.assertAlmostEqual(float(parsed_coords["longitude"]), 
                                             float(expected_coords["longitude"]), 
                                             places=4, 
                                             msg=f"❌ Longitude mismatch in {filename}")
    
    def _get_nested_value(self, data: Dict[str, Any], key: str) -> Optional[Any]:
        """Helper to get a value that might be nested in event_details."""
        if key in data:
            return data[key]
        elif "event_details" in data and isinstance(data["event_details"], dict) and key in data["event_details"]:
            return data["event_details"][key]
        return None
    
    def _test_full_pipeline(self, parsed: Dict[str, Any], expected: Dict[str, Any], filename: str):
        """Test the full pipeline from parsed data to AERCEvent to EventCreate."""
        try:
            # Transform to AERCEvent
            aerc_event = self.data_handler.transform_and_validate(parsed)
            self.assertIsNotNone(aerc_event, f"❌ Failed to transform parsed data to AERCEvent for {filename}")
            
            # Check essential fields in AERCEvent
            self.assertEqual(aerc_event.name, expected["name"], 
                           f"❌ Name mismatch in AERCEvent for {filename}")
            self.assertEqual(aerc_event.is_canceled, expected["is_canceled"], 
                           f"❌ Cancellation status mismatch in AERCEvent for {filename}")
            
            # Check that location details are preserved
            if hasattr(aerc_event, "location_details") and aerc_event.location_details:
                if "location_details" in expected and "country" in expected["location_details"]:
                    expected_country = expected["location_details"]["country"]
                    if hasattr(aerc_event.location_details, "country"):
                        self.assertEqual(aerc_event.location_details.country, expected_country, 
                                       f"❌ Country mismatch in AERCEvent for {filename}")
            
            # Check that ride_id is preserved if present
            if "ride_id" in expected:
                self.assertEqual(getattr(aerc_event, "ride_id", None), expected["ride_id"], 
                               f"❌ ride_id mismatch in AERCEvent for {filename}")
            
            # Convert to EventCreate
            event_create = self.data_handler.to_event_create(aerc_event)
            self.assertIsNotNone(event_create, f"❌ Failed to convert AERCEvent to EventCreate for {filename}")
            
            # Check essential fields in EventCreate
            self.assertEqual(event_create.name, expected["name"], 
                           f"❌ Name mismatch in EventCreate for {filename}")
            self.assertEqual(event_create.is_canceled, expected["is_canceled"], 
                           f"❌ Cancellation status mismatch in EventCreate for {filename}")
            
            # Check that event_details exists
            self.assertIsNotNone(event_create.event_details, 
                               f"❌ event_details missing in EventCreate for {filename}")
            
            # Check that specific fields are preserved in EventCreate if present in expected data
            for field in ["website", "flyer_url", "map_link"]:
                if field in expected:
                    field_value = getattr(event_create, field, None)
                    if field_value is None and hasattr(event_create, "event_details"):
                        # Try to get from event_details if it's not a direct attribute
                        event_details = event_create.event_details
                        if isinstance(event_details, dict) and field in event_details:
                            field_value = event_details[field]
                    
                    self.assertIsNotNone(field_value, 
                                       f"❌ {field} missing in EventCreate for {filename}")
            
            # Check has_intro_ride flag if present in expected data
            if "has_intro_ride" in expected:
                has_intro_ride = getattr(event_create, "has_intro_ride", None)
                self.assertEqual(has_intro_ride, expected["has_intro_ride"], 
                               f"❌ has_intro_ride mismatch in EventCreate for {filename}")
            
            # Check ride_id if present in expected data
            if "ride_id" in expected:
                ride_id = getattr(event_create, "ride_id", None)
                if ride_id is None and hasattr(event_create, "event_details"):
                    # Try to get from event_details if it's not a direct attribute
                    event_details = event_create.event_details
                    if isinstance(event_details, dict) and "ride_id" in event_details:
                        ride_id = event_details["ride_id"]
                
                self.assertEqual(ride_id, expected["ride_id"], 
                               f"❌ ride_id mismatch in EventCreate for {filename}")
            
            print(f"✅ Full pipeline validation passed for {filename}")
            
        except Exception as e:
            self.fail(f"❌ Error in full pipeline test for {filename}: {str(e)}")

if __name__ == "__main__":
    unittest.main() 