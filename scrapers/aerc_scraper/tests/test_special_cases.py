"""
Unit tests for special cases in HTML parsing.
Tests extraction of flyer links, cancelled events, and coordinates extraction.
"""

import unittest
import sys
import os
from pathlib import Path
import json

# Add project root to path
project_root = str(Path(__file__).parents[3])
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scrapers.aerc_scraper.parser_v2.html_parser import HTMLParser
from scrapers.aerc_scraper.data_handler import DataHandler

# Import HTML samples
HTML_SAMPLES_DIR = Path(__file__).parent / "html_samples"

# Load sample HTML from files
def load_html_sample(filename):
    """Load HTML sample from a file."""
    file_path = HTML_SAMPLES_DIR / filename
    if not file_path.exists():
        raise FileNotFoundError(f"Sample file not found: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

# Create directory if it doesn't exist
if not HTML_SAMPLES_DIR.exists():
    HTML_SAMPLES_DIR.mkdir(parents=True)

# Load the HTML samples
FLYER_EVENT_HTML = load_html_sample("old_pueblo_event.html")
CANCELLED_EVENT_HTML = load_html_sample("biltmore_cancelled_event.html")
MAP_EVENT_HTML = load_html_sample("tevis_cup_event.html")
BELAIR_EVENT_HTML = load_html_sample("belair_forest_event.html")

# Expected data structures for each HTML sample
FLYER_EVENT_EXPECTED = {
    'name': 'Original Old Pueblo',
    'region': 'SW',
    'date_start': '2025-03-28',
    'location': 'Empire Ranch, Empire Ranch Rd, Sonoita, AZ 85637',
    'has_intro_ride': True,
    'flyer_url': 'https://aerc.org/wp-content/uploads/2025/02/2025OldPueblo.pdf',
    'ride_manager': 'Marilyn McCoy',
    'ride_manager_contact': {
        'phone': '520-360-9445',
        'email': 'marilynmccoy@hotmail.com'
    },
    'distances': [
        {'distance': '50', 'start_time': '07:00 am'},
        {'distance': '25', 'start_time': '08:00 am'},
        {'distance': '10', 'start_time': '09:00 am'}
    ],
    'control_judges': [
        {'name': 'Larry Nolen', 'role': 'Control Judge'},
    ],
    'is_canceled': False
}

CANCELLED_EVENT_EXPECTED = {
    'name': 'Biltmore Open Challenge I',
    'region': 'SE',
    'date_start': '2025-05-02',
    'location': 'Biltmore Equestrian Center, 1 Biltmore Estate Dr., Asheville NC 28803',
    'has_intro_ride': False,
    'ride_manager': 'Cheryl Newman',
    'ride_manager_contact': {
        'phone': '828-665-1531',
        'email': 'cherylnewman@charter.net'
    },
    'distances': [
        {'distance': '50', 'start_time': '07:30 am'},
        {'distance': '25', 'start_time': '08:30 am'}
    ],
    'control_judges': [
        {'name': 'Nick Kohut', 'role': 'Control Judge'}
    ],
    'is_canceled': True
}

MAP_EVENT_EXPECTED = {
    'name': 'Western States Trail Ride (The Tevis Cup)',
    'region': 'W',
    'date_start': '2025-07-12',
    'location': 'Robie Park, Truckee, CA to Auburn, CA',
    'has_intro_ride': False,
    'ride_manager': 'Chuck Stalley',
    'ride_manager_contact': {
        'phone': '530-823-7616',
        'email': 'cstalley@saber.net'
    },
    'distances': [
        {'distance': '100', 'start_time': '05:15 am'}
    ],
    'control_judges': [
        {'name': 'Michael S. Peralez', 'role': 'Control Judge'}
    ],
    'website': 'https://www.teviscup.org',
    'map_link': 'https://www.google.com/maps/dir/?api=1&destination=39.23839,-120.17357',
    'coordinates': {
        'latitude': 39.23839,
        'longitude': -120.17357
    },
    'is_canceled': False
}

BELAIR_EVENT_EXPECTED = {
    'name': 'Belair Forest',
    'region': 'MW',
    'date_start': '2025-05-10',
    'location': 'Belair Provincial Forest, Hwy 44 at Hwy 302, Stead MB',
    'has_intro_ride': True,
    'ride_manager': 'Kelli Hayhurst',
    'ride_manager_contact': {
        'phone': '431-293-3233',
        'email': 'kellihayhurst64@gmail.com'
    },
    'distances': [
        {'distance': '50', 'start_time': '07:00 am'},
        {'distance': '25', 'start_time': '08:00 am'}
    ],
    'control_judges': [
        {'name': 'Brittney Derksen', 'role': 'Control Judge'}
    ],
    'map_link': 'https://www.google.com/maps/dir/?api=1&destination=50.445380,-96.443778',
    'coordinates': {
        'latitude': 50.44538,
        'longitude': -96.443778
    },
    'is_canceled': False
}


class TestSpecialCases(unittest.TestCase):
    """Test special cases in HTML parsing."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.parser = HTMLParser(debug_mode=True)
        self.data_handler = DataHandler()
        
    def _compare_parsed_event(self, parsed_event, expected_data, fields_to_check=None):
        """Helper method to compare parsed event with expected data."""
        fields_to_check = fields_to_check or expected_data.keys()
        
        for field in fields_to_check:
            if field == 'coordinates':
                # Special handling for coordinates (floating point comparison)
                self.assertIn(field, parsed_event, f"{field} not found in parsed event")
                for coord_key in ['latitude', 'longitude']:
                    self.assertAlmostEqual(
                        parsed_event[field][coord_key],
                        expected_data[field][coord_key],
                        places=5,
                        msg=f"{coord_key} doesn't match expected value"
                    )
            elif field == 'distances':
                # Check that all expected distances are present
                self.assertIn(field, parsed_event, f"{field} not found in parsed event")
                for expected_dist in expected_data[field]:
                    found = False
                    for actual_dist in parsed_event[field]:
                        if expected_dist['distance'] == actual_dist['distance']:
                            found = True
                            # Compare start_time if present
                            if 'start_time' in expected_dist:
                                self.assertEqual(
                                    actual_dist.get('start_time', '').lower(), 
                                    expected_dist['start_time'].lower(),
                                    f"Start time for distance {expected_dist['distance']} doesn't match"
                                )
                            break
                    self.assertTrue(found, f"Distance {expected_dist['distance']} not found in parsed event")
            elif field == 'control_judges':
                # Check that all expected judges are present
                self.assertIn(field, parsed_event, f"{field} not found in parsed event")
                for expected_judge in expected_data[field]:
                    found = False
                    for actual_judge in parsed_event[field]:
                        if expected_judge['name'] == actual_judge['name']:
                            found = True
                            self.assertEqual(
                                actual_judge['role'], 
                                expected_judge['role'],
                                f"Role for judge {expected_judge['name']} doesn't match"
                            )
                            break
                    self.assertTrue(found, f"Judge {expected_judge['name']} not found in parsed event")
            elif field == 'ride_manager_contact':
                # Check that all expected contact info is present
                self.assertIn(field, parsed_event, f"{field} not found in parsed event")
                for contact_key in ['phone', 'email']:
                    if contact_key in expected_data[field]:
                        self.assertIn(
                            contact_key, 
                            parsed_event[field],
                            f"{contact_key} not found in parsed event's contact info"
                        )
                        # For phone, just check it contains expected digits (format may vary)
                        if contact_key == 'phone':
                            expected_digits = ''.join(c for c in expected_data[field][contact_key] if c.isdigit())
                            actual_digits = ''.join(c for c in parsed_event[field][contact_key] if c.isdigit())
                            self.assertEqual(
                                actual_digits, 
                                expected_digits,
                                f"Phone number (digits only) doesn't match expected value"
                            )
                        else:
                            self.assertEqual(
                                parsed_event[field][contact_key], 
                                expected_data[field][contact_key],
                                f"{contact_key} doesn't match expected value"
                            )
            elif field == 'website':
                # Compare URLs without trailing slashes
                self.assertIn(field, parsed_event, f"{field} not found in parsed event")
                self.assertEqual(
                    parsed_event[field].rstrip('/'), 
                    expected_data[field].rstrip('/'),
                    f"{field} doesn't match expected value"
                )
            else:
                # Standard field comparison
                self.assertIn(field, parsed_event, f"{field} not found in parsed event")
                self.assertEqual(
                    parsed_event[field], 
                    expected_data[field],
                    f"{field} doesn't match expected value"
                )
        
    def test_full_parsing_old_pueblo(self):
        """Test full parsing of Old Pueblo event with flyer and intro ride."""
        events = self.parser.parse_html(FLYER_EVENT_HTML)
        self.assertGreater(len(events), 0, "No events were extracted from the HTML")
        event = events[0]
        
        # Check all fields against expected data
        self._compare_parsed_event(event, FLYER_EVENT_EXPECTED)
        
        # Test transforming to validated AERCEvent
        aerc_event = self.data_handler.transform_and_validate(event)
        self.assertTrue(aerc_event.has_intro_ride)
        
        # Check flyer URL
        self.assertEqual(aerc_event.flyer_url, FLYER_EVENT_EXPECTED['flyer_url'])
        
        # Test transforming to EventCreate
        event_create = self.data_handler.to_event_create(aerc_event)
        self.assertTrue(event_create.has_intro_ride)
        self.assertEqual(event_create.flyer_url, FLYER_EVENT_EXPECTED['flyer_url'])
    
    def test_full_parsing_biltmore_cancelled(self):
        """Test full parsing of cancelled Biltmore event."""
        events = self.parser.parse_html(CANCELLED_EVENT_HTML)
        self.assertGreater(len(events), 0, "No events were extracted from the HTML")
        event = events[0]
        
        # Check all fields against expected data
        self._compare_parsed_event(event, CANCELLED_EVENT_EXPECTED)
        
        # Test transforming to validated AERCEvent
        aerc_event = self.data_handler.transform_and_validate(event)
        self.assertTrue(aerc_event.is_canceled)
        
        # Test transforming to EventCreate
        event_create = self.data_handler.to_event_create(aerc_event)
        self.assertTrue(event_create.is_canceled)
    
    def test_full_parsing_tevis_cup(self):
        """Test full parsing of Tevis Cup event with coordinates and website."""
        events = self.parser.parse_html(MAP_EVENT_HTML)
        self.assertGreater(len(events), 0, "No events were extracted from the HTML")
        event = events[0]
        
        # Check all fields against expected data
        self._compare_parsed_event(event, MAP_EVENT_EXPECTED)
        
        # Test transforming to validated AERCEvent
        aerc_event = self.data_handler.transform_and_validate(event)
        self.assertIsNotNone(aerc_event.coordinates)
        # Handle coordinates as a Coordinates object
        self.assertAlmostEqual(
            aerc_event.coordinates.latitude, 
            MAP_EVENT_EXPECTED['coordinates']['latitude'], 
            places=5
        )
        self.assertAlmostEqual(
            aerc_event.coordinates.longitude, 
            MAP_EVENT_EXPECTED['coordinates']['longitude'], 
            places=5
        )
        
        # Check website URL
        self.assertEqual(aerc_event.website.rstrip('/'), MAP_EVENT_EXPECTED['website'].rstrip('/'))
    
    def test_flyer_link_extraction(self):
        """Test extraction of flyer links from event HTML."""
        events = self.parser.parse_html(FLYER_EVENT_HTML)
        self.assertGreater(len(events), 0, "No events were extracted from the HTML")
        event = events[0]
        
        # Focus on flyer-specific assertions
        self.assertIn('flyer_url', event)
        self.assertEqual(event['flyer_url'], FLYER_EVENT_EXPECTED['flyer_url'])
        
        # Test data handling
        aerc_event = self.data_handler.transform_and_validate(event)
        self.assertEqual(aerc_event.flyer_url, FLYER_EVENT_EXPECTED['flyer_url'])
        
        # Test creation of EventCreate model
        event_create = self.data_handler.to_event_create(aerc_event)
        # flyer_url should be directly on the event, not in event_details
        self.assertEqual(event_create.flyer_url, FLYER_EVENT_EXPECTED['flyer_url'])
        
    def test_cancelled_event_detection(self):
        """Test detection of cancelled events."""
        events = self.parser.parse_html(CANCELLED_EVENT_HTML)
        self.assertGreater(len(events), 0, "No events were extracted from the HTML")
        event = events[0]
        
        # Focus on cancellation-specific assertions
        self.assertEqual(event['name'], CANCELLED_EVENT_EXPECTED['name'])
        self.assertTrue(event['is_canceled'])
        
        # Test data handling
        aerc_event = self.data_handler.transform_and_validate(event)
        self.assertTrue(aerc_event.is_canceled)
        event_create = self.data_handler.to_event_create(aerc_event)
        self.assertTrue(event_create.is_canceled)
        
    def test_coordinates_extraction(self):
        """Test extraction of coordinates from Google Maps links."""
        events = self.parser.parse_html(MAP_EVENT_HTML)
        self.assertGreater(len(events), 0, "No events were extracted from the HTML")
        event = events[0]
        
        # Focus on coordinates-specific assertions
        self.assertIn('coordinates', event)
        self.assertAlmostEqual(
            event['coordinates']['latitude'], 
            MAP_EVENT_EXPECTED['coordinates']['latitude'], 
            places=5
        )
        self.assertAlmostEqual(
            event['coordinates']['longitude'], 
            MAP_EVENT_EXPECTED['coordinates']['longitude'], 
            places=5
        )
        
        # Test data handling
        aerc_event = self.data_handler.transform_and_validate(event)
        # Check coordinates in event_details
        self.assertIsNotNone(aerc_event.coordinates)
        event_create = self.data_handler.to_event_create(aerc_event)
        self.assertIn('coordinates', event_create.event_details)

    def test_full_parsing_belair_forest(self):
        """Test full parsing of Belair Forest event in Canada."""
        events = self.parser.parse_html(BELAIR_EVENT_HTML)
        self.assertGreater(len(events), 0, "No events were extracted from the HTML")
        event = events[0]
        
        # Check all fields against expected data
        self._compare_parsed_event(event, BELAIR_EVENT_EXPECTED)
        
        # Check the raw location contains MB (Manitoba)
        self.assertTrue('Stead MB' in event['description'], "MB province code not found in event description")
        
        # Test transforming to validated AERCEvent
        aerc_event = self.data_handler.transform_and_validate(event)
        self.assertIsNotNone(aerc_event.coordinates)
        # Handle coordinates as a Coordinates object
        self.assertAlmostEqual(
            aerc_event.coordinates.latitude, 
            BELAIR_EVENT_EXPECTED['coordinates']['latitude'], 
            places=5
        )
        self.assertAlmostEqual(
            aerc_event.coordinates.longitude, 
            BELAIR_EVENT_EXPECTED['coordinates']['longitude'], 
            places=5
        )
        
        # Test transforming to EventCreate
        event_create = self.data_handler.to_event_create(aerc_event)
        # Check that map_link is preserved
        self.assertEqual(event_create.map_link, BELAIR_EVENT_EXPECTED['map_link'])

    def test_canadian_location_extraction(self):
        """Test extraction of Canadian location with province code MB."""
        events = self.parser.parse_html(BELAIR_EVENT_HTML)
        self.assertGreater(len(events), 0, "No events were extracted from the HTML")
        event = events[0]
        
        # Focus on location-specific assertions
        self.assertIn('location', event)
        
        # Check if the description which contains the full HTML text has MB (Manitoba)
        self.assertTrue('Stead MB' in event['description'], "MB province code not found in event description")
        
        # Verify that coordinates are correctly extracted for this Canadian location
        self.assertIn('coordinates', event)
        self.assertAlmostEqual(event['coordinates']['latitude'], 50.44538, places=5)
        self.assertAlmostEqual(event['coordinates']['longitude'], -96.443778, places=5)
        
        # Test basic transformation
        aerc_event = self.data_handler.transform_and_validate(event)
        self.assertIsNotNone(aerc_event)
        
        # Check that the location is populated and coordinates are present
        self.assertIsNotNone(aerc_event.location)
        self.assertIsNotNone(aerc_event.coordinates)


if __name__ == '__main__':
    unittest.main() 