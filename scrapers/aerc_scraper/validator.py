"""
Data validation module using pydantic models.
"""

import logging
import hashlib
from datetime import datetime
import re
from typing import List, Dict, Any, Optional, Set
from pydantic import BaseModel, Field, validator, EmailStr
from .exceptions import ValidationError

logger = logging.getLogger(__name__)

class RideManagerContact(BaseModel):
    """Ride manager contact information."""
    name: Optional[str] = Field(None, description="Name of the ride manager")
    email: Optional[EmailStr] = Field(None, description="Email of the ride manager")
    phone: Optional[str] = Field(None, description="Phone number of the ride manager")
    
    @validator('phone')
    def validate_phone(cls, v):
        """Validate phone number format."""
        if v:
            # Remove all non-digit characters
            digits = re.sub(r'[^\d+]', '', v)
            if not re.match(r'^\+?\d{10,}$', digits):
                raise ValueError("Invalid phone number format")
            return digits
        return v

class ControlJudge(BaseModel):
    """Control judge information."""
    role: str = Field(..., description="Role of the judge (e.g., Head Control Judge)")
    name: str = Field(..., description="Name of the judge")

class Distance(BaseModel):
    """Ride distance information."""
    distance: str = Field(..., description="Distance of the ride")
    date: str = Field(..., description="Date of the ride (YYYY-MM-DD)")
    startTime: Optional[str] = Field(None, description="Start time of the ride")
    
    @validator('date')
    def validate_date(cls, v):
        """Validate date format."""
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError("Invalid date format, should be YYYY-MM-DD")

class AERCEvent(BaseModel):
    """AERC event information."""
    rideName: str = Field(..., description="Name of the ride")
    date: str = Field(..., description="Primary date of the event (YYYY-MM-DD)")
    region: str = Field(..., description="AERC region")
    location: str = Field(..., description="Location of the event")
    distances: List[Distance] = Field(default_factory=list, description="Available ride distances")
    rideManager: Optional[str] = Field(None, description="Name of the ride manager")
    rideManagerContact: Optional[RideManagerContact] = Field(None, description="Contact details for the ride manager")
    controlJudges: List[ControlJudge] = Field(default_factory=list, description="Control judges for the event")
    mapLink: Optional[str] = Field(None, description="Google Maps link to the event location")
    hasIntroRide: Optional[bool] = Field(False, description="Whether the event has an intro ride")
    tag: Optional[int] = Field(None, description="External ID for the event")
    
    @validator('date')
    def validate_date(cls, v):
        """Validate date format."""
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError("Invalid date format, should be YYYY-MM-DD")
    
    @validator('mapLink')
    def validate_map_link(cls, v):
        """Validate Google Maps link."""
        if v and not v.startswith(('https://maps.google.com', 'https://www.google.com/maps')):
            raise ValueError("Invalid Google Maps link")
        return v

class DataValidator:
    """Validates extracted event data."""
    
    def __init__(self):
        self.metrics = {
            'events_found': 0,
            'events_valid': 0,
            'events_duplicate': 0,
            'validation_errors': 0
        }
        self.seen_events: Set[str] = set()
    
    def validate_events(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate and clean extracted events data."""
        self.metrics['events_found'] = len(events)
        valid_events = []
        
        for event in events:
            try:
                # Generate event identifier for deduplication
                event_key = f"{event.get('rideName', '')}-{event.get('date', '')}-{event.get('location', '')}"
                if event_key in self.seen_events:
                    self.metrics['events_duplicate'] += 1
                    logger.debug(f"Skipping duplicate event: {event_key}")
                    continue
                self.seen_events.add(event_key)
                
                # Fill in defaults for required fields
                event['rideName'] = event.get('rideName', 'Untitled AERC Event').strip()
                event['region'] = event.get('region', 'Unknown Region').strip()
                event['date'] = event.get('date')
                
                if not event['date']:
                    self.metrics['validation_errors'] += 1
                    logger.warning(f"Skipping event with no date: {event['rideName']}")
                    continue
                
                # Clean location
                event['location'] = event.get('location', 'Location TBA').strip()
                if event['location'].lower() in ['tba', 'to be announced']:
                    event['location'] = 'Location TBA'
                
                # Generate tag if missing
                if not event.get('tag'):
                    event['tag'] = int(hashlib.md5(
                        f"{event['rideName']}-{event['date']}-{event['location']}".encode()
                    ).hexdigest()[:8], 16)
                
                # Validate through pydantic model
                validated_event = AERCEvent.model_validate(event)
                valid_events.append(validated_event.model_dump())
                
            except ValueError as e:
                self.metrics['validation_errors'] += 1
                logger.error(f"Validation error for event: {str(e)}")
                continue
                
            except Exception as e:
                self.metrics['validation_errors'] += 1
                logger.error(f"Error validating event: {str(e)}")
                continue
        
        self.metrics['events_valid'] = len(valid_events)
        logger.info(
            f"Validated {len(valid_events)} out of {len(events)} events "
            f"({self.metrics['validation_errors']} errors, "
            f"{self.metrics['events_duplicate']} duplicates)"
        )
        return valid_events
    
    def get_metrics(self) -> dict:
        """Get validation metrics."""
        return self.metrics.copy()