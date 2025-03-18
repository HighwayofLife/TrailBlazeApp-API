"""
Expected Test Data for AERC Scraper Tests.

This file contains the authoritative source of truth for expected test data used across multiple test files.
These data structures represent the expected output after parsing HTML files in the html_samples directory.

IMPORTANT: 
- DO NOT MODIFY this data unless you are intentionally changing the expected behavior of the parser.
- Any changes here will affect multiple tests including parser tests, data handler tests, and database tests.
- This is the canonical reference for how parsed data should be structured.
- This is how the data from the parser is validated against the expected data.
- If you change this data (which should only happen if you are changing the source HTML files), ensure the parser is updated to match.

The data is structured as a dictionary with filenames as keys and dictionaries of expected data as values.
Each event dictionary contains all fields that should be extracted from the corresponding HTML file.
"""

from typing import Dict, Any, List

# Expected output data for each HTML sample file
# This is the authoritative source of expected structured data
EXPECTED_DATA = {
    "old_pueblo_event.html": {
        "name": "Original Old Pueblo",
        "source": "AERC",
        "event_type": "endurance",
        "date_start": "2025-03-28",
        "location": "Empire Ranch, Empire Ranch Rd, Sonoita, AZ",
        "region": "SW",
        "is_canceled": False,
        "ride_manager": "Marilyn McCoy",
        "manager_phone": "520-360-9445",
        "manager_email": "marilynmccoy@hotmail.com",
        "website": "https://example.com/oldpueblo",
        "flyer_url": "https://aerc.org/wp-content/uploads/2025/02/2025OldPueblo.pdf",
        "has_intro_ride": True,
        "ride_id": "14526",
        "distances": [
            {"distance": "50 miles", "date": "Mar 28, 2025", "start_time": "07:00 am"},
            {"distance": "25 miles", "date": "Mar 28, 2025", "start_time": "08:00 am"},
            {"distance": "10 miles", "date": "Mar 28, 2025", "start_time": "09:00 am"}
        ],
        "location_details": {
            "city": "Sonoita",
            "state": "AZ",
            "country": "USA"
        },
        "control_judges": [
            {"name": "Larry Nolen", "role": "Control Judge"}
        ],
        "description": "Historic 50-year AERC ride, with pristine desert trails.",
        "directions": "From I-10, take Sonoita exit south to Empire Ranch Road."
    },
    "biltmore_cancelled_event.html": {
        "name": "Biltmore Open Challenge I",
        "source": "AERC",
        "event_type": "endurance",
        "date_start": "2025-05-02",
        "location": "Biltmore Equestrian Center, 1 Biltmore Estate Dr., NC",
        "region": "SE",
        "is_canceled": True,
        "ride_manager": "Cheryl Newman",
        "manager_phone": "828-665-1531", 
        "manager_email": "cherylnewman@charter.net",
        "has_intro_ride": False,
        "ride_id": "14546",
        "distances": [
            {"distance": "50 miles", "date": "May 02, 2025", "start_time": "07:30 am"},
            {"distance": "25 miles", "date": "May 02, 2025", "start_time": "08:30 am"}
        ],
        "location_details": {
            "city": "Asheville",
            "state": "NC",
            "country": "USA"
        },
        "control_judges": [
            {"name": "Nick Kohut", "role": "Control Judge"}
        ],
        "description": "Cancelled due to venue conflict. We apologize for any inconvenience.",
        "directions": "From I-40, take exit 50B onto Hwy 25 South. Follow for 2 miles to Biltmore entrance."
    },
    "tevis_cup_event.html": {
        "name": "Western States Trail Ride (The Tevis Cup)",
        "source": "AERC",
        "event_type": "endurance",
        "date_start": "2025-07-12",
        "location": "Robie Park, CA",
        "region": "W",
        "is_canceled": False,
        "ride_manager": "Chuck Stalley",
        "manager_phone": "530-823-7616",
        "manager_email": "cstalley@saber.net",
        "website": "https://www.teviscup.org/",
        "has_intro_ride": False,
        "ride_id": "14492",
        "distances": [
            {"distance": "100 miles", "date": "Jul 12, 2025", "start_time": "05:15 am"}
        ],
        "location_details": {
            "city": "Truckee",
            "state": "CA",
            "country": "USA"
        },
        "coordinates": {
            "latitude": 39.23839,
            "longitude": -120.17357
        },
        "map_link": "https://www.google.com/maps/dir/?api=1&destination=39.23839,-120.17357",
        "control_judges": [
            {"name": "Michael S. Peralez", "role": "Control Judge"}
        ],
        "description": "The world's oldest 100-mile trail ride, established in 1955. Ride from Tahoe to Auburn in one day.",
        "directions": "Start is at Robie Park near Truckee, CA. Take I-80 to the Truckee exit, then follow Highway 267 north. Turn right onto Northwoods Blvd, then right onto Fairway Drive to Robie Park."
    },
    "belair_forest_event.html": {
        "name": "Belair Forest",
        "source": "AERC",
        "event_type": "endurance",
        "date_start": "2025-05-10",
        "location": "Belair Provincial Forest, Hwy 44 at Hwy 302, MB",
        "region": "MW",
        "is_canceled": False,
        "ride_manager": "Kelli Hayhurst",
        "manager_phone": "431-293-3233",
        "manager_email": "kellihayhurst64@gmail.com",
        "has_intro_ride": True,
        "ride_id": "14587",
        "distances": [
            {"distance": "25 miles", "date": "May 10, 2025", "start_time": "08:00 am"},
            {"distance": "50 miles", "date": "May 10, 2025", "start_time": "07:00 am"}
        ],
        "location_details": {
            "city": "Stead",
            "state": "MB",
            "country": "Canada"
        },
        "coordinates": {
            "latitude": 50.44538,
            "longitude": -96.443778
        },
        "map_link": "https://www.google.com/maps/dir/?api=1&destination=50.445380,-96.443778",
        "control_judges": [
            {"name": "Brittney Derksen", "role": "Control Judge"}
        ],
        "description": "Beautiful trails through the Manitoba boreal forest. Moderate terrain with some sandy sections. Great introduction to Canadian endurance riding.",
        "directions": "From Winnipeg, take Highway 44 east. Turn north onto Highway 302 in Belair. Look for the ride signs and event parking area."
    },
    "cuyama_pioneer_event.html": {
        "name": "Cuyama XP Pioneer - intro ride each day",
        "source": "AERC",
        "event_type": "endurance",
        "date_start": "2025-03-28",
        "location": "Cottonwood Canyon, New Cuyama CA",
        "region": "PS",
        "is_canceled": False,
        "ride_manager": "Ann Nicholson",
        "manager_phone": "907-821-1819",
        "manager_email": "annie@xprides.com",
        "website": "https://xprides.com",
        "has_intro_ride": True,
        "ride_id": "14457",
        "distances": [
            {"distance": "25 miles", "date": "Mar 28, 2025", "start_time": "07:00 am"},
            {"distance": "50 miles", "date": "Mar 28, 2025", "start_time": "07:00 am"},
            {"distance": "25 miles", "date": "Mar 29, 2025", "start_time": "07:00 am"},
            {"distance": "50 miles", "date": "Mar 29, 2025", "start_time": "07:00 am"},
            {"distance": "25 miles", "date": "Mar 30, 2025", "start_time": "07:00 am"},
            {"distance": "50 miles", "date": "Mar 30, 2025", "start_time": "07:00 am"}
        ],
        "location_details": {
            "city": "New Cuyama",
            "state": "CA",
            "country": "USA"
        },
        "coordinates": {
            "latitude": 35.006586,
            "longitude": -119.888513
        },
        "map_link": "https://www.google.com/maps/dir/?api=1&destination=35.006586,-119.888513",
        "control_judges": [
            {"name": "Dave Nicholson", "role": "Control Judge"}
        ]
    }
}

# List of sample event filenames for easy importing
EVENT_SAMPLES = list(EXPECTED_DATA.keys())

# Helper function to get expected data for a single event
def get_expected_data(filename: str) -> Dict[str, Any]:
    """
    Get the expected data for a specific HTML sample file.
    
    Args:
        filename: The filename of the HTML sample
        
    Returns:
        Dictionary containing the expected parsed data
        
    Raises:
        KeyError: If the filename does not exist in the expected data
    """
    if filename not in EXPECTED_DATA:
        raise KeyError(f"No expected data found for '{filename}'")
    
    return EXPECTED_DATA[filename] 