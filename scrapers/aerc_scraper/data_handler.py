"""Data handler for AERC event data processing and validation."""

from datetime import datetime
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse

from pydantic import HttpUrl

from app.schemas.event import EventCreate
from scrapers.schema import (
    AERCEvent,
    ContactInfo,
    Distance,
    Location,
    EventSourceEnum,
    EventTypeEnum
)

class DataHandler:
    """Handles validation and transformation of AERC event data."""

    @staticmethod
    def _extract_and_format_event_details(raw_event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and format additional event details for storage.
        
        Args:
            raw_event: Raw event data
            
        Returns:
            Dictionary of additional event details
        """
        event_details = {}
        
        # Add coordinates if available
        if 'coordinates' in raw_event:
            event_details['coordinates'] = raw_event['coordinates']
            
        # Add map link if available
        if 'map_link' in raw_event:
            event_details['map_link'] = raw_event['map_link']
            
        # Add flyer URL if available
        if 'flyer_url' in raw_event:
            event_details['flyer_url'] = raw_event['flyer_url']
            
        # Add directions if available
        if 'directions' in raw_event:
            event_details['directions'] = raw_event['directions']
            
        # Add intro ride flag
        event_details['has_intro_ride'] = raw_event.get('has_intro_ride', False)
        
        # Add distances with start times if available
        if 'distances' in raw_event:
            distances_detail = []
            for dist in raw_event['distances']:
                dist_obj = {
                    'distance': dist.get('distance', '').split(' ')[0].strip(),  # Extract just the number
                    'unit': 'miles'
                }
                if 'start_time' in dist:
                    dist_obj['start_time'] = dist['start_time']
                distances_detail.append(dist_obj)
            event_details['distances'] = distances_detail
            
        # Add control judges if available
        if 'control_judges' in raw_event:
            event_details['control_judges'] = raw_event['control_judges']
            
        return event_details

    @classmethod
    def transform_and_validate(cls, raw_event: Dict[str, Any]) -> AERCEvent:
        """Transform raw event data into a validated AERCEvent."""
        # Build the location object
        location = cls._build_location(raw_event)
        
        # Build distances
        distances = cls._build_distances(raw_event)
        
        # Build contacts
        contacts = cls._build_contacts(raw_event)
        
        # Extract additional event details
        event_details = cls._extract_and_format_event_details(raw_event)
        
        # Build AERC event data
        event_data = {
            'name': raw_event['name'],
            'source': EventSourceEnum.AERC,
            'event_type': EventTypeEnum.ENDURANCE,  # Default for AERC events
            'date_start': datetime.strptime(raw_event['date_start'], '%Y-%m-%d'),
            'location': location,
            'region': raw_event.get('region'),
            'description': raw_event.get('description'),  # Add description from parser
            'distances': distances,
            'contacts': contacts,
            'website_url': cls._validate_url(raw_event.get('website')),
            'registration_url': cls._validate_url(raw_event.get('flyer_url')),
            'external_id': None,  # Can be added if needed
            'sanctioning_status': None,  # Can be extracted if available
            'has_drug_testing': False,  # Default value
            'has_intro_ride': raw_event.get('has_intro_ride', False),  # Add intro ride flag
            'is_canceled': raw_event.get('is_canceled', False),  # Add cancellation status
            'event_details': event_details if event_details else None
        }

        return AERCEvent.model_validate(event_data)
        
    @staticmethod
    def to_event_create(aerc_event: AERCEvent) -> EventCreate:
        """
        Convert an AERCEvent to EventCreate format for database storage.
        
        Args:
            aerc_event: Validated AERCEvent object
            
        Returns:
            EventCreate: Event in format ready for storage
        """
        # Extract location as string
        location_str = aerc_event.location.name
        if aerc_event.location.city:
            if location_str and not location_str.endswith(aerc_event.location.city):
                location_str += f", {aerc_event.location.city}"
            else:
                location_str = aerc_event.location.city
                
        if aerc_event.location.state:
            location_str += f", {aerc_event.location.state}"
                
        # Format distances as strings with start time information if available
        distance_strings = []
        event_details = aerc_event.model_dump(exclude_none=True).get('event_details', {}) or {}
        
        # Create a 'distances' field in event_details to store the detailed distance information
        detailed_distances = event_details.get('distances', [])
        
        for distance in aerc_event.distances:
            # Basic distance string (e.g. "25 miles")
            distance_str = f"{distance.distance}"
            if not distance_str.endswith('miles') and not distance_str.endswith('mi'):
                distance_str += f" {distance.unit}"
            
            distance_strings.append(distance_str)
            
            # Add enriched distance information to event_details
            detailed_distance = {
                "distance": distance.distance,
                "unit": distance.unit
            }
            
            if distance.start_time:
                detailed_distance["start_time"] = distance.start_time
                
            if distance.entry_fee:
                detailed_distance["entry_fee"] = distance.entry_fee
                
            if distance.max_riders:
                detailed_distance["max_riders"] = distance.max_riders
                
            detailed_distances.append(detailed_distance)
            
        # Update event_details with detailed distances
        if detailed_distances:
            event_details['distances'] = detailed_distances
            
        # Add coordinates to event_details if available
        if aerc_event.location.coordinates:
            event_details['coordinates'] = {
                'latitude': aerc_event.location.coordinates.get('latitude'),
                'longitude': aerc_event.location.coordinates.get('longitude')
            }
            
        # Add control judges to event_details
        control_judges = []
        other_contacts = []
        
        # Extract contact info
        ride_manager = None
        manager_email = None
        manager_phone = None
        
        if aerc_event.contacts:
            for contact in aerc_event.contacts:
                if contact.role == "Ride Manager":
                    ride_manager = contact.name
                    manager_email = contact.email
                    manager_phone = contact.phone
                elif contact.role == "Control Judge":
                    control_judges.append({
                        'name': contact.name,
                        'role': contact.role
                    })
                else:
                    # Store other contacts like Vet Judge, Technical Delegate, etc.
                    other_contacts.append({
                        'name': contact.name,
                        'role': contact.role
                    })
        
        # Add control judges to event_details
        if control_judges:
            event_details['control_judges'] = control_judges
            
        # Add other contacts to event_details
        if other_contacts:
            event_details['other_contacts'] = other_contacts
            
        # If there's a map link, add it to event_details
        if hasattr(aerc_event, 'event_details') and aerc_event.event_details:
            if 'map_link' in aerc_event.event_details:
                event_details['map_link'] = aerc_event.event_details['map_link']
                
            # Add directions if available
            if 'directions' in aerc_event.event_details:
                event_details['directions'] = aerc_event.event_details['directions']
                
            # Add intro ride flag if available
            if 'has_intro_ride' in aerc_event.event_details:
                event_details['has_intro_ride'] = aerc_event.event_details['has_intro_ride']
        
        # Convert to EventCreate
        return EventCreate(
            name=aerc_event.name,
            source=str(aerc_event.source.value),  # Convert enum to string
            event_type=str(aerc_event.event_type.value),  # Convert enum to string 
            date_start=aerc_event.date_start,
            date_end=aerc_event.date_end,
            location=location_str,
            region=aerc_event.region,
            description=aerc_event.description,
            website=str(aerc_event.website_url) if aerc_event.website_url else None,
            flyer_url=str(aerc_event.registration_url) if aerc_event.registration_url else None,
            distances=distance_strings,
            ride_manager=ride_manager,
            manager_email=manager_email,
            manager_phone=manager_phone,
            external_id=aerc_event.external_id,
            is_canceled=aerc_event.is_canceled,  # Use the is_canceled field
            event_details=event_details if event_details else None
        )

    @staticmethod
    def _parse_location(location_str: str) -> Dict[str, str]:
        """
        Parse location string into components.
        
        Example inputs:
        - "Ride Name - City, ST"
        - "City, State"
        - "Location Name"
        """
        parts = {'name': None, 'city': None, 'state': None}
        
        if not location_str:
            return parts

        # Try to split on dash first for locations with ride name
        name_parts = location_str.split('-', 1)
        if len(name_parts) > 1:
            parts['name'] = name_parts[0].strip()
            location_str = name_parts[1].strip()
        
        # Try to extract city and state
        location_parts = location_str.split(',')
        if len(location_parts) > 1:
            parts['city'] = location_parts[0].strip()
            parts['state'] = location_parts[1].strip()
            # We don't set the name here to match test expectations
            # The name will be set in transform_and_validate if needed
        else:
            # If no comma, treat the whole string as the name
            parts['name'] = location_str.strip()
            
        return parts

    @staticmethod
    def _validate_url(url: Optional[str]) -> Optional[HttpUrl]:
        """Validate and normalize URL."""
        if not url:
            return None
            
        try:
            # Basic validation - URL should have a domain with at least one dot
            if '.' not in url:
                return None
                
            # Ensure URL has scheme
            parsed = urlparse(url)
            if not parsed.scheme:
                url = f"https://{url}"
                
            # Let Pydantic validate the URL
            return HttpUrl(url)
        except Exception:
            return None 

    @classmethod
    def _build_location(cls, raw_event: Dict[str, Any]) -> Location:
        """Build the location object from raw event data."""
        # Transform location data
        location_parts = cls._parse_location(raw_event.get('location', ''))
        location_name = location_parts.get('name')
        
        # If no name was extracted but we have city/state, use the full location as name
        if not location_name and (location_parts.get('city') or location_parts.get('state')):
            location_name = raw_event.get('location', 'Unknown Location')
        
        # Use extracted city/state if available, otherwise use from location_parts
        city = raw_event.get('city') or location_parts.get('city')
        state = raw_event.get('state') or location_parts.get('state')
        
        # Add coordinates if available
        coordinates = None
        if raw_event.get('coordinates'):
            coordinates = {
                'latitude': raw_event['coordinates'].get('latitude'),
                'longitude': raw_event['coordinates'].get('longitude')
            }
            
        return Location(
            name=location_name or raw_event.get('location', 'Unknown Location'),
            city=city,
            state=state,
            country="USA",  # Default for AERC events
            coordinates=coordinates
        )
    
    @classmethod
    def _build_distances(cls, raw_event: Dict[str, Any]) -> List[Distance]:
        """Build the distances list from raw event data."""
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
        
        return distances
    
    @classmethod
    def _build_contacts(cls, raw_event: Dict[str, Any]) -> List[ContactInfo]:
        """Build the contacts list from raw event data."""
        contacts = []
        
        # Add ride manager as a contact
        if raw_event.get('ride_manager'):
            contact = ContactInfo(
                name=raw_event['ride_manager'],
                email=raw_event.get('ride_manager_contact', {}).get('email'),
                phone=raw_event.get('ride_manager_contact', {}).get('phone'),
                role="Ride Manager"
            )
            contacts.append(contact)
        
        # Add control judges as contacts
        for judge in raw_event.get('control_judges', []):
            contact = ContactInfo(
                name=judge.get('name', ''),
                role=judge.get('role', 'Control Judge')
            )
            contacts.append(contact)
            
        return contacts 