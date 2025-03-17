"""AERC event data validation module."""

import logging
import json
import sys
import os
from typing import List, Dict, Any
from datetime import datetime
from pydantic import ValidationError

from ..schema import AERCEvent, EventSourceEnum, EventTypeEnum, validate_event
from ..exceptions import ValidationError as ScraperValidationError

logger = logging.getLogger(__name__)

class DataValidator:
    """Validates extracted event data."""
    
    def __init__(self, debug_mode=False, exit_on_first_error=False):
        """Initialize validator."""
        self.metrics = {
            'validated': 0,
            'invalid': 0,
            'validation_time': 0.0
        }
        self.debug_mode = debug_mode or os.environ.get('SCRAPER_DEBUG', '').lower() == 'true'
        self.exit_on_first_error = exit_on_first_error or os.environ.get('SCRAPER_EXIT_ON_ERROR', '').lower() == 'true'
    
    def validate_events(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate extracted event data."""
        if not events:
            logger.warning("No events to validate")
            return []
        
        valid_events = []
        start_time = datetime.now()
        
        for event_data in events:
            try:
                # Ensure required base fields are present
                self._check_required_fields(event_data)
                
                # Add AERC-specific fields
                event_data['source'] = EventSourceEnum.AERC
                if 'event_type' not in event_data:
                    event_data['event_type'] = EventTypeEnum.ENDURANCE
                
                # Convert dates to proper format
                self._convert_dates(event_data)
                
                # Structure location data
                if 'location' in event_data and isinstance(event_data['location'], str):
                    event_data['location'] = self._parse_location(event_data['location'])
                
                # Structure contact information
                self._structure_contacts(event_data)
                
                # Structure distances
                if 'distances' in event_data:
                    event_data['distances'] = self._structure_distances(
                        event_data['distances'],
                        event_data.get('date_start')
                    )
                
                # Validate against schema
                validated_event = validate_event(event_data, EventSourceEnum.AERC)
                valid_events.append(validated_event.model_dump())
                self.metrics['validated'] += 1
                
            except (ValidationError, ValueError, ScraperValidationError) as e:
                self.metrics['invalid'] += 1
                error_msg = f"Validation error for event {event_data.get('name', 'Unknown')}: {str(e)}"
                logger.error(error_msg)
                
                # Print the JSON blob for debugging if in debug mode
                if self.debug_mode:
                    logger.debug(f"JSON blob with validation error: {json.dumps(event_data, indent=2, default=str)}")
                
                # Exit after first error if configured to do so
                if self.exit_on_first_error:
                    logger.error("Exiting after first validation error due to SCRAPER_EXIT_ON_ERROR=true")
                    sys.exit(1)
                
                continue
        
        self.metrics['validation_time'] = (datetime.now() - start_time).total_seconds()
        
        if not valid_events:
            logger.warning("No events passed validation")
        else:
            logger.info(f"Validated {len(valid_events)} events")
        
        return valid_events
    
    def _check_required_fields(self, event_data: Dict[str, Any]) -> None:
        """Check required fields are present."""
        required_fields = {'name', 'date_start', 'location'}
        missing_fields = required_fields - set(event_data.keys())
        
        if missing_fields:
            raise ScraperValidationError(
                f"Missing required fields: {', '.join(missing_fields)}"
            )
    
    def _convert_dates(self, event_data: Dict[str, Any]) -> None:
        """Convert date strings to datetime objects."""
        date_fields = ['date_start', 'date_end']
        for field in date_fields:
            if field in event_data and isinstance(event_data[field], str):
                try:
                    # Try common date formats
                    for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%Y-%m-%dT%H:%M:%S']:
                        try:
                            event_data[field] = datetime.strptime(
                                event_data[field], fmt
                            )
                            break
                        except ValueError:
                            continue
                except Exception as e:
                    raise ScraperValidationError(f"Invalid date format in {field}: {str(e)}")
    
    def _parse_location(self, location_str: str) -> Dict[str, Any]:
        """Parse location string into structured data."""
        location_data = {"name": location_str}
        
        # Try to extract city and state
        # Example format: "Venue Name, City, ST"
        parts = location_str.split(',')
        if len(parts) >= 2:
            location_data['name'] = parts[0].strip()
            location_data['city'] = parts[1].strip()
            if len(parts) >= 3:
                location_data['state'] = parts[2].strip()
        
        return location_data
    
    def _structure_contacts(self, event_data: Dict[str, Any]) -> None:
        """Structure contact information."""
        contacts = []
        
        # Add ride manager if present
        if 'ride_manager' in event_data:
            manager_contact = {
                'name': event_data['ride_manager'],
                'role': 'Ride Manager'
            }
            if 'ride_manager_email' in event_data:
                manager_contact['email'] = event_data['ride_manager_email']
            if 'ride_manager_phone' in event_data:
                manager_contact['phone'] = event_data['ride_manager_phone']
            contacts.append(manager_contact)
        
        # Add control judges if present
        if 'control_judges' in event_data:
            if isinstance(event_data['control_judges'], list):
                for judge in event_data['control_judges']:
                    if isinstance(judge, str):
                        contacts.append({
                            'name': judge,
                            'role': 'Control Judge'
                        })
                    elif isinstance(judge, dict):
                        judge['role'] = judge.get('role', 'Control Judge')
                        contacts.append(judge)
        
        event_data['contacts'] = contacts
    
    def _structure_distances(
        self,
        distances: List[Any],
        event_date: datetime
    ) -> List[Dict[str, Any]]:
        """Structure distance information."""
        structured_distances = []
        
        for distance in distances:
            if isinstance(distance, str):
                # Simple distance string
                structured_distances.append({
                    'distance': distance,
                    'date': event_date
                })
            elif isinstance(distance, dict):
                # Already structured, ensure date is present
                if 'date' not in distance:
                    distance['date'] = event_date
                structured_distances.append(distance)
        
        return structured_distances
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get validation metrics."""
        return self.metrics.copy()