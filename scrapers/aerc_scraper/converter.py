"""
Convert validated event data to database schema.
"""

import logging
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
                # Format distances list
                distances = []
                if event.get('distances'):
                    distances = [d.get('distance') for d in event['distances'] if d.get('distance')]
                
                # Get event start and end date
                date_start = datetime.strptime(event.get('date'), "%Y-%m-%d") if event.get('date') else None
                date_end = date_start
                
                # If multiple days, find the latest date
                if event.get('distances'):
                    for distance in event['distances']:
                        if distance.get('date'):
                            try:
                                distance_date = datetime.strptime(distance['date'], '%Y-%m-%d')
                                if distance_date > date_end:
                                    date_end = distance_date
                            except ValueError:
                                continue
                
                # Format contact information
                contact_info = []
                if event.get('rideManager'):
                    contact_info.append(f"Ride Manager: {event['rideManager']}")
                if event.get('rideManagerContact'):
                    contact = event['rideManagerContact']
                    if contact.get('phone'):
                        contact_info.append(f"Phone: {contact['phone']}")
                    if contact.get('email'):
                        contact_info.append(f"Email: {contact['email']}")
                
                # Format control judges
                judges = []
                if event.get('controlJudges'):
                    for judge in event['controlJudges']:
                        if judge.get('name'):
                            role = judge.get('role', 'Judge')
                            judges.append(f"{role}: {judge['name']}")
                
                # Create event object
                db_event = EventCreate(
                    name=event['rideName'],
                    date_start=date_start,
                    date_end=date_end,
                    location=event['location'],
                    region=event.get('region', 'Unknown'),
                    event_type='endurance',
                    description="\n".join(contact_info) if contact_info else None,
                    additional_info="\n".join(judges) if judges else None,
                    distances=distances,
                    map_url=event.get('mapLink'),
                    has_intro_ride=event.get('hasIntroRide', False),
                    external_id=str(event.get('tag')) if event.get('tag') else None,
                    source='AERC'
                )
                
                db_events.append(db_event)
                metrics['converted'] += 1
                
            except Exception as e:
                metrics['conversion_errors'] += 1
                logger.error(f"Error converting event to DB schema: {e}")
                continue
        
        if metrics['conversion_errors'] > 0:
            logger.warning(
                f"Converted {metrics['converted']} events with {metrics['conversion_errors']} errors"
            )
        else:
            logger.info(f"Successfully converted {metrics['converted']} events")
        
        return db_events
    
    def get_metrics(self) -> dict:
        """Get conversion metrics."""
        return {
            'total_converted': len(self.db_events) if hasattr(self, 'db_events') else 0
        }