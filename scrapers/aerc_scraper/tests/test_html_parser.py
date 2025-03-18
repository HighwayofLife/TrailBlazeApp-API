"""
Unit tests for the HTML parser component.
Tests extraction of structured data from raw HTML.
"""

import unittest
import sys
from pathlib import Path
from datetime import datetime
import os

# Add project root to path
project_root = str(Path(__file__).parents[3])
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from bs4 import BeautifulSoup
from scrapers.aerc_scraper.parser_v2.html_parser import HTMLParser
from scrapers.aerc_scraper.data_handler import DataHandler
from scrapers.aerc_scraper.tests.expected_test_data import EXPECTED_DATA, EVENT_SAMPLES, get_expected_data

class TestHTMLParser(unittest.TestCase):
    """Test HTML parser functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.parser = HTMLParser(debug_mode=True)
        
        # Load the first sample file for basic tests
        self.sample_name = EVENT_SAMPLES[0]  # Using old_pueblo_event.html as default
        self.sample_path = os.path.join(
            os.path.dirname(__file__), 
            'html_samples', 
            self.sample_name
        )
        
        # Load sample HTML
        with open(self.sample_path, 'r', encoding='utf-8') as f:
            self.sample_html = f.read()
            
        # Parse the sample HTML
        self.soup = BeautifulSoup(self.sample_html, 'html.parser')
        self.event_html = self.soup.find('div', class_='calendarRow')
        
        # Get expected data for this sample
        self.expected_data = get_expected_data(self.sample_name)
    
    def test_extract_event_data(self):
        """Test extraction of structured data from HTML."""
        # Parse HTML
        raw_event = self.parser._extract_event_data(self.event_html, 0)
        
        # Basic assertions
        self.assertIsNotNone(raw_event)
        self.assertEqual(raw_event['name'], self.expected_data['name'])
        
        # Verify date
        self.assertEqual(raw_event['date_start'], self.expected_data['date_start'])
        
        # Verify ride manager
        self.assertEqual(raw_event['ride_manager'], self.expected_data['ride_manager'])
        
        # Verify link extraction if present in expected data
        if 'website' in self.expected_data:
            self.assertEqual(raw_event.get('website'), self.expected_data['website'])
        
        # Verify ride_id
        if 'ride_id' in self.expected_data:
            self.assertEqual(raw_event.get('ride_id'), self.expected_data['ride_id'])
    
    def test_date_extraction(self):
        """Test extraction of event date."""
        date = self.parser._extract_date(self.event_html)
        # Should match the expected date from our test data
        self.assertEqual(date, self.expected_data['date_start'])
        
        # Verify date is in YYYY-MM-DD format
        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            self.fail("Date is not in YYYY-MM-DD format")
    
    def test_location_extraction(self):
        """Test extraction of event location."""
        location = self.parser._extract_location(self.event_html)
        self.assertIn(self.expected_data['location'], location)
    
    def test_links_extraction(self):
        """Test extraction of links (website, flyer, map)."""
        website, flyer_url, map_link = self.parser._extract_links(self.event_html)
        
        # Verify website link if present in expected data
        if 'website' in self.expected_data:
            self.assertEqual(website, self.expected_data['website'])
        
        # Verify flyer URL if present in expected data
        if 'flyer_url' in self.expected_data:
            self.assertEqual(flyer_url, self.expected_data['flyer_url'])
        
        # Verify map link if present in expected data
        if 'map_link' in self.expected_data:
            self.assertEqual(map_link, self.expected_data['map_link'])
        
    def test_contact_info_extraction(self):
        """Test extraction of contact information."""
        ride_manager, email, phone = self.parser._extract_contact_info(self.event_html)
        
        self.assertEqual(ride_manager, self.expected_data['ride_manager'])
        
        if 'manager_email' in self.expected_data:
            self.assertEqual(email, self.expected_data['manager_email'])
            
        if 'manager_phone' in self.expected_data:
            self.assertEqual(phone, self.expected_data['manager_phone'])
            
    def test_google_map_link_extraction(self):
        """Test extraction of Google Maps link and coordinates."""
        # Skip test if no coordinates in expected data
        if 'coordinates' not in self.expected_data:
            self.skipTest("No coordinates in expected data for this sample")
        
        # Test the link extraction directly
        website, flyer_url, map_link = self.parser._extract_links(self.event_html)
        
        # Verify the map link
        self.assertEqual(map_link, self.expected_data['map_link'])
        
        # The parser should extract coordinates from the map link
        raw_event = self.parser._extract_event_data(self.event_html, 0)
        
        # Verify coordinates
        self.assertIsInstance(raw_event['coordinates'], dict)
        self.assertIn('latitude', raw_event['coordinates'])
        self.assertIn('longitude', raw_event['coordinates'])
        
        # Coordinates should be close to the expected values (floating point comparison)
        self.assertAlmostEqual(
            raw_event['coordinates']['latitude'],
            self.expected_data['coordinates']['latitude'],
            places=4
        )
        self.assertAlmostEqual(
            raw_event['coordinates']['longitude'],
            self.expected_data['coordinates']['longitude'],
            places=4
        )
                
    def test_description_extraction(self):
        """Test extraction of event description and directions."""
        # Skip if no description in expected data
        if 'description' not in self.expected_data:
            self.skipTest("No description in expected data for this sample")
            
        raw_event = self.parser._extract_event_data(self.event_html, 0)
        
        # Check if description is extracted
        self.assertIn('description', raw_event)
        self.assertTrue(raw_event['description'], "Description should not be empty")
            
    def test_control_judges_extraction(self):
        """Test extraction of control judges information."""
        # Skip if no control judges in expected data
        if 'control_judges' not in self.expected_data:
            self.skipTest("No control judges in expected data for this sample")
            
        raw_event = self.parser._extract_event_data(self.event_html, 0)
        
        # Check if control judges are extracted
        self.assertIn('control_judges', raw_event)
        self.assertGreaterEqual(len(raw_event['control_judges']), 1)
        
        # At least the first judge should match
        expected_judge = self.expected_data['control_judges'][0]['name']
        found_judge = False
        for judge in raw_event['control_judges']:
            if judge['name'] == expected_judge:
                found_judge = True
                break
        
        self.assertTrue(found_judge, f"Control judge {expected_judge} not found in parsed data")

    def test_distance_extraction(self):
        """Test extraction of distance information."""
        # Skip if no distances in expected data
        if 'distances' not in self.expected_data:
            self.skipTest("No distances in expected data for this sample")
            
        distances = self.parser._extract_distances(self.event_html)
        
        # Verify distances are extracted
        self.assertGreater(len(distances), 0, "Should extract at least one distance")
        
        # Verify each distance has valid attributes
        for distance in distances:
            self.assertIn('distance', distance)
            self.assertIsInstance(distance['distance'], str)
        
    def test_full_parsing_flow(self):
        """Test the complete flow from HTML to structured data using our sample files."""
        for sample_name in EVENT_SAMPLES:
            with self.subTest(sample_name=sample_name):
                # Load the sample file
                sample_path = os.path.join(
                    os.path.dirname(__file__), 
                    'html_samples', 
                    sample_name
                )
                
                # Skip if file doesn't exist (could happen in development)
                if not os.path.exists(sample_path):
                    self.skipTest(f"Sample file {sample_name} not found")
                    
                # Load sample HTML
                with open(sample_path, 'r', encoding='utf-8') as f:
                    sample_html = f.read()
                
                # Get expected data for this sample
                expected = get_expected_data(sample_name)
                
                # Parse the HTML
                parsed_events = self.parser.parse_html(sample_html)
                
                # There should be at least one event parsed
                self.assertGreaterEqual(len(parsed_events), 1, 
                                       f"Failed to parse any events from {sample_name}")
                
                # Check the first event against expected data
                parsed = parsed_events[0]
                
                # Test essential fields
                self.assertEqual(parsed['name'], expected['name'])
                self.assertEqual(parsed['date_start'], expected['date_start'])
                self.assertEqual(parsed['is_canceled'], expected['is_canceled'])
                
                # Verify multi-day event flags
                if 'is_multi_day_event' in expected:
                    is_multi_day = parsed.get('is_multi_day_event', False)
                    self.assertEqual(is_multi_day, expected['is_multi_day_event'],
                                    f"Expected is_multi_day_event={expected['is_multi_day_event']}, got {is_multi_day}")
                
                if 'is_pioneer_ride' in expected:
                    is_pioneer = parsed.get('is_pioneer_ride', False)
                    self.assertEqual(is_pioneer, expected['is_pioneer_ride'],
                                    f"Expected is_pioneer_ride={expected['is_pioneer_ride']}, got {is_pioneer}")
                
                if 'ride_days' in expected:
                    ride_days = parsed.get('ride_days', 1)
                    self.assertEqual(ride_days, expected['ride_days'],
                                    f"Expected ride_days={expected['ride_days']}, got {ride_days}")
                
                # Check location_details if present
                if 'location_details' in expected:
                    self.assertIn('location_details', parsed)
                    if 'country' in expected['location_details']:
                        self.assertEqual(
                            parsed['location_details']['country'], 
                            expected['location_details']['country']
                        )
                
                # Transform to AERCEvent using DataHandler
                try:
                    data_handler = DataHandler()
                    event = data_handler.transform_and_validate(parsed)
                    
                    # Basic validation of transformed event
                    self.assertEqual(event.name, expected['name'])
                    self.assertEqual(event.is_canceled, expected['is_canceled'])
                    
                except Exception as e:
                    self.fail(f"Transformation failed for {sample_name}: {str(e)}")
            
    def test_has_intro_ride_detection(self):
        """Test detection of intro ride flag."""
        # Skip if has_intro_ride not defined in expected data
        if 'has_intro_ride' not in self.expected_data:
            self.skipTest("has_intro_ride not defined in expected data")
            
        raw_event = self.parser._extract_event_data(self.event_html, 0)
        
        # Check if the parser correctly identifies the intro ride from HTML
        self.assertIn('has_intro_ride', raw_event)
        self.assertEqual(raw_event['has_intro_ride'], self.expected_data['has_intro_ride'])
            
    def test_is_canceled_detection(self):
        """Test detection of canceled events."""
        # Test with a sample that should be a canceled event
        canceled_sample = None
        for sample in EVENT_SAMPLES:
            if EXPECTED_DATA[sample]['is_canceled']:
                canceled_sample = sample
                break
        
        if not canceled_sample:
            self.skipTest("No canceled event in sample data")
            
        # Load the canceled event
        canceled_path = os.path.join(
            os.path.dirname(__file__), 
            'html_samples', 
            canceled_sample
        )
        
        with open(canceled_path, 'r', encoding='utf-8') as f:
            canceled_html = f.read()
            
        # Parse the canceled event HTML
        parsed_events = self.parser.parse_html(canceled_html)
        
        # Verify the event was extracted
        self.assertEqual(len(parsed_events), 1, "Should extract one event")
        
        # Verify the event is marked as canceled
        self.assertTrue(parsed_events[0]['is_canceled'], "Event should be marked as canceled")
        
        # Also test a non-canceled event
        non_canceled_sample = None
        for sample in EVENT_SAMPLES:
            if not EXPECTED_DATA[sample]['is_canceled']:
                non_canceled_sample = sample
                break
                
        if non_canceled_sample:
            non_canceled_path = os.path.join(
                os.path.dirname(__file__), 
                'html_samples', 
                non_canceled_sample
            )
            
            with open(non_canceled_path, 'r', encoding='utf-8') as f:
                non_canceled_html = f.read()
                
            # Parse the non-canceled event HTML
            non_canceled_events = self.parser.parse_html(non_canceled_html)
            
            # Verify the event is not marked as canceled
            self.assertFalse(non_canceled_events[0]['is_canceled'], 
                           "Non-canceled event should not be marked as canceled")
    
    def test_multi_day_event_detection(self):
        """Test detection of multi-day events and pioneer rides."""
        # Find a multi-day event sample
        multi_day_sample = None
        for sample in EVENT_SAMPLES:
            if EXPECTED_DATA[sample]['is_multi_day_event']:
                multi_day_sample = sample
                break
        
        if not multi_day_sample:
            self.skipTest("No multi-day event in sample data")
            
        # Load the multi-day event
        multi_day_path = os.path.join(
            os.path.dirname(__file__), 
            'html_samples', 
            multi_day_sample
        )
        
        with open(multi_day_path, 'r', encoding='utf-8') as f:
            multi_day_html = f.read()
            
        # Parse the multi-day event HTML
        parsed_events = self.parser.parse_html(multi_day_html)
        
        # Verify the event was extracted
        self.assertEqual(len(parsed_events), 1, "Should extract one event")
        
        # Verify multi-day flags
        self.assertTrue(parsed_events[0]['is_multi_day_event'], 
                        "Event should be marked as multi-day")
        
        # Verify pioneer ride flag if applicable
        expected_is_pioneer = EXPECTED_DATA[multi_day_sample]['is_pioneer_ride']
        self.assertEqual(parsed_events[0]['is_pioneer_ride'], expected_is_pioneer,
                         f"Pioneer ride flag should be {expected_is_pioneer}")
        
        # Verify ride days
        expected_ride_days = EXPECTED_DATA[multi_day_sample]['ride_days']
        self.assertEqual(parsed_events[0]['ride_days'], expected_ride_days,
                         f"Ride days should be {expected_ride_days}")
        
        # Also test a single-day event
        single_day_sample = None
        for sample in EVENT_SAMPLES:
            if not EXPECTED_DATA[sample]['is_multi_day_event']:
                single_day_sample = sample
                break
                
        if single_day_sample:
            single_day_path = os.path.join(
                os.path.dirname(__file__), 
                'html_samples', 
                single_day_sample
            )
            
            with open(single_day_path, 'r', encoding='utf-8') as f:
                single_day_html = f.read()
                
            # Parse the single-day event HTML
            single_day_events = self.parser.parse_html(single_day_html)
            
            # Verify the event is not marked as multi-day
            self.assertFalse(single_day_events[0].get('is_multi_day_event', False), 
                           "Single-day event should not be marked as multi-day")
            
            # Verify not a pioneer ride
            self.assertFalse(single_day_events[0].get('is_pioneer_ride', False),
                          "Single-day event should not be marked as pioneer ride")

if __name__ == '__main__':
    unittest.main() 