"""Data handler for AERC event data processing and validation."""

from datetime import datetime
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse

from pydantic import HttpUrl

# Import from the centralized schema instead of scrapers.schema
from app.schemas import (
    EventCreate,
    AERCEvent,
    ContactInfo,
    EventDistance as Distance,
    LocationDetails as Location,
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
        if 'has_intro_ride' in raw_event:
            event_details['has_intro_ride'] = raw_event['has_intro_ride']
            
        # Add ride ID if available
        if 'ride_id' in raw_event:
            event_details['ride_id'] = raw_event['ride_id']
            
        # Add location details if available
        location_details = {}
        if 'city' in raw_event:
            location_details['city'] = raw_event['city']
        if 'state' in raw_event:
            location_details['state'] = raw_event['state']
        if 'country' in raw_event:
            location_details['country'] = raw_event['country']
            
        if location_details:
            event_details['location_details'] = location_details
            
        # Add ride manager contact info
        if 'ride_manager_contact' in raw_event:
            event_details['ride_manager_contact'] = raw_event['ride_manager_contact']
            
        # Add control judges
        if 'control_judges' in raw_event:
            event_details['control_judges'] = raw_event['control_judges']
            
        # Add description
        if 'description' in raw_event:
            event_details['description'] = raw_event['description']
            
        return event_details
        
    @classmethod
    def transform_and_validate(cls, raw_event: Dict[str, Any]) -> AERCEvent:
        """
        Transform raw event data into AERCEvent object and validate it.
        
        Args:
            raw_event: Raw event data from parser
            
        Returns:
            Validated AERCEvent object
            
        Raises:
            ValueError: If validation fails
        """
        # Extract required and common fields
        try:
            # Set fixed values for AERC events
            event_data = {
                'source': EventSourceEnum.AERC,
                'event_type': EventTypeEnum.ENDURANCE,
            }
            
            # Extract basic fields
            if 'name' in raw_event:
                event_data['name'] = raw_event['name']
                
            if 'date_start' in raw_event:
                # Parse date string to datetime
                if isinstance(raw_event['date_start'], str):
                    try:
                        event_data['date_start'] = datetime.strptime(raw_event['date_start'], '%Y-%m-%d')
                    except ValueError:
                        # Try another format
                        event_data['date_start'] = datetime.strptime(raw_event['date_start'], '%Y-%m-%dT%H:%M:%S')
                else:
                    event_data['date_start'] = raw_event['date_start']
                    
            # For date_end, use date_start if not provided
            if 'date_end' in raw_event:
                event_data['date_end'] = raw_event['date_end']
                
            # Region is optional but important
            if 'region' in raw_event:
                event_data['region'] = raw_event['region']
                
            # Extract location
            if 'location' in raw_event:
                event_data['location'] = raw_event['location']
                
                # Build structured location
                location_details = cls._build_location(raw_event)
                if location_details:
                    event_data['location_details'] = location_details
                    
            # Add coordinates as a structured field if available
            if 'coordinates' in raw_event:
                event_data['coordinates'] = raw_event['coordinates']
                
            # Extract ride manager
            if 'ride_manager' in raw_event:
                event_data['ride_manager'] = raw_event['ride_manager']
                
            # Extract ride manager contact info
            if 'ride_manager_contact' in raw_event:
                contact_info = raw_event['ride_manager_contact']
                if 'email' in contact_info:
                    event_data['manager_email'] = contact_info['email']
                if 'phone' in contact_info:
                    event_data['manager_phone'] = contact_info['phone']
                    
            # Process website
            if 'website' in raw_event:
                website = cls._validate_url(raw_event['website'])
                if website:
                    event_data['website'] = str(website)
                    
            # Process flyer URL
            if 'flyer_url' in raw_event:
                flyer_url = cls._validate_url(raw_event['flyer_url'])
                if flyer_url:
                    event_data['flyer_url'] = str(flyer_url)
                    
            # Process map link
            if 'map_link' in raw_event:
                map_link = cls._validate_url(raw_event['map_link'])
                if map_link:
                    event_data['map_link'] = str(map_link)
                    
            # Process distances
            if 'distances' in raw_event:
                event_data['distances'] = cls._build_distances(raw_event)
                
            # Process control judges
            if 'control_judges' in raw_event:
                event_data['control_judges'] = raw_event['control_judges']
                
            # Process flags
            if 'is_canceled' in raw_event:
                event_data['is_canceled'] = raw_event['is_canceled']
                
            if 'has_intro_ride' in raw_event:
                event_data['has_intro_ride'] = raw_event['has_intro_ride']
                
            # Process ride ID
            if 'ride_id' in raw_event:
                event_data['ride_id'] = raw_event['ride_id']
                
            # Create and validate the AERCEvent object
            event = AERCEvent(**event_data)
            return event
            
        except Exception as e:
            raise ValueError(f"Failed to validate event data: {str(e)}")
    
    @staticmethod
    def to_event_create(aerc_event: AERCEvent) -> EventCreate:
        """
        Convert AERCEvent to EventCreate model for database insertion.
        
        Args:
            aerc_event: Validated AERCEvent object
            
        Returns:
            EventCreate object ready for database insertion
        """
        # Extract all fields from AERCEvent
        event_dict = aerc_event.model_dump()
        
        # Get rid of location_details as a top-level field
        location_details = event_dict.pop('location_details', None)
        
        # Coordinates as a top-level field
        coordinates = event_dict.pop('coordinates', None)
        
        # Control judges as a structure
        control_judges = event_dict.pop('control_judges', None)
        
        # Treatment vets as a structure
        treatment_vets = event_dict.pop('treatment_vets', None)
        
        # Other fields to include in event_details
        sanctioning_status = event_dict.pop('sanctioning_status', None)
        has_drug_testing = event_dict.pop('has_drug_testing', False)
        
        # Prepare distances
        distances = event_dict.get('distances', [])
        simple_distances = []
        
        # Check if distances is already in the right format
        if distances and isinstance(distances[0], str):
            simple_distances = distances
        else:
            # Convert Distance objects to strings
            for distance in distances:
                if isinstance(distance, dict):
                    simple_distances.append(distance.get('distance', ''))
                elif hasattr(distance, 'distance'):
                    simple_distances.append(distance.distance)
                else:
                    simple_distances.append(str(distance))
                    
        event_dict['distances'] = simple_distances
        
        # Build event_details dictionary
        event_details = {}
        
        # Store structured data in event_details
        if location_details:
            event_details['location_details'] = location_details.model_dump() if hasattr(location_details, 'model_dump') else location_details
            
        if coordinates:
            event_details['coordinates'] = coordinates.model_dump() if hasattr(coordinates, 'model_dump') else coordinates
            
        if control_judges:
            event_details['control_judges'] = [
                judge.model_dump() if hasattr(judge, 'model_dump') else judge 
                for judge in control_judges
            ]
            
        if treatment_vets:
            event_details['treatment_vets'] = [
                vet.model_dump() if hasattr(vet, 'model_dump') else vet 
                for vet in treatment_vets
            ]
            
        # Store detailed distance information
        if distances and not isinstance(distances[0], str):
            event_details['distances'] = [
                dist.model_dump() if hasattr(dist, 'model_dump') else dist 
                for dist in distances
            ]
            
        # Store other AERC-specific fields
        if sanctioning_status:
            event_details['sanctioning_status'] = sanctioning_status
            
        if has_drug_testing:
            event_details['has_drug_testing'] = has_drug_testing
            
        # Store original fields in event_details
        if 'ride_id' in event_dict and event_dict['ride_id']:
            # Use the direct field instead of storing in event_details
            pass
        
        if 'has_intro_ride' in event_dict:
            # Use the direct field instead of storing in event_details
            pass
            
        # Add event_details to the event dictionary
        if event_details:
            event_dict['event_details'] = event_details
            
        # Remove fields not in EventCreate model
        event_dict.pop('control_judges', None)
        event_dict.pop('treatment_vets', None)
        event_dict.pop('has_drug_testing', None)
        event_dict.pop('sanctioning_status', None)
        
        # Create and return the EventCreate object
        try:
            return EventCreate(**event_dict)
        except Exception as e:
            raise ValueError(f"Failed to create EventCreate model: {str(e)}")
    
    @staticmethod
    def _parse_location(location_str: str) -> Dict[str, str]:
        """
        Parse location string into structured components.
        
        Args:
            location_str: Location string (e.g. "City, State")
            
        Returns:
            Dictionary with city, state, and country components
        """
        if not location_str:
            return {}
            
        components = {}
        
        # Split by comma
        parts = [part.strip() for part in location_str.split(',')]
        
        # Basic case: City, State
        if len(parts) == 2:
            components['city'] = parts[0]
            
            # State might have country
            state_parts = parts[1].split()
            if len(state_parts) == 1:
                components['state'] = state_parts[0]
            elif len(state_parts) >= 2:
                # Last part might be the country
                if state_parts[-1].lower() in ['usa', 'canada']:
                    components['country'] = state_parts[-1]
                    components['state'] = ' '.join(state_parts[:-1])
                else:
                    components['state'] = ' '.join(state_parts)
        
        # More complex: City, State, Country or Location, City, State, [Country]
        elif len(parts) >= 3:
            # Assume the last part is state or country
            if parts[-1].lower() in ['usa', 'canada']:
                components['country'] = parts[-1]
                components['state'] = parts[-2]
                components['city'] = parts[-3]
            else:
                components['state'] = parts[-1]
                components['city'] = parts[-2]
                
        # Just one part
        elif len(parts) == 1:
            # Try to extract state from the single part
            words = parts[0].split()
            if len(words) >= 2:
                if words[-1].upper() in ['AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA', 
                                      'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD', 
                                      'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 
                                      'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC', 
                                      'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY',
                                      'AB', 'BC', 'MB', 'NB', 'NL', 'NS', 'NT', 'NU', 'ON', 'PE', 'QC', 'SK', 'YT']:
                    components['state'] = words[-1]
                    components['city'] = ' '.join(words[:-1])
                else:
                    # No clear division, assume it's all city
                    components['city'] = parts[0]
            else:
                components['city'] = parts[0]
                
        # Set default country if not determined
        if 'state' in components:
            # Check for Canadian provinces
            if components['state'] in ['AB', 'BC', 'MB', 'NB', 'NL', 'NS', 'NT', 'NU', 'ON', 'PE', 'QC', 'SK', 'YT']:
                components.setdefault('country', 'Canada')
            else:
                components.setdefault('country', 'USA')
        else:
            components.setdefault('country', 'USA')
            
        return components
    
    @staticmethod
    def _validate_url(url: Optional[str]) -> Optional[HttpUrl]:
        """
        Validate and normalize URL.
        
        Args:
            url: URL string to validate
            
        Returns:
            Validated HttpUrl or None if invalid
        """
        if not url:
            return None
            
        # Basic validation
        try:
            # Add scheme if missing
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
                
            # Parse and validate
            parsed = urlparse(url)
            if not parsed.netloc:
                return None
                
            return HttpUrl(url)
        except Exception:
            return None
    
    @classmethod
    def _build_location(cls, raw_event: Dict[str, Any]) -> Optional[Location]:
        """
        Build Location object from raw event data.
        
        Args:
            raw_event: Raw event data
            
        Returns:
            Location object or None if not enough data
        """
        location_data = {}
        
        # Try to extract from structured data first
        if 'city' in raw_event:
            location_data['city'] = raw_event['city']
            
        if 'state' in raw_event:
            location_data['state'] = raw_event['state']
            
        if 'country' in raw_event:
            location_data['country'] = raw_event['country']
            
        # If no structured data, try to parse from location string
        if not location_data and 'location' in raw_event:
            location_data = cls._parse_location(raw_event['location'])
            
        # Add address if available
        if 'location' in raw_event:
            location_data['address'] = raw_event['location']
            
        # Create Location object if we have enough data
        if location_data:
            try:
                return Location(**location_data)
            except Exception:
                # If validation fails, return what we have
                return location_data
                
        return None
    
    @classmethod
    def _build_distances(cls, raw_event: Dict[str, Any]) -> List[Distance]:
        """
        Build list of Distance objects from raw event data.
        
        Args:
            raw_event: Raw event data
            
        Returns:
            List of Distance objects
        """
        distances = []
        
        if 'distances' in raw_event and raw_event['distances']:
            for dist in raw_event['distances']:
                if isinstance(dist, dict):
                    try:
                        # Add date if missing
                        if 'date' not in dist and 'date_start' in raw_event:
                            dist['date'] = raw_event['date_start']
                            
                        distances.append(Distance(**dist))
                    except Exception:
                        # If validation fails, add as is
                        distances.append(dist)
                else:
                    # If it's just a string, create a simple Distance object
                    try:
                        distances.append(Distance(distance=str(dist)))
                    except Exception:
                        pass
                        
        return distances
    
    @classmethod
    def _build_contacts(cls, raw_event: Dict[str, Any]) -> List[ContactInfo]:
        """
        Build list of ContactInfo objects from raw event data.
        
        Args:
            raw_event: Raw event data
            
        Returns:
            List of ContactInfo objects
        """
        contacts = []
        
        # Add ride manager
        if 'ride_manager' in raw_event:
            contact_data = {
                'name': raw_event['ride_manager'],
                'role': 'Ride Manager'
            }
            
            # Add contact info if available
            if 'ride_manager_contact' in raw_event:
                contact_info = raw_event['ride_manager_contact']
                if 'email' in contact_info:
                    contact_data['email'] = contact_info['email']
                if 'phone' in contact_info:
                    contact_data['phone'] = contact_info['phone']
                    
            try:
                contacts.append(ContactInfo(**contact_data))
            except Exception:
                pass
                
        return contacts 