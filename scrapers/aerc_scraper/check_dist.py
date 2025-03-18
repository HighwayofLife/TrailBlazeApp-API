#!/usr/bin/env python3
"""
Test script to verify the HTML parser and data handler improvements.
This checks extraction of all fields including distances, coordinates, and flags.
"""

import sys
import json
from pathlib import Path
from pprint import pprint

# Add project root to path
project_root = str(Path(__file__).parents[2])
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from parser_v2.html_parser import HTMLParser
from data_handler import DataHandler

# Sample event HTML with multiple distances
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

# Sample of a canceled event
CANCELED_HTML = """
<div class="calendarRow">
    <span class="rideName">Cancelled Event</span>
    <span class="rideDate">10/15/2023</span>
    <span class="rideLocation">Anywhere, TX</span>
    <div class="details">This event has been CANCELED due to weather conditions.</div>
    <div>
        <p>RM: John Doe</p>
        <p>Email: john@example.com</p>
        <p>Distances: 25, 50, 75</p>
    </div>
</div>
"""

def main():
    """Run the test script."""
    print("Testing HTML parser improvements...")
    
    # Initialize parser
    parser = HTMLParser()
    data_handler = DataHandler()
    
    # Parse the HTML
    events = parser.parse_html(SAMPLE_HTML)
    print(f"Found {len(events)} events in the HTML")
    
    if not events:
        print("No events found!")
        return
    
    # Get the first event
    event = events[0]
    
    print("\n=== Raw Event Data ===")
    print(f"Name: {event['name']}")
    print(f"Date: {event['date_start']}")
    print(f"Region: {event['region']}")
    print(f"Location: {event['location']}")
    
    # Check for city/state
    print(f"City: {event.get('city', 'Not extracted')}")
    print(f"State: {event.get('state', 'Not extracted')}")
    
    # Check for coordinates
    if 'coordinates' in event:
        print(f"Coordinates: Latitude {event['coordinates'].get('latitude')}, Longitude {event['coordinates'].get('longitude')}")
    else:
        print("Coordinates: Not extracted")
        
    # Check for map link
    print(f"Map Link: {event.get('map_link', 'Not found')}")
    
    # Check for distances
    print("\nDistances:")
    for dist in event.get('distances', []):
        print(f"  - {dist.get('distance')} miles @ {dist.get('start_time', 'No time')}")
    
    # Check for intro ride
    print(f"Has Intro Ride: {event.get('has_intro_ride', False)}")
    
    # Check for cancellation
    print(f"Is Canceled: {event.get('is_canceled', False)}")
    
    # Check for description
    print(f"\nDescription: {event.get('description', 'No description')}")
    
    # Check for control judges
    if 'control_judges' in event:
        print("\nControl Judges:")
        for judge in event['control_judges']:
            print(f"  - {judge.get('name')} ({judge.get('role', 'Control Judge')})")
    
    # Transform to validated event
    print("\n=== Validating and Transforming ===")
    try:
        aerc_event = data_handler.transform_and_validate(event)
        print("Successfully transformed to AERCEvent!")
        
        # Convert to EventCreate format
        event_create = data_handler.to_event_create(aerc_event)
        print("Successfully converted to EventCreate format!")
        
        # Check distances in EventCreate
        print("\nEventCreate distances:")
        for dist in event_create.distances:
            print(f"  - {dist}")
            
        # Check event details
        if event_create.event_details:
            print("\nEvent Details:")
            # Pretty print the detailed distances if available
            if 'distances' in event_create.event_details:
                print("\nDetailed distances:")
                for dist in event_create.event_details['distances']:
                    print(f"  - {dist.get('distance')} {dist.get('unit', 'miles')} @ {dist.get('start_time', 'No time')}")
            
            # Print coordinates if available
            if 'coordinates' in event_create.event_details:
                coords = event_create.event_details['coordinates']
                print(f"\nCoordinates: Latitude {coords.get('latitude')}, Longitude {coords.get('longitude')}")
                
            # Print other fields in event_details
            print("\nOther event details:")
            for key, value in event_create.event_details.items():
                if key not in ['distances', 'coordinates']:
                    print(f"  - {key}: {value}")
    
    except Exception as e:
        print(f"Error during transformation: {e}")
    
    # Test a canceled event
    print("\n=== Testing Canceled Event ===")
    canceled_events = parser.parse_html(CANCELED_HTML)
    if canceled_events:
        print(f"Found {len(canceled_events)} canceled events")
        print(f"Name: {canceled_events[0]['name']}")
        print(f"Is Canceled: {canceled_events[0].get('is_canceled', False)}")
    else:
        print("No canceled events found!")

if __name__ == "__main__":
    main() 