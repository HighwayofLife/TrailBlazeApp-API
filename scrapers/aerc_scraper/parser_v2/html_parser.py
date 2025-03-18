"""
Direct HTML parser for AERC calendar data using BeautifulSoup.
This parser directly extracts structured data from the AERC calendar HTML
without relying on AI.
"""

import logging
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from bs4 import BeautifulSoup

from scrapers.aerc_scraper.data_handler import DataHandler
from scrapers.schema import AERCEvent

logger = logging.getLogger(__name__)

class HTMLParser:
    """Parser for extracting structured event data directly from AERC HTML."""
    
    def __init__(self, debug_mode: bool = False):
        """Initialize the HTML parser with optional debug mode."""
        self.debug_mode = debug_mode
        self.metrics = {
            'events_found': 0,
            'events_extracted': 0,
            'links_total': 0,
            'website_links': 0,
            'flyer_links': 0,
            'map_links': 0,
            'parsing_errors': 0,
            'date_parsing_errors': 0,
            'validation_errors': 0,
        }
    
    def parse_html(self, html: str) -> List[Dict[str, Any]]:
        """
        Parse AERC calendar HTML and extract structured event data.
        
        Args:
            html: Raw HTML content from the AERC calendar
            
        Returns:
            List of raw event dictionaries
        """
        logger.info("Starting direct HTML parsing of AERC calendar data")
        raw_events = []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find all ride rows (calendar entries)
            ride_rows = soup.find_all('div', class_='calendarRow')
            self.metrics['events_found'] = len(ride_rows)
            
            logger.info(f"Found {len(ride_rows)} potential events in HTML")
            
            # Extract data from each row
            for i, row in enumerate(ride_rows):
                try:
                    raw_event = self._extract_event_data(row, i)
                    if raw_event:
                        raw_events.append(raw_event)
                        self.metrics['events_extracted'] += 1
                        
                        # Log extraction details in debug mode
                        if self.debug_mode:
                            logger.debug(f"Extracted event {i+1}/{len(ride_rows)}: {raw_event.get('name', 'Unknown')}")
                            if raw_event.get('website'):
                                logger.debug(f"  - Website: {raw_event.get('website')}")
                            if raw_event.get('flyer_url'):
                                logger.debug(f"  - Registration: {raw_event.get('flyer_url')}")
                    else:
                        logger.warning(f"Failed to extract event at index {i}")
                
                except Exception as e:
                    self.metrics['parsing_errors'] += 1
                    logger.error(f"Error parsing row {i}: {str(e)}")
            
            # Combine events with the same ride_id
            events = self._combine_events_with_same_ride_id(raw_events)
        
        except Exception as e:
            logger.error(f"Failed to parse HTML: {str(e)}")
            return []
        
        logger.info(f"Successfully extracted {len(events)} events from HTML")
        logger.info(f"Link statistics: {self.metrics['website_links']} websites, "
                   f"{self.metrics['flyer_links']} flyers, {self.metrics['map_links']} maps")
        
        return events
    
    def _combine_events_with_same_ride_id(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Combine events with the same ride_id into a single event.
        
        This handles multi-day events that may be listed as separate calendar entries
        but should be treated as a single event in our system.
        
        Args:
            events: List of raw event dictionaries
            
        Returns:
            List of combined event dictionaries
        """
        # If there are no events, return empty list
        if not events:
            return []
            
        # Group events by ride_id
        events_by_id = {}
        for event in events:
            ride_id = event.get('ride_id')
            # If event has no ride_id, treat it as a unique event
            if not ride_id:
                events_by_id[f"no_id_{id(event)}"] = [event]
                continue
                
            if ride_id not in events_by_id:
                events_by_id[ride_id] = []
            events_by_id[ride_id].append(event)
            
        # Combine events with the same ride_id
        combined_events = []
        for ride_id, events_list in events_by_id.items():
            # If there's only one event with this ride_id, add it directly
            if len(events_list) == 1:
                combined_events.append(events_list[0])
                continue
                
            # If there are multiple events with this ride_id, combine them
            logger.info(f"Combining {len(events_list)} events with ride_id {ride_id}")
            combined_event = self._merge_events(events_list)
            combined_events.append(combined_event)
            
        return combined_events
        
    def _merge_events(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge multiple events with the same ride_id into a single event.
        
        Args:
            events: List of event dictionaries to merge
            
        Returns:
            Merged event dictionary
        """
        # Use the first event as the base
        base_event = events[0].copy()
        
        # Initialize collection for multiple dates and distances
        all_distances = base_event.get('distances', []).copy()
        
        # Track min and max dates for date_start and date_end
        date_start = base_event.get('date_start')
        date_end = base_event.get('date_end', date_start)
        
        # Merge additional events into the base event
        for event in events[1:]:
            # Collect all distances
            event_distances = event.get('distances', [])
            for distance in event_distances:
                # Only add if not already present (avoid duplicates)
                if distance not in all_distances:
                    all_distances.append(distance)
            
            # Update date range
            event_date = event.get('date_start')
            if event_date:
                if not date_start or event_date < date_start:
                    date_start = event_date
                if not date_end or event_date > date_end:
                    date_end = event_date
                    
            # If any event is marked as having an intro ride, the combined event has one
            if event.get('has_intro_ride', False):
                base_event['has_intro_ride'] = True
                
            # If any event has a special property that the base doesn't, add it
            for key, value in event.items():
                if key not in base_event and value:
                    base_event[key] = value
        
        # Update the base event with merged data
        base_event['distances'] = all_distances
        base_event['date_start'] = date_start
        
        # Only set date_end if it's different from date_start
        if date_end and date_end != date_start:
            base_event['date_end'] = date_end
            
        # Set event duration flags and ride days
        if len(events) > 1:
            base_event['is_multi_day_event'] = True
            
            # Calculate ride days - either from date range or number of events
            if date_start and date_end and date_end != date_start:
                # Convert string dates to datetime objects before subtraction
                from datetime import datetime
                try:
                    start_date_obj = datetime.strptime(date_start, '%Y-%m-%d')
                    end_date_obj = datetime.strptime(date_end, '%Y-%m-%d')
                    delta = end_date_obj - start_date_obj
                    ride_days = delta.days + 1  # Include both start and end day
                except ValueError:
                    # If date parsing fails, fall back to number of events
                    ride_days = len(events)
            else:
                # If dates aren't reliable, use the number of events as an approximation
                ride_days = len(events)
                
            base_event['ride_days'] = ride_days
            
            # Set pioneer ride flag (3+ days)
            base_event['is_pioneer_ride'] = ride_days >= 3
        
        return base_event
    
    def _extract_event_data(self, row, index: int) -> Optional[Dict[str, Any]]:
        """Extract structured data from a single event row."""
        # Extract basic event information
        name_elem = row.select_one('span.rideName')
        if not name_elem:
            logger.warning(f"No ride name found for event at index {index}")
            return None
            
        name = name_elem.text.strip()
        
        # Clean up cancelled marker in name if present
        is_canceled = self._check_if_canceled(row)
        if is_canceled:
            # Remove "** Cancelled **" or similar text from the name
            name = re.sub(r'\s*\*+\s*Cancelled\s*\*+\s*', '', name, flags=re.IGNORECASE).strip()
        
        # Extract region
        region_elem = row.select_one('td.region')
        region = region_elem.text.strip() if region_elem else None
        
        # Extract date
        date = self._extract_date(row)
        if not date:
            logger.warning(f"Could not extract date for event: {name}")
            self.metrics['date_parsing_errors'] += 1
            # Fall back to current date for required field
            date = datetime.now().strftime('%Y-%m-%d')
        
        # Extract location
        location = self._extract_location(row)
        if not location:
            logger.warning(f"Could not extract location for event: {name}")
            location = "Unknown Location"
        
        # Extract links
        website, flyer_url, map_link = self._extract_links(row)
        
        # Extract ride manager info
        ride_manager, manager_email, manager_phone = self._extract_contact_info(row)
        
        # Extract distances
        distances = self._extract_distances(row)
        
        # Extract description
        description = self._extract_description(row)
        
        # Extract directions
        directions = self._extract_directions(row)
        
        # Extract cancellation status
        is_canceled = self._check_if_canceled(row)
        
        # Extract coordinates from map link if available
        coordinates = None
        if map_link:
            coordinates = self._extract_coordinates(map_link)
        
        # Extract control judges
        control_judges = self._extract_control_judges(row)
        
        # Check for intro ride
        has_intro_ride = self._check_has_intro_ride(row)
        
        # Extract city, state, and country from location
        city, state, country = self._extract_city_state_country(location)
        
        # Try to extract ride_id from the span tag attribute
        ride_id = None
        ride_id_elem = row.select_one('span.rideName')
        if ride_id_elem and ride_id_elem.has_attr('tag'):
            ride_id = ride_id_elem['tag']
        
        # Build event object with field names matching the validator's expectations
        event = {
            'name': name,               
            'date_start': date,         
            'region': region,
            'location': location,
            'distances': distances,
            'ride_manager': ride_manager,
            'description': description,
            'directions': directions,
            'is_canceled': is_canceled,
            'has_intro_ride': has_intro_ride,
            'control_judges': control_judges,
            'source': 'AERC',           # Required field that was missing
            'event_type': 'endurance',  # Default for AERC events
            # Default values for multi-day event flags - these will be updated during event merging if needed
            'is_multi_day_event': False,
            'is_pioneer_ride': False,
            'ride_days': 1
        }
        
        # Add location_details as a structured object
        event['location_details'] = {
            'city': city,
            'state': state,
            'country': country
        }
        
        # Add ride_id if available
        if ride_id:
            event['ride_id'] = ride_id
            
        # Add coordinates if available
        if coordinates:
            event['coordinates'] = coordinates
        
        # Add optional fields if present
        if website:
            event['website'] = website
            
        if flyer_url:
            event['flyer_url'] = flyer_url
            
        if map_link:
            event['map_link'] = map_link
            
        # Add contact info
        if manager_email or manager_phone:
            event['ride_manager_contact'] = {}
            if manager_email:
                event['ride_manager_contact']['email'] = manager_email
            if manager_phone:
                event['ride_manager_contact']['phone'] = manager_phone
        
        return event
    
    def _extract_date(self, row) -> Optional[str]:
        """Extract and format event date."""
        # First try the span.rideDate
        date_text = None
        date_elem = row.select_one('span.rideDate')
        if date_elem:
            date_text = date_elem.text.strip()
        
        # If that fails, look for any date-like text in the row
        if not date_text:
            # Look for common date patterns in the HTML
            full_text = row.get_text()
            # Look for MM/DD/YYYY pattern
            date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{2,4})', full_text)
            if date_match:
                date_text = date_match.group(1)
            
            # If still not found, look for month names
            if not date_text:
                month_pattern = r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* (\d{1,2})(?:st|nd|rd|th)?,? (\d{4})'
                month_match = re.search(month_pattern, full_text, re.IGNORECASE)
                if month_match:
                    month, day, year = month_match.groups()
                    date_text = f"{month} {day}, {year}"
        
        if not date_text:
            return None

        # Clean up date text
        date_text = re.sub(r'\s+', ' ', date_text.strip())
        
        # Try to parse with different formats
        date_formats = [
            '%m/%d/%Y',        # MM/DD/YYYY
            '%m/%d/%y',         # MM/DD/YY
            '%b %d, %Y',       # Month DD, YYYY
            '%B %d, %Y',       # Month DD, YYYY
            '%Y-%m-%d',        # YYYY-MM-DD
        ]
        
        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(date_text, fmt)
                return parsed_date.strftime('%Y-%m-%d')  # Convert to YYYY-MM-DD
            except ValueError:
                continue
        
        # If we get here, no format matched
        logger.warning(f"Could not parse date: '{date_text}'")
        return None
    
    def _extract_location(self, row) -> str:
        """Extract event location."""
        # First try to find location in the second row, which usually contains the location data
        location_text = ""
        
        try:
            # Look for the second table row which contains the location information
            location_rows = row.select('tr.fix-jumpy')
            if len(location_rows) > 1:
                # The location is in the second row and third <td> cell
                second_row = location_rows[1]
                location_cell = second_row.select_one('td:nth-child(3)')
                if location_cell:
                    # Extract the text, but remove any links or extra info
                    cell_text = location_cell.get_text(strip=True).split('\n')[0]
                    # Remove "Click Here for Directions" or similar text
                    cell_text = re.sub(r'Click Here for Directions.*', '', cell_text, flags=re.IGNORECASE).strip()
                    
                    # Check if there's actual location text and not just a label like "Website" or "Entry/Flyer"
                    if cell_text and not any(s in cell_text.lower() for s in ['entry', 'flyer', 'website']):
                        location_text = cell_text
        except Exception as e:
            if self.debug_mode:
                logger.warning(f"Error extracting location from second row: {e}")
        
        # If not found above or empty, try looking in the detailed table
        if not location_text:
            try:
                # Look for the labeled location in the detailed data table
                # Format: <td>Ride</td><td>Location : </td><td>Actual Location</td>
                location_rows = row.select('table.detailData tr')
                for location_row in location_rows:
                    # Look for the row that contains "Location : "
                    if location_row.get_text().find("Location :") != -1:
                        cells = location_row.select('td')
                        if len(cells) > 2:  # Should have at least 3 cells
                            # The location is in the 3rd cell
                            detail_text = cells[2].get_text(strip=True).split('\n')[0]
                            # Remove "Click Here for Directions" or similar text
                            location_text = re.sub(r'Click Here for Directions.*', '', detail_text, flags=re.IGNORECASE).strip()
                        break
            except Exception as e:
                if self.debug_mode:
                    logger.warning(f"Error extracting location from detail table: {e}")
        
        # Fallback: try to find other location indicators
        if not location_text:
            try:
                location_elem = row.select_one('span.rideLocation')
                if location_elem:
                    location_text = location_elem.text.strip()
            except Exception as e:
                if self.debug_mode:
                    logger.warning(f"Error extracting location from span.rideLocation: {e}")
        
        # Last fallback - Look for any span with meaningful text
        if not location_text:
            for elem in row.select('span:not(.rideName):not(.rideDate)'):
                text = elem.text.strip()
                if text and len(text) > 5 and not text.startswith('http') and text != "Ride Details":
                    location_text = text
                    break
        
        # For cancelled events, the location might include a cancellation notice
        # Remove it to get the actual location
        if location_text:
            location_text = re.sub(r'\*+\s*cancelled\s*\*+', '', location_text, flags=re.IGNORECASE).strip()
        
        return location_text or "Unknown Location"
    
    def _extract_links(self, row) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Extract website, flyer, and map links from event."""
        website = None
        flyer_url = None
        map_link = None
        
        links = row.find_all('a')
        self.metrics['links_total'] += len(links)
        
        for link in links:
            href = link.get('href')
            text = link.get_text(strip=True).lower()
            
            if not href:
                continue
                
            # Categorize the link
            if 'maps.google' in href or 'map' in href.lower() or any(word in text for word in ['directions', 'map', 'location']):
                map_link = href
                self.metrics['map_links'] += 1
            elif href.endswith('.pdf') or any(word in text for word in ['entry', 'flyer', 'form']):
                flyer_url = href
                self.metrics['flyer_links'] += 1
            elif 'http' in href and 'maps.google' not in href and any(word in text for word in ['website', 'details', 'info', 'site', 'follow']):
                website = href
                self.metrics['website_links'] += 1
        
        return website, flyer_url, map_link
    
    def _extract_contact_info(self, row) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Extract ride manager and contact information."""
        ride_manager = None
        manager_email = None
        manager_phone = None
        
        # Look for ride manager pattern: usually "RM: Name"
        text = row.get_text()
        rm_match = re.search(r'(?:RM|Ride Manager|RideManager)[:\s]+([^,\n]+)', text)
        if rm_match:
            ride_manager = rm_match.group(1).strip()
        
        # Look for email addresses
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
        if email_match:
            manager_email = email_match.group(0)
        
        # Look for phone numbers (simple pattern)
        phone_match = re.search(r'(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})', text)
        if phone_match:
            # Keep the original phone format with dashes, parentheses, etc.
            manager_phone = phone_match.group(1)
            
            # Previous formatting code (commented out)
            # Format the phone number to match the required pattern
            # Remove all non-digit characters except for leading + sign
            # phone = phone_match.group(1)
            # formatted_phone = ''.join([c for c in phone if c.isdigit() or (c == '+' and phone.index(c) == 0)])
            # 
            # # Ensure the phone number has at least 10 digits
            # if len(formatted_phone) >= 10:
            #    manager_phone = formatted_phone
        
        return ride_manager, manager_email, manager_phone
    
    def _extract_distances(self, row) -> List[Dict[str, str]]:
        """Extract distance information with start times."""
        distances = []
        
        # Get the full text for regex pattern matching
        full_text = row.get_text()
        
        # First try to find structured distance data
        distance_elems = row.select('span.distance')
        if distance_elems:
            for elem in distance_elems:
                distances.append({'distance': elem.text.strip()})
        else:
            # Look specifically for the pattern in the detailed event data table
            # Pattern found in the event details: "<td>Distances</td><td>25&nbsp;</td><td>on Oct 10, 2025 starting at 08:00 am</td>"
            distance_rows = row.select('tr')
            for distance_row in distance_rows:
                cells = distance_row.select('td')
                if len(cells) >= 3 and cells[0].text.strip() == 'Distances':
                    distance_value = cells[1].text.strip().replace('\xa0', ' ').strip()
                    start_time_text = cells[2].text.strip()
                    
                    # Extract the start time from the text using regex
                    start_time_match = re.search(r'starting at\s+(\d{1,2}:\d{2}\s*(?:am|pm|AM|PM)|(?:\d{1,2}\s*(?:am|pm|AM|PM)))', start_time_text)
                    start_time = start_time_match.group(1).strip() if start_time_match else None
                    
                    # Filter out invalid distances
                    try:
                        dist_num = int(distance_value)
                        if dist_num < 10 or dist_num > 200:
                            continue
                    except ValueError:
                        # If it's not a plain number, try to extract just the number part
                        num_match = re.search(r'(\d+)', distance_value)
                        if num_match:
                            try:
                                dist_num = int(num_match.group(1))
                                if dist_num < 10 or dist_num > 200:
                                    continue
                            except ValueError:
                                pass
                    
                    distance_obj = {'distance': distance_value}
                    if start_time:
                        distance_obj['start_time'] = start_time
                    
                    distances.append(distance_obj)
            
            # If no distance rows were found using the table structure, fall back to regex patterns
            if not distances:
                # Try to find distances with start times pattern
                # Pattern: "X miles on <date> starting at X:XXam/pm" or just "X" followed by start time info
                start_time_pattern = r'((?:^|[^\d])(\d{1,3})(?:\s?(?:mi|km|mile|miles))?(?:[^\d]|$))(?:\son\s[\w\s,]+\sstarting\sat\s(\d{1,2}:\d{2}\s?(?:am|pm|AM|PM)|(?:\d{1,2}\s?(?:am|pm|AM|PM))))?'
                start_time_matches = re.findall(start_time_pattern, full_text)
                
                if start_time_matches:
                    for match in start_time_matches:
                        # Extract the number from the matched text
                        dist_num_str = match[1].strip() if len(match) > 1 else None
                        distance_value = match[0].strip()
                        start_time_value = match[2].strip() if len(match) > 2 and match[2] else None
                        
                        # Filter out invalid distances
                        if dist_num_str and dist_num_str.isdigit():
                            dist_num = int(dist_num_str)
                            if dist_num < 10 or dist_num > 200:
                                continue
                        
                        distance_obj = {'distance': dist_num_str if dist_num_str else distance_value}
                        if start_time_value:
                            distance_obj['start_time'] = start_time_value
                        
                        distances.append(distance_obj)
                else:
                    # Fall back to simple distance pattern matching
                    distance_pattern = r'(?:^|\s)(\d{1,3}(?:\s?(?:mi|km|mile|miles))?(?:/\d{1,3}(?:\s?(?:mi|km|mile|miles))?)*)(?:\s|$)'
                    distance_matches = re.findall(distance_pattern, full_text)
                    
                    for match in distance_matches:
                        # Split multiple distances (e.g., "25/50/75")
                        for dist in match.split('/'):
                            dist = dist.strip()
                            
                            # Filter out invalid distances
                            if dist.isdigit():
                                dist_num = int(dist)
                                if dist_num < 10 or dist_num > 200:
                                    continue
                            
                            distances.append({'distance': dist})
        
        # If we still have no distances, look for any numbers that might be distances
        if not distances:
            # Look for just numbers (likely miles) in the text
            number_pattern = r'(?:^|\s)(\d{1,3})(?:\s|$)'
            number_matches = re.findall(number_pattern, full_text)
            
            for match in number_matches:
                # Only add numbers in a reasonable range for ride distances (10-100)
                num = int(match)
                if 10 <= num <= 100:
                    distances.append({'distance': f"{match} miles"})
        
        # Remove duplicates based on distance value
        filtered_distances = []
        seen_distances = set()
        
        for dist in distances:
            dist_val = dist['distance'].lower()
            if dist_val not in seen_distances:
                filtered_distances.append(dist)
                seen_distances.add(dist_val)
        
        # Look for any start times not associated with specific distances
        if filtered_distances and not any('start_time' in d for d in filtered_distances):
            time_pattern = r'start(?:ing|s)?\s+at\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM))'
            time_matches = re.findall(time_pattern, full_text)
            
            if time_matches:
                # Apply the first start time found to all distances without times
                for i in range(len(filtered_distances)):
                    if 'start_time' not in filtered_distances[i]:
                        filtered_distances[i]['start_time'] = time_matches[0]
        
        # Ensure each distance has at least an empty string for start_time to avoid None errors
        for d in filtered_distances:
            if 'start_time' not in d:
                d['start_time'] = ''
                
        return filtered_distances
    
    def _extract_description(self, row) -> Optional[str]:
        """Extract event description from the HTML."""
        description_elem = row.select_one('div.details')
        if description_elem:
            # Extract text but remove any HTML tags
            description = description_elem.get_text(strip=True)
            return description
        
        # Fallback: try to find a paragraph with description-like content
        for p in row.select('p'):
            text = p.get_text(strip=True)
            if len(text) > 30 and not any(keyword in text.lower() for keyword in ['directions', 'map', 'contact']):
                return text
                
        # If still not found, use any text that might contain description
        full_text = row.get_text(strip=True)
        # Try to extract a meaningful portion
        if len(full_text) > 50:
            # Clean up the text and remove common non-description parts
            cleaned = re.sub(r'(?:RM|Ride Manager|RideManager)[:\s]+([^,\n]+)', '', full_text)
            cleaned = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '', cleaned)
            cleaned = re.sub(r'(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})', '', cleaned)
            # Remove dates and times
            cleaned = re.sub(r'\d{1,2}/\d{1,2}/\d{2,4}', '', cleaned)
            cleaned = re.sub(r'\d{1,2}:\d{2}\s*(?:am|pm|AM|PM)', '', cleaned)
            
            # If we still have significant text, use it as description
            if len(cleaned) > 50:
                return cleaned.strip()
        
        return "No description available"
    
    def _extract_directions(self, row) -> Optional[str]:
        """Extract directions information."""
        directions_elem = row.select_one('div.directions')
        if directions_elem:
            return directions_elem.get_text(strip=True)
        
        # Look for any element with directions information
        for elem in row.select('p, div, span'):
            text = elem.get_text(strip=True).lower()
            if 'directions' in text and len(text) > 20:
                return elem.get_text(strip=True)
        
        # If no specific directions, try to extract from map link text
        map_links = [a for a in row.select('a') if 'map' in a.get_text(strip=True).lower() or 'directions' in a.get_text(strip=True).lower()]
        if map_links:
            link_text = map_links[0].get_text(strip=True)
            if len(link_text) > 10:  # Not just "Map" or "Directions"
                return link_text
        
        return None
    
    def _check_if_canceled(self, row) -> bool:
        """Check if an event is canceled."""
        # Look for canceled or cancelled text in the HTML
        text = row.get_text().lower()
        return any(word in text for word in ['canceled', 'cancelled', 'postponed'])
    
    def _extract_coordinates(self, map_link) -> Optional[Dict[str, float]]:
        """Extract coordinates from Google Maps link if present."""
        if not map_link:
            return None
            
        # Extract coordinates from Google Maps URL
        # Format can be maps.google.com/maps?q=lat,lng or maps.google.com/?q=lat,lng
        coord_match = re.search(r'[?&]q=(-?\d+\.\d+),(-?\d+\.\d+)', map_link)
        if coord_match:
            lat = float(coord_match.group(1))
            lng = float(coord_match.group(2))
            return {'latitude': lat, 'longitude': lng}
        
        # Try another common format (@lat,lng,zoom)
        coord_match2 = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', map_link)
        if coord_match2:
            lat = float(coord_match2.group(1))
            lng = float(coord_match2.group(2))
            return {'latitude': lat, 'longitude': lng}
            
        # Try destination format (destination=lat,lng)
        coord_match3 = re.search(r'destination=(-?\d+\.\d+),(-?\d+\.\d+)', map_link)
        if coord_match3:
            lat = float(coord_match3.group(1))
            lng = float(coord_match3.group(2))
            return {'latitude': lat, 'longitude': lng}
            
        return None
        
    def _extract_control_judges(self, row) -> List[Dict[str, str]]:
        """Extract control judges from event data."""
        judges = []
        
        # Look for control judge pattern
        text = row.get_text()
        
        # Pattern: "Control Judge: Name" or "Control Judges: Name1, Name2"
        judges_pattern = r'Control Judge(?:s)?:\s*([^,\n]+(?:,\s*[^,\n]+)*)'
        judges_match = re.search(judges_pattern, text, re.IGNORECASE)
        
        if judges_match:
            judge_names = [name.strip() for name in judges_match.group(1).split(',')]
            for name in judge_names:
                if name:  # Ensure name is not empty
                    judges.append({
                        'name': name,
                        'role': 'Control Judge'
                    })
                    
        # Look for other specific roles
        role_patterns = [
            (r'Vet Judge(?:s)?:\s*([^,\n]+(?:,\s*[^,\n]+)*)', 'Vet Judge'),
            (r'Technical Delegate(?:s)?:\s*([^,\n]+(?:,\s*[^,\n]+)*)', 'Technical Delegate'),
            (r'Steward(?:s)?:\s*([^,\n]+(?:,\s*[^,\n]+)*)', 'Steward')
        ]
        
        for pattern, role in role_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                role_names = [name.strip() for name in match.group(1).split(',')]
                for name in role_names:
                    if name:  # Ensure name is not empty
                        judges.append({
                            'name': name,
                            'role': role
                        })
        
        return judges
        
    def _check_has_intro_ride(self, row) -> bool:
        """Check if the event has an intro ride option."""
        text = row.get_text().lower()
        
        # Look for intro ride keywords
        intro_keywords = [
            'intro ride', 'introductory ride', 'intro distance', 
            'novice ride', 'beginner ride', 'fun ride', 'has intro ride'
        ]
        
        # Check for red colored intro ride marker
        intro_marker = row.select_one('span[style*="color: red"]')
        if intro_marker and 'intro' in intro_marker.text.lower():
            return True
            
        # Check text for intro keywords
        return any(keyword in text for keyword in intro_keywords)
        
    def _extract_city_state_country(self, location: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Extract city, state, and country from location string."""
        if not location or location == "Unknown Location":
            return None, None, "USA"
        
        # Default country is USA, will be overridden if Canadian province or other identifiers are found
        country = "USA"
        city = None
        state = None
            
        # Check for Canadian provinces - both abbreviations and full names
        canadian_provinces = {
            'AB': 'Alberta', 'BC': 'British Columbia', 'MB': 'Manitoba', 'NB': 'New Brunswick',
            'NL': 'Newfoundland and Labrador', 'NS': 'Nova Scotia', 'NT': 'Northwest Territories',
            'NU': 'Nunavut', 'ON': 'Ontario', 'PE': 'Prince Edward Island', 'QC': 'Quebec',
            'SK': 'Saskatchewan', 'YT': 'Yukon'
        }
        
        # Check for explicit Canadian content first
        if 'Canada' in location or 'Manitoba' in location:
            country = "Canada"
            
        # Special checks for Manitoba content
        if 'Manitoba' in location:
            state = 'MB'
            
        # Identify Canadian provinces with word boundaries and various separators
        for province_code in canadian_provinces.keys():
            # Check for province code with various delimiters or at the end of a string
            if (f' {province_code}' in location or f', {province_code}' in location or 
                f' {province_code},' in location or location.endswith(f' {province_code}')):
                country = "Canada"
                state = province_code
                break
        
        # Pattern 1: "City, ST" or "City, State"
        city_state_match = re.search(r'([^,]+),\s*([A-Z]{2}|[A-Za-z\s]+)(?:,\s*(.+))?$', location)
        if city_state_match:
            city = city_state_match.group(1).strip()
            state_or_prov = city_state_match.group(2).strip()
            
            # If there's a third group, it might be the country
            if city_state_match.group(3):
                possible_country = city_state_match.group(3).strip()
                if possible_country.lower() == 'canada':
                    country = 'Canada'
            
            # Check if the state is a Canadian province abbreviation
            if state_or_prov in canadian_provinces:
                country = 'Canada'
                state = state_or_prov
            # If state is a longer value, check if it's a full province name
            elif state_or_prov in canadian_provinces.values():
                country = 'Canada'
                # Find the abbreviation for this province
                for abbr, full in canadian_provinces.items():
                    if full == state_or_prov:
                        state = abbr
                        break
            else:
                state = state_or_prov
                
                # If state is not 2 letters, try to normalize it
                if len(state) > 2:
                    # This is a simple example - you might want a more comprehensive state mapping
                    state_map = {
                        'ALABAMA': 'AL', 'ALASKA': 'AK', 'ARIZONA': 'AZ', 'ARKANSAS': 'AR',
                        'CALIFORNIA': 'CA', 'COLORADO': 'CO', 'CONNECTICUT': 'CT', 'DELAWARE': 'DE',
                        'FLORIDA': 'FL', 'GEORGIA': 'GA', 'HAWAII': 'HI', 'IDAHO': 'ID',
                        'ILLINOIS': 'IL', 'INDIANA': 'IN', 'IOWA': 'IA', 'KANSAS': 'KS',
                        'KENTUCKY': 'KY', 'LOUISIANA': 'LA', 'MAINE': 'ME', 'MARYLAND': 'MD',
                        'MASSACHUSETTS': 'MA', 'MICHIGAN': 'MI', 'MINNESOTA': 'MN', 'MISSISSIPPI': 'MS',
                        'MISSOURI': 'MO', 'MONTANA': 'MT', 'NEBRASKA': 'NE', 'NEVADA': 'NV',
                        'NEW HAMPSHIRE': 'NH', 'NEW JERSEY': 'NJ', 'NEW MEXICO': 'NM', 'NEW YORK': 'NY',
                        'NORTH CAROLINA': 'NC', 'NORTH DAKOTA': 'ND', 'OHIO': 'OH', 'OKLAHOMA': 'OK',
                        'OREGON': 'OR', 'PENNSYLVANIA': 'PA', 'RHODE ISLAND': 'RI', 'SOUTH CAROLINA': 'SC',
                        'SOUTH DAKOTA': 'SD', 'TENNESSEE': 'TN', 'TEXAS': 'TX', 'UTAH': 'UT',
                        'VERMONT': 'VT', 'VIRGINIA': 'VA', 'WASHINGTON': 'WA', 'WEST VIRGINIA': 'WV',
                        'WISCONSIN': 'WI', 'WYOMING': 'WY'
                    }
                    normalized_state = state.upper()
                    if normalized_state in state_map:
                        state = state_map[normalized_state]
            
            return city, state, country
        
        # Look for location patterns with province/state at the end
        # This handles patterns like "Belair Provincial Forest, Hwy 44 at Hwy 302, Stead MB"
        province_pattern = re.search(r'(\w+)\s+([A-Z]{2})(?:\s|$)', location)
        if province_pattern:
            city_candidate = province_pattern.group(1).strip()
            province_candidate = province_pattern.group(2).strip()
            
            if province_candidate in canadian_provinces:
                country = "Canada"
                state = province_candidate
                city = city_candidate
                return city, state, country
                
        # Look for a pattern where the city and province/state are at the end
        # e.g., "Something, Something, City ST" or "Something, City ST"
        end_location_pattern = re.search(r',\s*([^,]+)\s+([A-Z]{2})\s*$', location)
        if end_location_pattern:
            city_candidate = end_location_pattern.group(1).strip()
            state_candidate = end_location_pattern.group(2).strip()
            
            # If state is a Canadian province, set country to Canada
            if state_candidate in canadian_provinces:
                country = "Canada"
                
            return city_candidate, state_candidate, country
                
        # General fallback for locations with commas
        location_parts = location.split(',')
        if len(location_parts) >= 2:
            # Last part might contain city and state/province
            last_part = location_parts[-1].strip()
            
            # Look for patterns like "City MB" or "City, MB"
            province_pattern = re.search(r'([^,]+)\s+([A-Z]{2})\b', last_part)
            if province_pattern:
                city = province_pattern.group(1).strip()
                state = province_pattern.group(2).strip()
                if state in canadian_provinces:
                    country = "Canada"
            else:
                # Check if it contains state and country
                state_country_match = re.search(r'([A-Z]{2})\s+(.+)$', last_part)
                if state_country_match:
                    state = state_country_match.group(1)
                    possible_country = state_country_match.group(2).strip()
                    if possible_country.lower() == 'canada':
                        country = 'Canada'
                else:
                    # Last part might be just a state
                    state_match = re.search(r'\b([A-Z]{2})\b', last_part)
                    if state_match:
                        state = state_match.group(1)
                        
                        # If there's more in the last part, it might be city + state
                        city_state_split = last_part.split()
                        if len(city_state_split) > 1 and city_state_split[-1] == state:
                            city = ' '.join(city_state_split[:-1])
                    
                # If we still don't have a city, use the second to last part
                if len(location_parts) >= 2 and not city:
                    city = location_parts[-2].strip()
        
        # Final check for Canadian provinces
        if state and state in canadian_provinces:
            country = 'Canada'
            
        # Special case for Manitoba/Canadian locations: check for Manitoba-related text in description
        if (state == 'MB' or 'Manitoba' in location or
            any(prov in location for prov in canadian_provinces.values())):
            country = 'Canada'
            
            # If we have MB state and no city, try to extract city from the location string
            if state == 'MB' and not city:
                # Try to find locations commonly associated with Manitoba events
                mb_location_match = re.search(r'(Stead|Belair|Winnipeg)', location)
                if mb_location_match:
                    city = mb_location_match.group(1)
        
        # Fallback for Canadian province but no city yet
        if country == 'Canada' and state and not city:
            # Look for the last comma-separated part before any mention of the province
            prov_index = location.find(state)
            if prov_index > 0:
                # Get text before the province
                before_prov = location[:prov_index].strip()
                parts = before_prov.split(',')
                if parts:
                    potential_city = parts[-1].strip()
                    # Clean up any highway references or other non-city text
                    potential_city = re.sub(r'(Hwy|Highway|Rd|Road|St|Street|Ave|Avenue)\s+\d+.*', '', potential_city).strip()
                    if potential_city and not potential_city.endswith(tuple(['Hwy', 'Highway', 'Rd', 'Road', 'St', 'Street', 'Ave', 'Avenue'])):
                        city = potential_city
        
        # Force Canada country for MB state
        if state == 'MB':
            country = 'Canada'
                
        return city, state, country
        
    def _extract_city_state(self, location: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract city and state from location string (backward compatibility)."""
        city, state, _ = self._extract_city_state_country(location)
        return city, state
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get parser metrics."""
        return self.metrics 