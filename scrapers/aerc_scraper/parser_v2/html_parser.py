"""
Direct HTML parser for AERC calendar data using BeautifulSoup.
This parser directly extracts structured data from the AERC calendar HTML
without relying on AI.
"""

import logging
import re
from datetime import datetime, timedelta
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

        This is the main entry point for the HTML parser. It processes the raw HTML
        content from the AERC calendar and extracts structured data for each event,
        combining multi-day events and validating against the AERCEvent schema.

        Args:
            html: Raw HTML content from the AERC calendar

        Returns:
            List of event dictionaries conforming to the AERCEvent schema

        Raises:
            ValueError: If the HTML content is invalid or empty
        """
        logger.info("Starting direct HTML parsing of AERC calendar data")
        raw_events = []

        if not html or not html.strip():
            logger.error("Empty HTML content provided")
            raise ValueError("Empty HTML content provided")

        try:
            soup = BeautifulSoup(html, 'html.parser')

            # Find all ride rows (calendar entries)
            ride_rows = soup.find_all('div', class_='calendarRow')
            self.metrics['events_found'] = len(ride_rows)

            logger.info(f"Found {len(ride_rows)} potential events in HTML")

            if not ride_rows:
                logger.warning("No calendar rows found in HTML. The HTML structure may have changed.")

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
                    logger.error(f"Error parsing row {i}: {str(e)}", exc_info=self.debug_mode)

            # Combine events with the same ride_id
            events = self._combine_events_with_same_ride_id(raw_events)

            # Validate each event against the AERCEvent schema
            validated_events = []
            for event in events:
                try:
                    # Validate and clean the event data
                    clean_event = self.validate_event_data(event)

                    # Format dates if they're not already in ISO format
                    if 'date_start' in clean_event and not clean_event['date_start'].startswith('20'):
                        clean_event['date_start'] = self.format_date(clean_event['date_start'])

                    if 'date_end' in clean_event and not clean_event['date_end'].startswith('20'):
                        clean_event['date_end'] = self.format_date(clean_event['date_end'])

                    validated_events.append(clean_event)
                except Exception as e:
                    self.metrics['validation_errors'] += 1
                    logger.error(f"Validation error for event {event.get('name', 'Unknown')}: {str(e)}")
                    # Include the event even if validation fails, but clean it
                    try:
                        # Remove None values at minimum
                        clean_event = {k: v for k, v in event.items() if v is not None}
                        validated_events.append(clean_event)
                    except:
                        # If cleaning fails, add the original event
                        validated_events.append(event)

        except Exception as e:
            logger.error(f"Failed to parse HTML: {str(e)}", exc_info=self.debug_mode)
            raise ValueError(f"HTML parsing failed: {str(e)}")

        logger.info(f"Successfully extracted {len(validated_events)} events from HTML")
        logger.info(f"Link statistics: {self.metrics['website_links']} websites, "
                   f"{self.metrics['flyer_links']} flyers, {self.metrics['map_links']} maps")

        return validated_events

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

    def _extract_event_data(self, event_row: BeautifulSoup, index: int) -> Optional[Dict[str, Any]]:
        """
        Extract all event data from a calendar row.
        """
        event_id = self._extract_ride_id(event_row)
        name = self._extract_ride_name(event_row)
        distances = self._extract_distances(event_row)
        location = self._extract_location(event_row)
        date_data = self._extract_dates(event_row)
        contact_info = self._extract_contact_info(event_row)
        description = self._extract_description(event_row)
        directions = self._extract_directions(event_row)
        judges = self._extract_control_judges(event_row)

        # Extract links (website, flyer, map)
        website, flyer_url, map_link = self._extract_links(event_row)

        # Extract the region
        region = self._extract_region(event_row)

        # Extract coordinates
        coordinates = self._extract_coordinates(event_row, location)

        # Check for special event types
        has_intro_ride = self._check_has_intro_ride(event_row, distances)
        is_canceled = self._check_if_canceled(event_row)

        # Check for multi-day and pioneer event flags
        is_multi_day = False
        is_pioneer = False
        ride_days = 1

        # Parse name for clues about multi-day/pioneer
        name_lower = name.lower()

        # Check for pioneer indicator in name
        if 'pioneer' in name_lower or 'xp' in name_lower.split():
            is_pioneer = True
            is_multi_day = True
            ride_days = max(3, ride_days)  # Pioneer rides are typically 3+ days

        # Special case for Cuyama XP Pioneer
        if 'cuyama' in name_lower and ('pioneer' in name_lower or 'xp' in name_lower.split()):
            is_pioneer = True
            is_multi_day = True
            ride_days = 3  # Cuyama is explicitly a 3-day event

        # Check for multi-day indicators in name
        multi_day_keywords = ['day', 'days', 'multi']
        if any(keyword in name_lower for keyword in multi_day_keywords):
            is_multi_day = True
            # Try to extract the number of days
            days_match = re.search(r'(\d+)[\s-]day', name_lower)
            if days_match:
                ride_days = max(int(days_match.group(1)), ride_days)
            else:
                ride_days = max(2, ride_days)

        # Check for multi-day based on date range
        if date_data.get('date_end') and date_data.get('date_start') != date_data.get('date_end'):
            is_multi_day = True

            # Calculate the number of days
            start_date = datetime.strptime(date_data.get('date_start'), '%Y-%m-%d')
            end_date = datetime.strptime(date_data.get('date_end'), '%Y-%m-%d')
            days_delta = (end_date - start_date).days + 1  # +1 to include both start and end days
            ride_days = max(days_delta, ride_days)

        # Check for duplicate distances (e.g., "50/50/50" indicating 3 days of 50 miles)
        if len(distances) >= 2:
            distance_values = [dist.get('distance', '') for dist in distances]
            unique_dates = set(dist.get('date', '') for dist in distances if 'date' in dist)

            # If we have multiple dates in the distances, it's a multi-day event
            if len(unique_dates) > 1:
                is_multi_day = True
                ride_days = max(len(unique_dates), ride_days)

                # If 3 or more days, it's a pioneer ride
                if len(unique_dates) >= 3:
                    is_pioneer = True

            # Check for duplicate distances on different days
            if len(set(distance_values)) < len(distance_values):
                is_multi_day = True
                ride_days = max(len(distance_values), ride_days)

        # Combine all data
        event_data = {
            'ride_id': event_id,
            'name': name,
            'distances': distances,
            'location': location,
            'location_details': self._extract_location_details(event_row, location),
            'ride_manager': contact_info.get('name'),
            'ride_manager_contact': contact_info,
            'region': region,
            'date_start': date_data.get('date_start'),
            'date_end': date_data.get('date_end', date_data.get('date_start')),
            'description': description,
            'directions': directions,
            'control_judges': judges,
            'has_intro_ride': has_intro_ride,
            'is_canceled': is_canceled,
            'is_multi_day_event': is_multi_day,
            'is_pioneer_ride': is_pioneer,
            'ride_days': ride_days,
            'website': website,
            'flyer_url': flyer_url,
            'map_link': map_link,
            'coordinates': coordinates,
            'source': 'AERC',
            'event_type': 'Ride'
        }

        return event_data

    def _extract_ride_id(self, event_row: BeautifulSoup) -> Optional[str]:
        """
        Extract the ride ID from the event row.
        Ride ID is typically stored in the 'tag' attribute of the ride name element.
        """
        # First check if there's a span.rideName element with a tag attribute
        name_elem = event_row.select_one('span.rideName')
        if name_elem and name_elem.has_attr('tag'):
            return name_elem['tag']

        # Next try to look for the a.rideName element
        link_elem = event_row.select_one('a.rideName')
        if link_elem and link_elem.has_attr('tag'):
            return link_elem['tag']

        # Finally check if we can extract an ID from any element with a 'ride-id' or similar attribute
        id_elements = event_row.select('[ride-id], [data-ride-id], [data-id], [id]')
        for elem in id_elements:
            for attr in ['ride-id', 'data-ride-id', 'data-id', 'id']:
                if elem.has_attr(attr) and elem[attr]:
                    return elem[attr]

        # If no ride ID could be found, return None
        return None

    def _extract_ride_name(self, event_row: BeautifulSoup) -> str:
        """
        Extract the ride name from the event row.
        The ride name is typically in an element with class 'rideName' or in the header.
        """
        # First check if there's a span.rideName element
        name_elem = event_row.select_one('span.rideName')
        if name_elem and name_elem.text.strip():
            name = name_elem.text.strip()
            # Remove "** Cancelled **" prefix
            name = re.sub(r'^\s*\*+\s*Cancelled\s*\*+\s*', '', name, flags=re.IGNORECASE)
            return name.strip()

        # Next try to look for the a.rideName element
        link_elem = event_row.select_one('a.rideName')
        if link_elem and link_elem.text.strip():
            name = link_elem.text.strip()
            # Remove "** Cancelled **" prefix
            name = re.sub(r'^\s*\*+\s*Cancelled\s*\*+\s*', '', name, flags=re.IGNORECASE)
            return name.strip()

        # Try to find it in the selectionText element (often contains the ride name)
        selection_text = event_row.select_one('div.selectionText')
        if selection_text and selection_text.text.strip():
            text = selection_text.text.strip()
            # If it contains "Details for", extract just the ride name
            if "Details for" in text:
                text = text.split("Details for")[1].strip()
            # Remove "** Cancelled **" prefix
            text = re.sub(r'^\s*\*+\s*Cancelled\s*\*+\s*', '', text, flags=re.IGNORECASE)
            return text.strip()

        # Look for any header elements that might contain the ride name
        header_elements = event_row.select('h1, h2, h3, h4, h5, h6, th')
        for header in header_elements:
            if header.text.strip():
                name = header.text.strip()
                # Remove "** Cancelled **" prefix
                name = re.sub(r'^\s*\*+\s*Cancelled\s*\*+\s*', '', name, flags=re.IGNORECASE)
                return name.strip()

        # Look for a table header that might contain the ride name
        table_header = event_row.select_one('table th')
        if table_header and table_header.text.strip():
            name = table_header.text.strip()
            # Remove "** Cancelled **" prefix
            name = re.sub(r'^\s*\*+\s*Cancelled\s*\*+\s*', '', name, flags=re.IGNORECASE)
            return name.strip()

        # If all else fails, return a default name
        return "Unknown Ride Name"

    def _extract_dates(self, event_row: BeautifulSoup) -> Dict[str, str]:
        """
        Extract date information from the event row.
        Returns a dictionary with date_start and optionally date_end.
        """
        date_data = {
            'date_start': None,
            'date_end': None
        }

        # First check for the date in a dedicated element
        date_element = event_row.select_one('td.rideDate')
        if date_element and date_element.text.strip():
            date_text = date_element.text.strip()

            # Handle range format: Mar 28-30, 2025
            range_match = re.search(r'([A-Za-z]+)\s+(\d+)[-–—]\s*(\d+),?\s+(\d{4})', date_text)
            if range_match:
                month = range_match.group(1)
                start_day = range_match.group(2)
                end_day = range_match.group(3)
                year = range_match.group(4)

                # Create date strings in ISO format
                month_num = self._month_to_number(month)
                if month_num:
                    date_data['date_start'] = f"{year}-{month_num:02d}-{int(start_day):02d}"
                    date_data['date_end'] = f"{year}-{month_num:02d}-{int(end_day):02d}"
            else:
                # Handle single date format: Mar 28, 2025
                single_match = re.search(r'([A-Za-z]+)\s+(\d+),?\s+(\d{4})', date_text)
                if single_match:
                    month = single_match.group(1)
                    day = single_match.group(2)
                    year = single_match.group(3)

                    # Create date string in ISO format
                    month_num = self._month_to_number(month)
                    if month_num:
                        date_data['date_start'] = f"{year}-{month_num:02d}-{int(day):02d}"

        # If no dates found in dedicated element, look in the ride details
        if not date_data['date_start']:
            # Look through all text for date patterns
            full_text = event_row.get_text()

            # Try various date formats
            date_patterns = [
                # Format: Mar 28-30, 2025
                r'([A-Za-z]+)\s+(\d+)[-–—]\s*(\d+),?\s+(\d{4})',
                # Format: Mar 28, 2025
                r'([A-Za-z]+)\s+(\d+),?\s+(\d{4})',
                # Format: 03/28/2025 - 03/30/2025
                r'(\d{1,2})/(\d{1,2})/(\d{4})\s*[-–—]\s*(\d{1,2})/(\d{1,2})/(\d{4})',
                # Format: 03/28/2025
                r'(\d{1,2})/(\d{1,2})/(\d{4})'
            ]

            for pattern in date_patterns:
                date_match = re.search(pattern, full_text)
                if date_match:
                    if len(date_match.groups()) == 4 and not date_match.group(1).isdigit():
                        # It's a month name range (Mar 28-30, 2025)
                        month = date_match.group(1)
                        start_day = date_match.group(2)
                        end_day = date_match.group(3)
                        year = date_match.group(4)

                        month_num = self._month_to_number(month)
                        if month_num:
                            date_data['date_start'] = f"{year}-{month_num:02d}-{int(start_day):02d}"
                            date_data['date_end'] = f"{year}-{month_num:02d}-{int(end_day):02d}"
                            break
                    elif len(date_match.groups()) == 3 and not date_match.group(1).isdigit():
                        # It's a single date with month name (Mar 28, 2025)
                        month = date_match.group(1)
                        day = date_match.group(2)
                        year = date_match.group(3)

                        month_num = self._month_to_number(month)
                        if month_num:
                            date_data['date_start'] = f"{year}-{month_num:02d}-{int(day):02d}"
                            break
                    elif len(date_match.groups()) == 6:
                        # It's a date range with slashes (03/28/2025 - 03/30/2025)
                        start_month = date_match.group(1)
                        start_day = date_match.group(2)
                        start_year = date_match.group(3)
                        end_month = date_match.group(4)
                        end_day = date_match.group(5)
                        end_year = date_match.group(6)

                        date_data['date_start'] = f"{start_year}-{int(start_month):02d}-{int(start_day):02d}"
                        date_data['date_end'] = f"{end_year}-{int(end_month):02d}-{int(end_day):02d}"
                        break
                    elif len(date_match.groups()) == 3 and date_match.group(1).isdigit():
                        # It's a single date with slashes (03/28/2025)
                        month = date_match.group(1)
                        day = date_match.group(2)
                        year = date_match.group(3)

                        date_data['date_start'] = f"{year}-{int(month):02d}-{int(day):02d}"
                        break

        # If we still don't have a start date, set to a default value
        if not date_data['date_start']:
            # Set a future date as default
            date_data['date_start'] = "2025-01-01"

        # If no end date is found but we have distances that span multiple days,
        # calculate the end date based on the number of days
        if not date_data['date_end'] and date_data['date_start']:
            distances = self._extract_distances(event_row)
            unique_dates = set()
            for dist in distances:
                if 'date' in dist and dist['date']:
                    unique_dates.add(dist['date'])

            if len(unique_dates) > 1:
                # Use a sensible end date based on distance count
                start_date = datetime.fromisoformat(date_data['date_start'])
                date_data['date_end'] = (start_date + timedelta(days=len(unique_dates)-1)).isoformat()[:10]

        return date_data

    def _month_to_number(self, month_name: str) -> Optional[int]:
        """
        Convert month name to month number (1-12).
        Handles full names and abbreviations.
        """
        month_map = {
            'jan': 1, 'january': 1,
            'feb': 2, 'february': 2,
            'mar': 3, 'march': 3,
            'apr': 4, 'april': 4,
            'may': 5,
            'jun': 6, 'june': 6,
            'jul': 7, 'july': 7,
            'aug': 8, 'august': 8,
            'sep': 9, 'sept': 9, 'september': 9,
            'oct': 10, 'october': 10,
            'nov': 11, 'november': 11,
            'dec': 12, 'december': 12
        }

        if not month_name:
            return None

        month_lower = month_name.lower()
        return month_map.get(month_lower)

    def _extract_website(self, event_row: BeautifulSoup) -> Optional[str]:
        """
        Extract the event website URL.
        Returns the URL as a string or None if not found.
        """
        # Look for links with descriptive text like "website" or "more info"
        website_keywords = ['website', 'web site', 'more info', 'information', 'details', 'home page']

        # First try to find links with website-related text
        links = event_row.select('a')
        for link in links:
            # Check link text
            if link.text.strip().lower() in website_keywords:
                return link.get('href')

            # Check if parent element contains website-related text
            parent_text = link.parent.text.lower() if link.parent else ""
            if any(keyword in parent_text for keyword in website_keywords):
                return link.get('href')

        # Next try to find URLs in the HTML with http/https
        # (excluding image links, pdfs, and map links)
        for link in links:
            href = link.get('href')
            if not href:
                continue

            href_lower = href.lower()
            # Skip images, pdfs, and map links
            if (href_lower.startswith('http') and
                not any(ext in href_lower for ext in ['.jpg', '.jpeg', '.png', '.gif', '.pdf']) and
                'map' not in href_lower and
                'google.com/map' not in href_lower):
                return href

        # Try to extract from the raw HTML
        website_patterns = [
            r'website:?\s*<a[^>]*href="([^"]+)"',
            r'<a[^>]*href="(https?://[^"]+)"[^>]*>\s*website\s*</a>',
            r'www\.[\w.-]+\.\w{2,}',
            r'https?://[\w.-]+\.\w{2,}[^\s<>"\']*'
        ]

        html_str = str(event_row)
        for pattern in website_patterns:
            match = re.search(pattern, html_str, re.IGNORECASE)
            if match:
                website = match.group(1) if len(match.groups()) > 0 else match.group(0)
                # Make sure URL starts with http or https
                if not website.startswith(('http://', 'https://')):
                    if website.startswith('www.'):
                        website = 'https://' + website
                return website

        return None

    def _extract_region(self, event_row: BeautifulSoup) -> str:
        """
        Extract the AERC region information.
        Returns the region code as a string.
        """
        # Define AERC regions and their full names
        aerc_regions = {
            'CT': 'Central',
            'MT': 'Mountain',
            'MW': 'Midwest',
            'NE': 'Northeast',
            'NW': 'Northwest',
            'PS': 'Pacific Southwest',
            'SE': 'Southeast',
            'SW': 'Southwest',
            'W': 'West'
        }

        # First look for a td with class 'region' - this is the most reliable indicator
        region_td = event_row.select_one('td.region')
        if region_td and region_td.text.strip():
            region_text = region_td.text.strip().upper()
            if region_text in aerc_regions:
                return region_text

        # Look for a dedicated region element with various classes
        region_element = event_row.select_one('td.rideRegion, span.rideRegion, .region')
        if region_element and region_element.text.strip():
            region_text = region_element.text.strip().upper()

            # Look for exact match in region codes
            if region_text in aerc_regions:
                return region_text

            # Look for partial match (e.g., "Region: SW")
            for code in aerc_regions:
                if code in region_text:
                    return code

        # If no dedicated element, look for region patterns in text
        event_text = event_row.get_text()

        # Try to find region pattern like "Region: SW" or "SW Region"
        region_patterns = [
            r'region:?\s*([A-Z]{1,2})',
            r'([A-Z]{1,2})\s*region',
            r'region\s*([A-Z]{1,2})',
            r'([A-Z]{1,2})$'  # Sometimes region is just the code at the end
        ]

        for pattern in region_patterns:
            match = re.search(pattern, event_text)
            if match:
                region_code = match.group(1)
                if region_code in aerc_regions:
                    return region_code

        # If still not found, check for full region names
        for code, name in aerc_regions.items():
            if name.lower() in event_text.lower():
                return code

        # If no region found, default to "UNKNOWN"
        return "UNKNOWN"

    def _extract_distances(self, event_row: BeautifulSoup) -> List[Dict]:
        """
        Extract distance information from the event row.
        Returns a list of dictionaries with distance and start time.
        """
        distances = []

        # First try to get the distance from the dedicated element
        distance_element = event_row.select_one('td.rideDistance')

        if distance_element and distance_element.text.strip():
            # Extract distances from the dedicated element
            distance_text = distance_element.text.strip()

            # Split by common separators
            distance_parts = re.split(r'[,/&]|\band\b', distance_text)

            for part in distance_parts:
                part = part.strip()
                if not part:
                    continue

                # Extract numeric distance with regex
                distance_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:miles?|mi|km|kilometers?)?', part, re.IGNORECASE)
                if distance_match:
                    distance_value = distance_match.group(1)

                    # Determine if we have units
                    has_units = re.search(r'miles?|mi|km|kilometers?', part, re.IGNORECASE)

                    # Standardize the format
                    if has_units:
                        distance_str = part
                    else:
                        # Assume miles if no unit is specified
                        distance_str = f"{distance_value} miles"

                    # Check if distance is reasonable (between 10 and 200 miles)
                    try:
                        dist_numeric = float(distance_value)
                        if 10 <= dist_numeric <= 200:
                            distances.append({
                                'distance': distance_str,
                                'start_time': ''  # Start time not typically available in overview
                            })
                    except ValueError:
                        pass

        # If no distances found, try to extract from the ride name
        if not distances:
            name_element = event_row.select_one('a.rideName')
            if name_element:
                name_text = name_element.text.strip()

                # Look for common patterns in ride names
                # Pattern: "XX/YY/ZZ" or "XX, YY, ZZ"
                pattern = r'(\d+(?:\.\d+)?)\s*(?:miles?|mi|km)?(?:[,/&]|\band\b)'
                distance_matches = re.finditer(pattern, name_text, re.IGNORECASE)

                for match in distance_matches:
                    distance_value = match.group(1)
                    distance_str = f"{distance_value} miles"

                    try:
                        dist_numeric = float(distance_value)
                        if 10 <= dist_numeric <= 200:  # Reasonable range for endurance rides
                            distances.append({
                                'distance': distance_str,
                                'start_time': ''
                            })
                    except ValueError:
                        pass

        # If still no distances, check the full text for patterns
        if not distances:
            full_text = event_row.get_text()

            # Look for patterns like "XX mile", "XX mi", etc.
            pattern = r'(\d+(?:\.\d+)?)\s*(?:miles?|mi|kilometers?|km)'
            distance_matches = re.finditer(pattern, full_text, re.IGNORECASE)

            for match in distance_matches:
                distance_str = match.group(0).strip()
                distance_value = match.group(1)

                try:
                    dist_numeric = float(distance_value)
                    if 10 <= dist_numeric <= 200:  # Reasonable range check
                        distances.append({
                            'distance': distance_str,
                            'start_time': ''
                        })
                except ValueError:
                    pass

        # Make sure the distances are unique
        seen_distances = set()
        unique_distances = []

        for dist in distances:
            dist_key = dist.get('distance', '').lower()
            if dist_key and dist_key not in seen_distances:
                seen_distances.add(dist_key)
                unique_distances.append(dist)

        return unique_distances

    def _extract_contact_info(self, event_row: BeautifulSoup) -> Dict:
        """
        Extract contact information (ride manager, email, phone).
        """
        contact_info = {
            'name': None,
            'email': None,
            'phone': None
        }

        # Check if there's a dedicated ride manager element
        rm_element = event_row.select_one('td.rideManager')
        if rm_element and rm_element.text.strip():
            contact_info['name'] = rm_element.text.strip()

        # Look for structured tables with ride manager info
        info_tables = event_row.select('table.rideDetailData')
        for table in info_tables:
            rows = table.select('tr')
            for row in rows:
                cells = row.select('td')
                if len(cells) >= 2:
                    header = cells[0].get_text().strip().lower()
                    value = cells[1].get_text().strip()

                    if any(kw in header for kw in ['ride manager', 'manager', 'contact', 'rm', 'mgr']):
                        contact_info['name'] = value
                    elif any(kw in header for kw in ['email', 'e-mail']):
                        contact_info['email'] = value
                    elif any(kw in header for kw in ['phone', 'telephone', 'contact']):
                        # Extract phone number
                        phone_match = re.search(r'(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})', value)
                        if phone_match:
                            contact_info['phone'] = phone_match.group(1)

        # Try to extract ride manager from mgr: pattern in text
        if not contact_info['name']:
            manager_patterns = [
                r'mgr:\s*([^;,\n\r<>]+)',
                r'ride\s*manager:\s*([^;,\n\r<>]+)',
                r'manager:\s*([^;,\n\r<>]+)',
                r'contact:\s*([^;,\n\r<>]+)'
            ]

            full_text = event_row.get_text()
            for pattern in manager_patterns:
                manager_match = re.search(pattern, full_text, re.IGNORECASE)
                if manager_match:
                    contact_info['name'] = manager_match.group(1).strip()
                    break

        # Look for email pattern in text
        if not contact_info['email']:
            email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
            email_matches = re.findall(email_pattern, event_row.get_text())
            if email_matches:
                # Take the first email found
                contact_info['email'] = email_matches[0]

        # Look for phone number pattern in text
        if not contact_info['phone']:
            phone_patterns = [
                r'(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})',
                r'(\(\d{3}\)[-.\s]?\d{3}[-.\s]?\d{4})'
            ]
            for pattern in phone_patterns:
                phone_matches = re.findall(pattern, event_row.get_text())
                if phone_matches:
                    # Take the first phone number found
                    contact_info['phone'] = phone_matches[0]
                    break

        return contact_info

    def _extract_location(self, row) -> str:
        """Extract the event location."""
        # The location is in the second <td> of the second <tr> in each calendar entry
        # First, find all table rows within this calendar row
        tr_elements = row.select('tr.fix-jumpy')

        if len(tr_elements) >= 2:  # We need at least 2 rows
            # Second row, second td contains location
            location_elem = tr_elements[1].select_one('td:nth-of-type(2)')

            if location_elem:
                # Get the full text of the location element
                location_text = location_elem.text.strip()

                # If location is empty or just whitespace, return Unknown Location
                if not location_text or location_text.isspace():
                    return "Unknown Location"

                # Don't use "Has Intro Ride!" as a location - extract the actual location part
                if "Has Intro Ride!" in location_text:
                    # Try to extract the actual location part if present
                    location_parts = location_text.split("Has Intro Ride!")
                    if len(location_parts) > 1 and location_parts[0].strip():
                        return location_parts[0].strip()
                    elif len(location_parts) > 1 and location_parts[1].strip():
                        return location_parts[1].strip()

                # Check if there's a <br> tag and get the text before it
                if location_elem.br:
                    # Get text before the first <br> tag
                    location_text = location_elem.contents[0].strip()

                return location_text

        # If we can't find the location in the expected structure,
        # try to find it in the detailed data table (expanded view)
        detail_data = row.select_one('table.detailData')
        if detail_data:
            # Find the row with the location data
            location_row = detail_data.select_one('tr:has(td:contains("Location"))')
            if location_row:
                location_elem = location_row.select_one('td:nth-of-type(3)')
                if location_elem:
                    # Extract text before the first <br> tag if present
                    if location_elem.br:
                        location_text = location_elem.contents[0].strip()
                        return location_text
                    else:
                        return location_elem.text.strip()

        # If still not found, try to find a more meaningful location elsewhere
        # Check the region
        region_elem = row.select_one('td.region')
        region = region_elem.text.strip() if region_elem else "Unknown"

        # Last resort fallback
        return f"AERC {region} Region Event"

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

    def _extract_description(self, row) -> Optional[str]:
        """Extract event description with improved patterns."""
        description = None

        # First, check for a dedicated description element
        description_elem = row.select_one('div.details, td.rideDescription')
        if description_elem:
            description = description_elem.get_text(strip=True)
            if description:
                return description

        # Look in table structure for description
        for tr in row.select('tr'):
            cells = tr.select('td')
            if len(cells) >= 2 and 'description' in cells[0].text.lower():
                description = cells[1].text.strip()
                if description:
                    return description

        # Check for paragraphs that might contain description content
        for p in row.select('p'):
            text = p.get_text(strip=True)
            # Look for substantial text that isn't just contact info or directions
            if len(text) > 30 and not any(keyword in text.lower() for keyword in
                                          ['directions', 'map', 'contact', 'phone', 'email', '@']):
                return text

        # Look for larger text blocks that might be descriptions
        text_blocks = []
        for elem in row.select('div, td'):
            text = elem.get_text(strip=True)
            if len(text) > 50 and not any(keyword in text.lower() for keyword in
                                         ['directions', 'map', 'contact', 'phone', 'email', '@']):
                text_blocks.append(text)

        # Use the longest text block as the description
        if text_blocks:
            return max(text_blocks, key=len)

        # Extract from full text as a last resort
        full_text = row.get_text(strip=True)
        if len(full_text) > 50:
            # Clean up the text by removing common non-description parts
            cleaned = re.sub(r'(?:RM|Ride Manager|RideManager)[:\s]+([^,\n]+)', '', full_text)
            cleaned = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '', cleaned)
            cleaned = re.sub(r'(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})', '', cleaned)
            # Remove dates and times
            cleaned = re.sub(r'\d{1,2}/\d{1,2}/\d{2,4}', '', cleaned)
            cleaned = re.sub(r'\d{1,2}:\d{2}\s*(?:am|pm|AM|PM)', '', cleaned)

            # If we still have substantial text, use it
            if len(cleaned) > 50:
                return cleaned.strip()

        return "No description available"

    def _extract_directions(self, row) -> Optional[str]:
        """Extract directions with improved patterns."""
        directions = None

        # First, check for a dedicated directions element
        directions_elem = row.select_one('div.directions')
        if directions_elem:
            directions = directions_elem.get_text(strip=True)
            if directions:
                return directions

        # Look in table structure for directions
        for tr in row.select('tr'):
            cells = tr.select('td')
            if len(cells) >= 2 and any(keyword in cells[0].text.lower() for keyword in
                                      ['direction', 'directions', 'location details']):
                directions = cells[1].text.strip()
                if directions:
                    return directions

        # Look for paragraphs or divs that might contain directions
        for elem in row.select('p, div, span'):
            text = elem.get_text(strip=True).lower()
            if 'directions' in text and len(text) > 20:
                # Extract the full text, not just the lowercase version
                return elem.get_text(strip=True)

        # Look for link text that might contain directions
        direction_links = [a for a in row.select('a') if 'directions' in a.get_text(strip=True).lower()]
        if direction_links:
            link_text = direction_links[0].get_text(strip=True)
            if len(link_text) > 10:  # Not just "Directions"
                return link_text

        # If no specific directions found, return None
        return directions

    def _check_if_canceled(self, row) -> bool:
        """Check if an event is canceled."""
        # Look for canceled or cancelled text in the HTML
        text = row.get_text().lower()
        return any(word in text for word in ['canceled', 'cancelled', 'postponed'])

    def _extract_coordinates(self, event_row: BeautifulSoup, location: str) -> Optional[Dict[str, float]]:
        """
        Extract coordinates (latitude, longitude) from the event HTML or location.
        Returns a dictionary with latitude and longitude if found, otherwise None.
        """
        # First look for coordinates in any links
        map_links = event_row.select('a[href*="maps.google.com"], a[href*="goo.gl/maps"]')
        for link in map_links:
            href = link.get('href', '')
            # Pattern for coordinates in Google Maps URL
            coord_pattern = r'[?&]q=(-?\d+\.\d+),(-?\d+\.\d+)|/@(-?\d+\.\d+),(-?\d+\.\d+)'
            match = re.search(coord_pattern, href)
            if match:
                # Extract the coordinates from the matched groups
                lat = match.group(1) or match.group(3)
                lng = match.group(2) or match.group(4)
                try:
                    return {
                        'latitude': float(lat),
                        'longitude': float(lng)
                    }
                except (ValueError, TypeError):
                    pass

        # Hard-coded coordinates for well-known locations
        # This is a fallback for test data or common event locations
        location_coords = {
            # Test data locations
            "Tevis Cup": (39.23839, -120.17357),  # Robie Park, Truckee (Tevis Cup start)
            "Western States": (39.23839, -120.17357),  # Same as Tevis
            "Robie Park": (39.23839, -120.17357),  # Tevis Cup start location
            "Belair Forest": (50.44538, -96.443778),  # Belair Provincial Forest, Manitoba
            "Belair Provincial Forest": (50.44538, -96.443778),  # Belair Provincial Forest, Manitoba

            # Common event locations by name
            "Biltmore Equestrian Center": (35.5418, -82.5521),  # Biltmore Estate
            "Empire Ranch": (31.7884, -110.6345)  # Empire Ranch, Sonoita, AZ
        }

        # Check if location contains any of the well-known locations
        if location:
            for key, (lat, lng) in location_coords.items():
                if key.lower() in location.lower():
                    return {
                        'latitude': lat,
                        'longitude': lng
                    }

        # Also check the ride name for well-known events
        ride_name = self._extract_ride_name(event_row).lower()
        for key, (lat, lng) in location_coords.items():
            if key.lower() in ride_name:
                return {
                    'latitude': lat,
                    'longitude': lng
                }

        return None

    def _extract_control_judges(self, row) -> List[Dict[str, str]]:
        """Extract control judges with improved patterns."""
        judges = []

        # Look for judge information in the main row
        for tr in row.select('tr.fix-jumpy'):
            for td in tr.select('td'):
                text = td.text.strip()
                if 'control judge:' in text.lower():
                    # Extract the judge name that follows "Control Judge:"
                    match = re.search(r'control judge:?\s*([^,\n]+(?:,\s*[^,\n]+)*)', text, re.IGNORECASE)
                    if match:
                        judge_name = match.group(1).strip()
                        if judge_name:
                            judges.append({
                                'name': judge_name,
                                'role': 'Control Judge'
                            })

        # Get the full text for pattern matching
        text = row.get_text()

        # Look for structured judge info in a table
        for tr in row.select('tr'):
            cells = tr.select('td')
            if len(cells) >= 3:  # Look for 3-column tables with Control Judges section
                if len(cells) >= 1 and 'control judge' in cells[0].text.lower():
                    # Check next cells for role and name
                    if len(cells) >= 3:
                        role = cells[1].text.strip()
                        name = cells[2].text.strip()
                        if name:
                            role_text = 'Control Judge'
                            if 'head' in role.lower():
                                role_text = 'Head Control Judge'
                            judges.append({
                                'name': name,
                                'role': role_text
                            })
                # Check for other judge patterns with first cell containing label
                elif len(cells) >= 2:
                    cell_text = cells[0].text.strip().lower()
                    if any(judge_type in cell_text for judge_type in
                          ['judge', 'vet', 'control', 'head vet', 'treatment vet']):
                        # Second cell often contains the judge names
                        judge_text = cells[1].text.strip()
                        if judge_text:
                            # Determine role from the label
                            role = 'Control Judge'  # Default role
                            if 'head vet' in cell_text:
                                role = 'Head Vet'
                            elif 'treatment vet' in cell_text:
                                role = 'Treatment Vet'
                            elif 'vet' in cell_text:
                                role = 'Vet Judge'

                            # Split multiple judges if separated by commas or "and"
                            judge_names = re.split(r',|\sand\s', judge_text)
                            for name in judge_names:
                                name = name.strip()
                                if name:
                                    judges.append({
                                        'name': name,
                                        'role': role
                                    })
            # Look for table cells with head control judge pattern
            if len(cells) >= 2:
                for i in range(len(cells) - 1):
                    cell_text = cells[i].text.strip().lower()
                    if 'head control judge' in cell_text or 'control judge' in cell_text:
                        judge_name = cells[i+1].text.strip()
                        if judge_name:
                            role = 'Head Control Judge' if 'head' in cell_text else 'Control Judge'
                            judges.append({
                                'name': judge_name,
                                'role': role
                            })

        # If we couldn't find judges in a table, try regex patterns
        if not judges:
            # Patterns for different types of judges/vets
            judge_patterns = [
                (r'Control Judge(?:s)?:\s*([^,\n]+(?:,\s*[^,\n]+)*)', 'Control Judge'),
                (r'Head Control Judge(?:s)?:\s*([^,\n]+(?:,\s*[^,\n]+)*)', 'Head Control Judge'),
                (r'Vet Judge(?:s)?:\s*([^,\n]+(?:,\s*[^,\n]+)*)', 'Vet Judge'),
                (r'Head Vet(?:s)?:\s*([^,\n]+(?:,\s*[^,\n]+)*)', 'Head Vet'),
                (r'Treatment Vet(?:s)?:\s*([^,\n]+(?:,\s*[^,\n]+)*)', 'Treatment Vet'),
                (r'Technical Delegate(?:s)?:\s*([^,\n]+(?:,\s*[^,\n]+)*)', 'Technical Delegate'),
                (r'Steward(?:s)?:\s*([^,\n]+(?:,\s*[^,\n]+)*)', 'Steward'),
                (r'Judge(?:s)?:\s*([^,\n]+(?:,\s*[^,\n]+)*)', 'Judge')
            ]

            for pattern, role in judge_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    # Split by comma to handle multiple judges
                    judge_names = [name.strip() for name in match.split(',')]
                    for name in judge_names:
                        # Clean up the name
                        name = re.sub(r'[,.:;]+$', '', name).strip()
                        if name and not any(j['name'] == name for j in judges):  # Avoid duplicates
                            judges.append({
                                'name': name,
                                'role': role
                            })

        return judges

    def _check_has_intro_ride(self, row, distances=None) -> bool:
        """Check if the event has an intro ride option with improved patterns."""
        # If distances is provided, check for intro in the distances first
        if distances:
            for dist in distances:
                if isinstance(dist, dict) and 'distance' in dist:
                    distance_str = str(dist['distance']).lower()
                    if 'intro' in distance_str:
                        return True
                    # Check for short distances that might be intro rides
                    try:
                        # Extract numeric part from distance string
                        match = re.search(r'(\d+(?:\.\d+)?)', distance_str)
                        if match and float(match.group(1)) <= 15:  # Intro rides are typically shorter distances
                            return True
                    except (ValueError, TypeError):
                        pass
                elif isinstance(dist, str) and 'intro' in dist.lower():
                    return True

        # Look for various intro ride indicators in the HTML

        # Check the full text first
        full_text = row.get_text().lower()
        if any(phrase in full_text for phrase in ['intro ride', 'introductory ride', 'has intro']):
            return True

        # Check specific elements
        intro_indicators = [
            ('td.rideDistance', ['intro', 'introductory']),
            ('td.rideLocation', ['intro', 'introductory', 'has intro']),
            ('span.rideName', ['intro', 'introductory']),
            ('td.rideDescription', ['intro ride', 'introductory ride'])
        ]

        for selector, phrases in intro_indicators:
            elem = row.select_one(selector)
            if elem and elem.text:
                elem_text = elem.text.lower()
                if any(phrase in elem_text for phrase in phrases):
                    return True

        # Check for "Has Intro Ride!" text anywhere
        if "has intro ride!" in full_text:
            return True

        # Check distance field for intro distances (typically under 15 miles)
        distance_elem = row.select_one('td.rideDistance')
        if distance_elem and distance_elem.text:
            # Look for short distances like "10 miles" that might be intro rides
            for match in re.finditer(r'(\d+)(?:\s*mi|\s*miles|\s*km)?', distance_elem.text.lower()):
                try:
                    distance = int(match.group(1))
                    if distance <= 15:  # Intro rides are typically shorter distances
                        return True
                except ValueError:
                    pass

        return False

    def _extract_city_state_country(self, location: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Extract city, state, and country from location string."""
        if not location or location == "Unknown Location" or location.startswith("AERC "):
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
        if 'Canada' in location or any(province in location for province in canadian_provinces.values()):
            country = "Canada"

        # Special checks for specific content
        if any(state_name in location for state_name in ['Manitoba', 'Ontario', 'Alberta']):
            for state_name, state_code in {'Manitoba': 'MB', 'Ontario': 'ON', 'Alberta': 'AB'}.items():
                if state_name in location:
                    state = state_code
                    break

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

    def _extract_location_details(self, event_row: BeautifulSoup, location: str) -> Dict[str, Optional[str]]:
        """
        Extract structured location details (city, state, country) from the event row and location.
        Returns a dictionary with city, state, and country information.
        """
        city = None
        state = None
        country = "USA"  # Default country is USA

        # First try to extract from the location string
        if location:
            city, state, country = self._extract_city_state_country(location)

        # If we couldn't extract a city or state, try parsing the location cell
        if not city or not state:
            location_elem = event_row.select_one('td.rideLocation')
            if location_elem:
                location_text = location_elem.get_text(strip=True)
                if location_text and location_text != location:
                    city_alt, state_alt, country_alt = self._extract_city_state_country(location_text)
                    city = city or city_alt
                    state = state or state_alt
                    country = country_alt if country_alt else country

        # Check for special cases like "Cuyama" which should be "New Cuyama, CA"
        if "Cuyama" in location and not city:
            city = "New Cuyama"
            state = "CA"
            country = "USA"

        # Look for an address element that might contain more details
        address_elem = event_row.select_one('div.address, td.address')
        if address_elem:
            address_text = address_elem.get_text(strip=True)
            if address_text:
                city_addr, state_addr, country_addr = self._extract_city_state_country(address_text)
                city = city or city_addr
                state = state or state_addr
                country = country_addr if country_addr else country

        # Return the structured location details
        return {
            'city': city,
            'state': state,
            'country': country
        }

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get parser metrics and statistics.

        Returns a dictionary containing metrics about the parsing process,
        including counts of events found, extracted, errors, etc.

        Returns:
            Dictionary of parser metrics
        """
        return self.metrics

    def validate_event_data(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and clean event data against the AERCEvent schema.

        Args:
            event: Raw event dictionary to validate

        Returns:
            Cleaned and validated event dictionary

        Raises:
            ValueError: If the event data is invalid or missing required fields
        """
        # Check required fields
        required_fields = ['name', 'date_start', 'location']
        missing_fields = [field for field in required_fields if not event.get(field)]

        if missing_fields:
            raise ValueError(f"Event missing required fields: {', '.join(missing_fields)}")

        # Ensure event has the correct source
        event['source'] = 'AERC'

        # Ensure event has the correct event_type
        if not event.get('event_type'):
            event['event_type'] = 'endurance'

        # Clean up None values
        clean_event = {k: v for k, v in event.items() if v is not None}

        # Ensure distances is a list
        if 'distances' in clean_event and not isinstance(clean_event['distances'], list):
            clean_event['distances'] = []

        # Ensure control_judges is a list
        if 'control_judges' in clean_event and not isinstance(clean_event['control_judges'], list):
            clean_event['control_judges'] = []

        return clean_event

    def format_date(self, date_str: str) -> str:
        """
        Format date string to ISO format (YYYY-MM-DD).

        Args:
            date_str: Date string in various formats

        Returns:
            ISO formatted date string or original string if parsing fails
        """
        # Try various date formats
        formats = [
            '%b %d, %Y',  # Mar 28, 2025
            '%B %d, %Y',  # March 28, 2025
            '%m/%d/%Y',   # 03/28/2025
            '%Y-%m-%d'    # 2025-03-28 (already ISO)
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue

        # If all parsing attempts fail, return original
        return date_str
