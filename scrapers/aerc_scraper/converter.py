"""
Convert validated event data to database schema.
"""

import logging
import json
from typing import List, Dict, Any
from datetime import datetime
from app.schemas.event import EventCreate
from .exceptions import DataExtractionError

logger = logging.getLogger(__name__)

class DataConverter:
    """Converts extracted event data to database schema."""
    
    def convert_to_db_events(self, events: List[Dict[str, Any]]) -> List[EventCreate]:
        """Convert validated event data to database event schema."""
        db_events = []
        metrics = {
            'converted': 0,
            'conversion_errors': 0
        }
        
        for event in events:
            try:
                # Debug output
                logger.debug(f"Converting event: {json.dumps(event, indent=2, default=str)}")
                
                # Format distances list with better error handling
                distances = []
                if event.get('distances'):
                    if isinstance(event['distances'], list):
                        for d in event['distances']:
                            if isinstance(d, dict) and d.get('distance'):
                                distances.append(d.get('distance'))
                            elif isinstance(d, str):
                                distances.append(d)
                    elif isinstance(event['distances'], str):
                        # Handle case where distances is a single string
                        distances = [event['distances']]
                
                # Get event start and end date with better error handling
                date_start = None
                # Try to get date from the already-transformed field name
                if event.get('date_start'):
                    if isinstance(event['date_start'], datetime):
                        date_start = event['date_start']
                    else:
                        try:
                            date_start = datetime.strptime(event['date_start'], "%Y-%m-%d")
                        except ValueError:
                            try:
                                # Try alternative formats
                                date_start = datetime.strptime(event['date_start'], "%m/%d/%Y")
                            except ValueError:
                                logger.error(f"Could not parse date_start: {event['date_start']}")
                # Fallback to 'date' field
                elif event.get('date'):
                    if isinstance(event['date'], datetime):
                        date_start = event['date']
                    else:
                        try:
                            date_start = datetime.strptime(event['date'], "%Y-%m-%d")
                        except ValueError:
                            try:
                                # Try alternative formats
                                date_start = datetime.strptime(event['date'], "%m/%d/%Y")
                            except ValueError:
                                logger.error(f"Could not parse date: {event['date']}")
                
                # Set default date if missing
                if not date_start:
                    date_start = datetime.now()
                    logger.warning(f"Missing start date, using current date: {date_start}")
                
                date_end = date_start
                
                # If multiple days, find the latest date
                if event.get('date_end'):
                    # If date_end already exists, use it
                    if isinstance(event['date_end'], datetime):
                        date_end = event['date_end']
                    else:
                        try:
                            date_end = datetime.strptime(event['date_end'], "%Y-%m-%d")
                        except (ValueError, TypeError):
                            logger.error(f"Could not parse date_end: {event['date_end']}")
                elif event.get('distances') and isinstance(event['distances'], list):
                    for distance in event['distances']:
                        if isinstance(distance, dict) and distance.get('date'):
                            try:
                                distance_date = None
                                if isinstance(distance['date'], datetime):
                                    distance_date = distance['date']
                                else:
                                    distance_date = datetime.strptime(distance['date'], '%Y-%m-%d')
                                
                                if distance_date and (date_end is None or distance_date > date_end):
                                    date_end = distance_date
                            except (ValueError, TypeError):
                                continue
                
                # Extract location with flexible field mapping
                location = "Unknown Location"
                if event.get('location'):
                    if isinstance(event['location'], dict):
                        # Handle structured location data
                        loc_parts = []
                        if event['location'].get('name'):
                            loc_parts.append(event['location']['name'])
                        if event['location'].get('city'):
                            loc_parts.append(event['location']['city'])
                        if event['location'].get('state'):
                            loc_parts.append(event['location']['state'])
                        location = ", ".join(loc_parts)
                    else:
                        location = event['location']
                
                # Format contact information
                contact_info = []
                # Try both ride_manager and rideManager fields
                if event.get('ride_manager'):
                    contact_info.append(f"Ride Manager: {event['ride_manager']}")
                elif event.get('rideManager'):
                    contact_info.append(f"Ride Manager: {event['rideManager']}")
                
                # Check for manager contact information from different possible fields
                if event.get('manager_contact'):
                    contact_info.append(event['manager_contact'])
                elif event.get('rideManagerContact'):
                    contact = event['rideManagerContact']
                    if isinstance(contact, dict):
                        if contact.get('phone'):
                            contact_info.append(f"Phone: {contact['phone']}")
                        if contact.get('email'):
                            contact_info.append(f"Email: {contact['email']}")
                
                # Add individual contact fields if they exist
                if event.get('manager_email'):
                    contact_info.append(f"Email: {event['manager_email']}")
                if event.get('manager_phone'):
                    contact_info.append(f"Phone: {event['manager_phone']}")
                
                # Format control judges with good fallback handling
                judges = []
                # Try different possible field names
                if event.get('judges') and isinstance(event['judges'], list):
                    judges = event['judges']
                elif event.get('controlJudges') and isinstance(event['controlJudges'], list):
                    for judge in event['controlJudges']:
                        if isinstance(judge, dict) and judge.get('name'):
                            role = judge.get('role', 'Judge')
                            judges.append(f"{role}: {judge['name']}")
                        elif isinstance(judge, str):
                            judges.append(judge)
                
                # Get event name with fallbacks
                name = "Unnamed AERC Event"
                if event.get('name'):
                    name = event['name']
                elif event.get('rideName'):
                    name = event['rideName']
                
                # Create event object - protect against type errors with better handling
                try:
                    db_event = EventCreate(
                        name=name,
                        date_start=date_start,
                        date_end=date_end,
                        location=location,
                        region=event.get('region', 'Unknown'),
                        event_type='endurance',
                        description="\n".join(contact_info) if contact_info else None,
                        additional_info="\n".join(judges) if judges else None,
                        distances=distances,
                        map_url=event.get('map_url') or event.get('mapLink'),
                        has_intro_ride=bool(event.get('has_intro_ride', False)) or bool(event.get('hasIntroRide', False)),
                        external_id=str(event.get('external_id') or event.get('tag') or "") or None,
                        source='AERC',
                        is_canceled=bool(event.get('is_canceled', False))
                    )
                    
                    db_events.append(db_event)
                    metrics['converted'] += 1
                    
                except Exception as e:
                    metrics['conversion_errors'] += 1
                    logger.error(f"Error creating EventCreate object: {e}")
                    continue
                
            except Exception as e:
                metrics['conversion_errors'] += 1
                logger.error(f"Error converting event to DB schema: {e}")
                # Add the event data to the error log
                logger.error(f"Event data causing error: {json.dumps(event, indent=2, default=str) if event else 'None'}")
                continue
        
        if metrics['conversion_errors'] > 0:
            logger.warning(
                f"Converted {metrics['converted']} events with {metrics['conversion_errors']} errors"
            )
        else:
            logger.info(f"Successfully converted {metrics['converted']} events")
        
        self.db_events = db_events
        return db_events
    
    def get_metrics(self) -> dict:
        """Get conversion metrics."""
        return {
            'total_converted': len(self.db_events) if hasattr(self, 'db_events') else 0
        }