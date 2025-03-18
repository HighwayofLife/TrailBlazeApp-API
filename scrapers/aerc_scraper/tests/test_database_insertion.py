"""
Unit tests for database insertion of parsed event data.
Tests the full flow from HTML parsing to database storage.
"""

import unittest
import sys
import os
import asyncio
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

# Add project root to path
project_root = str(Path(__file__).parents[3])
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scrapers.aerc_scraper.parser_v2.html_parser import HTMLParser
from scrapers.aerc_scraper.data_handler import DataHandler
from scrapers.aerc_scraper.database import DatabaseHandler
from scrapers.schema import AERCEvent
from scrapers.aerc_scraper.tests.test_html_parser import SAMPLE_EVENT_HTML, EXPECTED_PARSED_DATA

class TestDatabaseInsertion(unittest.TestCase):
    """Test the full flow from HTML parsing to database insertion."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.parser = HTMLParser(debug_mode=True)
        self.data_handler = DataHandler()
        
        # Create mock database session
        self.mock_db = AsyncMock()
        
        # Set up commit method to be awaitable
        async def mock_commit():
            return None
        self.mock_db.commit.side_effect = mock_commit
        
        # Create a database handler
        self.database = DatabaseHandler()
        
        # Parse the sample HTML
        self.events = self.parser.parse_html(SAMPLE_EVENT_HTML)
        self.assertTrue(len(self.events) > 0, "Failed to parse any events from sample HTML")
        self.raw_event = self.events[0]
        self.aerc_event = self.data_handler.transform_and_validate(self.raw_event)
        self.event_create = self.data_handler.to_event_create(self.aerc_event)
        
        # List of events to store
        self.events_to_store = [self.event_create]
    
    @patch('scrapers.aerc_scraper.database.get_events')
    @patch('scrapers.aerc_scraper.database.create_event')
    @patch('scrapers.aerc_scraper.database.update_event')
    def test_store_events(self, mock_update, mock_create, mock_get):
        """Test that events are correctly stored in the database."""
        # Mock get_events to return empty list (no existing events)
        async def mock_get_events(*args, **kwargs):
            return []
        mock_get.side_effect = mock_get_events
        
        # Mock create_event to return an object with ID
        mock_event = MagicMock()
        mock_event.id = 1
        
        # Set up mock to return awaitable coroutine
        async def mock_create_coro(*args, **kwargs):
            return mock_event
        mock_create.side_effect = mock_create_coro
        
        # Call the store_events method and run it in the event loop
        metrics = asyncio.run(self.database.store_events(self.events_to_store, self.mock_db))
        
        # Check that get_events was called
        mock_get.assert_called()
        
        # Check that create_event was called
        self.assertTrue(mock_create.called)
        
        # Check metrics
        self.assertEqual(metrics['added'], 1)
        self.assertEqual(metrics['errors'], 0)
    
    @patch('scrapers.aerc_scraper.database.get_events')
    @patch('scrapers.aerc_scraper.database.create_event')
    @patch('scrapers.aerc_scraper.database.update_event')
    def test_update_existing_event(self, mock_update, mock_create, mock_get):
        """Test that existing events are correctly updated in the database."""
        # Create a mock existing event that matches our event
        mock_existing = MagicMock()
        mock_existing.id = 1
        mock_existing.name = self.event_create.name
        mock_existing.location = self.event_create.location
        mock_existing.is_canceled = False
        
        # Mock get_events to return our existing event
        async def mock_get_events(*args, **kwargs):
            return [mock_existing]
        mock_get.side_effect = mock_get_events
        
        # Mock update_event to return the updated event
        mock_updated = MagicMock()
        mock_updated.id = 1
        
        # Set up mock to return awaitable coroutine
        async def mock_update_coro(*args, **kwargs):
            return mock_updated
        mock_update.side_effect = mock_update_coro
        
        # Call the store_events method and run it in the event loop
        metrics = asyncio.run(self.database.store_events(self.events_to_store, self.mock_db))
        
        # Check that get_events was called
        mock_get.assert_called()
        
        # Check that update_event was called
        self.assertTrue(mock_update.called)
        
        # Check metrics
        self.assertEqual(metrics['updated'], 1)
        self.assertEqual(metrics['added'], 0)
        self.assertEqual(metrics['errors'], 0)
    
    @patch('scrapers.aerc_scraper.database.get_events')
    @patch('scrapers.aerc_scraper.database.create_event')
    @patch('scrapers.aerc_scraper.database.update_event')
    def test_skip_canceled_event(self, mock_update, mock_create, mock_get):
        """Test that canceled events are skipped."""
        # Create a mock existing event that is canceled
        mock_existing = MagicMock()
        mock_existing.id = 1
        mock_existing.name = self.event_create.name
        mock_existing.location = self.event_create.location
        mock_existing.is_canceled = True
        
        # Mock get_events to return our existing event
        async def mock_get_events(*args, **kwargs):
            return [mock_existing]
        mock_get.side_effect = mock_get_events
        
        # Call the store_events method and run it in the event loop
        metrics = asyncio.run(self.database.store_events(self.events_to_store, self.mock_db))
        
        # Check that get_events was called
        mock_get.assert_called()
        
        # Check that update_event was not called
        mock_update.assert_not_called()
        
        # Check metrics
        self.assertEqual(metrics['skipped'], 1)
        self.assertEqual(metrics['updated'], 0)
        self.assertEqual(metrics['added'], 0)
    
    @patch('scrapers.aerc_scraper.database.get_events')
    @patch('scrapers.aerc_scraper.database.create_event')
    def test_event_details_storage(self, mock_create, mock_get):
        """Test that event details are correctly stored."""
        # Mock get_events to return empty list (no existing events)
        async def mock_get_events(*args, **kwargs):
            return []
        mock_get.side_effect = mock_get_events
        
        # Mock create_event to return an object with ID
        mock_event = MagicMock()
        mock_event.id = 1
        
        # Set up mock to return awaitable coroutine
        async def mock_create_coro(*args, **kwargs):
            return mock_event
        mock_create.side_effect = mock_create_coro
        
        # Call the store_events method and run it in the event loop
        metrics = asyncio.run(self.database.store_events(self.events_to_store, self.mock_db))
        
        # Check that create_event was called with the right event data
        mock_create.assert_called()
        
        # Extract the event from the call arguments
        event_arg = mock_create.call_args[0][1]
        
        # Check that event_details contains map_link and location data
        self.assertIsNotNone(event_arg.event_details)
        self.assertIn('map_link', event_arg.event_details)
        
        # Check map_link matches expected data
        map_link = event_arg.event_details['map_link']
        self.assertEqual(
            map_link,
            EXPECTED_PARSED_DATA['map_link']
        )
        
        # Check control judges
        self.assertIn('control_judges', event_arg.event_details)
        judges = event_arg.event_details['control_judges']
        self.assertGreaterEqual(len(judges), 1)
        
        # Check intro ride flag
        self.assertIn('has_intro_ride', event_arg.event_details)
        self.assertEqual(event_arg.event_details['has_intro_ride'], EXPECTED_PARSED_DATA['has_intro_ride'])
    
    def test_phone_number_format(self):
        """Test that phone numbers are correctly preserved with formatting."""
        # Extract phone from the raw event
        if 'ride_manager_contact' in self.raw_event and 'phone' in self.raw_event['ride_manager_contact']:
            raw_phone = self.raw_event['ride_manager_contact']['phone']
            # Make sure it contains dashes or other formatting
            self.assertTrue(
                '-' in raw_phone or '.' in raw_phone or ' ' in raw_phone or '(' in raw_phone,
                f"Phone number {raw_phone} doesn't have expected formatting"
            )
            # Compare to expected data
            self.assertEqual(raw_phone, EXPECTED_PARSED_DATA['ride_manager_contact']['phone'])
            
        # Check that this formatting is preserved in the EventCreate object    
        self.assertEqual(
            self.event_create.manager_phone,
            EXPECTED_PARSED_DATA['ride_manager_contact']['phone']
        )

if __name__ == '__main__':
    unittest.main() 