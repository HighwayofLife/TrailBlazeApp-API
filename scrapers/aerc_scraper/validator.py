"""AERC event data validation module."""

import logging
import json
import sys
import os
from typing import List, Dict, Any, Tuple
from datetime import datetime
from pydantic import ValidationError
from app.logging_config import get_logger

from ..schema import AERCEvent, EventSourceEnum, EventTypeEnum, validate_event
from ..exceptions import ValidationError as ScraperValidationError

# Use the properly configured logger from app.logging_config
logger = get_logger("scrapers.aerc_scraper.validator")

class DataValidator:
    """Validates extracted event data."""
    
    def __init__(self, debug_mode=False, exit_on_first_error=False):
        """Initialize validator."""
        self.metrics = {
            'validated': 0,
            'invalid': 0,
            'validation_time': 0.0,
            'validation_failures': []  # Store details about validation failures
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
                # Store the original data for potential retry
                original_data = event_data.copy()
                
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
                
                # Store information about the validation failure
                failure_info = {
                    'event_data': original_data,
                    'error_type': type(e).__name__,
                    'error_message': str(e),
                    'event_name': event_data.get('name', 'Unknown'),
                    'missing_fields': []
                }
                
                # Check for missing required fields
                for field in ['name', 'date_start', 'location']:
                    if field not in event_data or not event_data.get(field):
                        failure_info['missing_fields'].append(field)
                
                # Check for date format issues
                if 'date_start' in event_data and isinstance(event_data.get('date_start'), str):
                    try:
                        datetime.strptime(event_data['date_start'], '%Y-%m-%d')
                    except ValueError:
                        failure_info['date_format_issue'] = True
                
                self.metrics['validation_failures'].append(failure_info)
                
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

    def validate_event(self, event: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate an event's data."""
        issues = []
        
        # Log event being validated
        logger.debug(f"Validating event: {event.get('name', 'Unknown')}")
        
        # Check required fields
        required_fields = ['name', 'date', 'location']
        for field in required_fields:
            if not event.get(field):
                issues.append(f"Missing required field: {field}")
                logger.warning(f"Event validation failed: Missing {field}")
        
        # Validate date format
        if event.get('date'):
            try:
                datetime.strptime(event['date'], '%Y-%m-%d')
            except ValueError:
                issues.append("Invalid date format. Must be YYYY-MM-DD")
                logger.warning(f"Event validation failed: Invalid date format: {event['date']}")
        
        # Validate location
        if event.get('location'):
            if len(event['location']) < 3:
                issues.append("Location too short")
                logger.warning(f"Event validation failed: Location too short: {event['location']}")
        
        # Log validation result
        if issues:
            logger.warning(f"Event validation failed with {len(issues)} issues: {', '.join(issues)}")
        else:
            logger.info(f"Event validation passed: {event.get('name', 'Unknown')}")
        
        return len(issues) == 0, issues