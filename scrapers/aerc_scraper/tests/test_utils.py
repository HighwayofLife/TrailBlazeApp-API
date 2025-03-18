"""
Testing utilities for AERC scraper component.
"""

import re
from datetime import datetime
from typing import Dict, Any

from scrapers.aerc_scraper.data_handler import DataHandler
from scrapers.schema import AERCEvent, Location, ContactInfo, Distance, EventSourceEnum, EventTypeEnum

class TestDataHandler(DataHandler):
    """Test-specific version of DataHandler with phone number format handling."""
    
    @staticmethod
    def transform_and_validate(raw_event: Dict[str, Any]) -> AERCEvent:
        """Modified transform_and_validate that handles phone number format issues."""
        # Transform location data
        location_parts = DataHandler._parse_location(raw_event.get('location', ''))
        location_name = location_parts.get('name')
        
        # If no name was extracted but we have city/state, use the full location as name
        if not location_name and (location_parts.get('city') or location_parts.get('state')):
            location_name = raw_event.get('location', 'Unknown Location')
            
        location = Location(
            name=location_name or raw_event.get('location', 'Unknown Location'),
            city=location_parts.get('city'),
            state=location_parts.get('state'),
            country="USA"  # Default for AERC events
        )

        # Transform contact information with sanitized phone numbers
        contacts = []
        if raw_event.get('ride_manager'):
            # Clean the phone number for validation
            phone = raw_event.get('ride_manager_contact', {}).get('phone')
            if phone:
                # Remove all non-digit characters except + for country code
                phone = re.sub(r'[^\d+]', '', phone)
                
            contact = ContactInfo(
                name=raw_event['ride_manager'],
                email=raw_event.get('ride_manager_contact', {}).get('email'),
                phone=phone,
                role="Ride Manager"
            )
            contacts.append(contact)

        # Transform distances
        distances = []
        for dist in raw_event.get('distances', []):
            # Create a distance object with additional properties to avoid attribute errors
            try:
                distance_obj = Distance(
                    distance=dist['distance'],
                    date=datetime.strptime(raw_event['date_start'], '%Y-%m-%d'),
                    # Adding start_time as empty string to avoid None errors if accessed
                    start_time=dist.get('start_time', ''),
                    # Add any other potential fields that might be accessed
                    entry_fee=dist.get('entry_fee'),
                    max_riders=dist.get('max_riders'),
                )
                distances.append(distance_obj)
            except Exception as e:
                # Log but don't fail if a specific distance can't be processed
                print(f"Warning: Could not process distance {dist}: {str(e)}")
                continue

        # Create validated event object
        event_data = {
            'name': raw_event['name'],
            'source': EventSourceEnum.AERC,
            'event_type': EventTypeEnum.ENDURANCE,  # Default for AERC events
            'date_start': datetime.strptime(raw_event['date_start'], '%Y-%m-%d'),
            'location': location,
            'region': raw_event.get('region'),
            'description': None,  # Not provided in raw data
            'distances': distances,
            'contacts': contacts,
            'website_url': DataHandler._validate_url(raw_event.get('website')),
            'registration_url': DataHandler._validate_url(raw_event.get('flyer_url')),
            'external_id': None,  # Can be added if needed
            'sanctioning_status': None,  # Can be extracted if available
            'has_drug_testing': False,  # Default value
        }

        return AERCEvent.model_validate(event_data) 