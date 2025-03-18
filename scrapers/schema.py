"""Shared schema validation module for scrapers.

This module links scraper data formats to the core event schema definitions.
Rather than defining duplicate schemas, it reuses the core schemas from app/schemas/event.py.
"""

from datetime import datetime
from typing import Dict, Any

# Import the core schemas directly to avoid duplication
from app.schemas.event import (
    EventSourceEnum, EventTypeEnum, EventBase, AERCEvent, SERAEvent, UMECRAEvent,
    ContactInfo, EventDistance as Distance, LocationDetails as Location,
    Coordinates, validate_event, SOURCE_SCHEMAS
)

# Re-export all imported symbols for backward compatibility
__all__ = [
    'EventSourceEnum', 'EventTypeEnum', 'EventBase', 'AERCEvent', 'SERAEvent', 'UMECRAEvent',
    'ContactInfo', 'Distance', 'Location', 'Coordinates', 'validate_event', 'SOURCE_SCHEMAS'
]

# Function to convert scraped data to the centralized schema format
def convert_to_event_schema(source_data: Dict[str, Any], source: str) -> Dict[str, Any]:
    """Convert source-specific scraped data to the standard event schema format.
    
    Args:
        source_data: Raw data from the scraper
        source: The source identifier (e.g., 'AERC')
        
    Returns:
        Dict formatted according to the appropriate schema for the given source
    """
    # This function can be expanded to handle specific format conversions
    # For now, just ensure the source is set
    source_data['source'] = source
    return source_data