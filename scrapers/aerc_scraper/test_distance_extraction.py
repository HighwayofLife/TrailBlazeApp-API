"""
Test script to verify distance extraction from AERC HTML data.
"""

import sys
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add the project root to the Python path
project_root = str(Path(__file__).parents[2])
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from bs4 import BeautifulSoup
from scrapers.aerc_scraper.parser_v2.html_parser import HTMLParser
from scrapers.aerc_scraper.data_handler import DataHandler
from scrapers.schema import AERCEvent, Location, ContactInfo, Distance, EventSourceEnum, EventTypeEnum

# Create a simplified test version of the data handler that handles phone number formatting
class TestDataHandler(DataHandler):
    @staticmethod
    def transform_and_validate(raw_event: Dict[str, Any]) -> AERCEvent:
        """Modified transform and validate that handles phone number format issues."""
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

# Sample event HTML extracted from the cache
SAMPLE_HTML = """
<div class="calendarRow "><div class="selectionText bold"> Details for Moab Canyons Pioneer </div><table><tbody>
<tr class="fix-jumpy"><td rowspan="3" class="region">MT</td><td class="bold">10/10/2025</td>
<td class="bold"><span class="rideName details" tag="14576">Moab Canyons Pioneer</span></td>
<td><span class="details" tag="14576">Ride Details</span></td></tr>
<tr class="fix-jumpy"><td>25/50 miles<br /><span style="color: red;">Has Intro Ride!</span></td>
<td>Jug Rock Camp, Spring Canyon Rd, Moab, Utah<br />
<a href="https://www.google.com/maps/dir/?api=1&destination=38.636389,-109.883056" target="_blank">Click Here for Directions via Google Maps</a> </td>
<td><a href="https://mickeysmt.wixsite.com/moabenduranceride" target="_blank">Website</a><br></td></tr>
<tr id="TRrideID14576" class="fix-jumpy"><td>mgr: Mickey Smith</td><td>Control Judge: Kathy Backus</td>
<td nowrap=""><span class="details" tag="14576">* Details *</span></td></tr>
<tr name="rideID14576Details"><td colspan="4"></td></tr>
<tr name="rideID14576Details" id="rideRow14576" class="toggle-ride-dets fix-jumpy" style="display: none;">
<td colspan="4"><table class="detailData" border="1"><tbody>
<tr><td>Ride</td><td>Location : </td><td>Jug Rock Camp, Spring Canyon Rd, Moab, Utah<br />
<a href="https://www.google.com/maps/dir/?api=1&destination=38.636389,-109.883056" target="_blank">Click Here for Directions via Google Maps</a></td></tr>
<tr><td></td><td>Website : </td><td><a href="https://mickeysmt.wixsite.com/moabenduranceride" target="_blank">follow this link</a></td></tr>
<tr><td>Managers</td><td>Ride Manager : </td><td>Mickey Smith, 435-260-8521,  (Mickey@blazeadventure.com)</td>
<tr><td>Control Judges</td><td>Head Control Judge : </td><td>Kathy Backus</td></tr>
<tr><td></td><td>Control Judge : </td><td>Summer Peterson</td></tr>
<tr><td></td><td>Control Judge : </td><td>Dana Reeder</td></tr>
<tr><td>Distances</td><td>50&nbsp;</td><td>on Oct 10, 2025 starting at 07:30 am</td></tr>
<tr><td>Distances</td><td>50&nbsp;</td><td>on Oct 11, 2025 starting at 07:30 am</td></tr>
<tr><td>Distances</td><td>50&nbsp;</td><td>on Oct 12, 2025 starting at 07:30 am</td></tr>
<tr><td>Distances</td><td>25&nbsp;</td><td>on Oct 10, 2025 starting at 08:00 am</td></tr>
<tr><td>Distances</td><td>25&nbsp;</td><td>on Oct 11, 2025 starting at 08:00 am</td></tr>
<tr><td>Distances</td><td>25&nbsp;</td><td>on Oct 12, 2025 starting at 08:00 am</td></tr>
<tr><td>Descriptive</td><td colspan="2" style="text-align: left; color: #000;">Description:<br />Primitive camping site, be prepared!!<br /><br />Directions:<br />See website<br /><br /></td></tr>
</tbody></table></td></tr><tr><td colspan="4" class="spacer"><hr width="98%"></td></tr></tbody></table></div>
"""

def main():
    """Test distance extraction functionality."""
    print("Testing Distance Extraction from AERC HTML")
    print("-----------------------------------------")
    
    # Parse the sample HTML
    soup = BeautifulSoup(SAMPLE_HTML, 'html.parser')
    sample_event_html = soup.find('div', class_='calendarRow')
    
    if not sample_event_html:
        print("Failed to parse sample event HTML.")
        return
    
    event_name = sample_event_html.select_one('span.rideName')
    print(f"Sample event: {event_name.text if event_name else 'Unknown'}")
    
    # Create HTML parser and extract event data
    parser = HTMLParser(debug_mode=True)
    raw_event = parser._extract_event_data(sample_event_html, 0)
    
    if not raw_event:
        print("Failed to extract event data.")
        return
    
    print("\nExtracted Raw Event Data:")
    print(f"Name: {raw_event.get('name')}")
    print(f"Date: {raw_event.get('date_start')}")
    print(f"Location: {raw_event.get('location')}")
    
    print("\nExtracted Distances:")
    for i, dist in enumerate(raw_event.get('distances', [])):
        print(f"  Distance {i+1}: {dist.get('distance')} - Start Time: {dist.get('start_time')}")
    
    # Transform raw event to AERCEvent using our test DataHandler
    try:
        data_handler = TestDataHandler()
        event = data_handler.transform_and_validate(raw_event)
        
        print("\nValidated AERCEvent:")
        print(f"Name: {event.name}")
        print(f"Date: {event.date_start}")
        print("\nValidated Distances:")
        for i, dist in enumerate(event.distances):
            print(f"  Distance {i+1}: {dist.distance} - Start Time: {dist.start_time}")
        
        # Convert to EventCreate format
        event_create = data_handler.to_event_create(event)
        
        print("\nEventCreate Format (for database storage):")
        print(f"Name: {event_create.name}")
        print(f"Date: {event_create.date_start}")
        print(f"Distances: {', '.join(event_create.distances)}")
        
        if event_create.event_details and 'distances' in event_create.event_details:
            print("\nDetailed Distances in event_details:")
            for i, dist in enumerate(event_create.event_details['distances']):
                print(f"  Distance {i+1}: {dist.get('distance')} - Start Time: {dist.get('start_time', 'N/A')}")
        
    except Exception as e:
        print(f"Error during validation: {e}")
    
    print("\nDistance Extraction Test Complete")

if __name__ == "__main__":
    main() 