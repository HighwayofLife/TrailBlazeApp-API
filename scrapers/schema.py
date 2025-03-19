"""Shared schema validation module for scrapers.

This module serves as a bridge between the core event schema and scrapers,
providing consistent access to schema definitions and validation functions.
All scrapers should import schema classes from this module rather than
directly from app/schemas/event.py to maintain a single point of maintenance.

This approach allows:
1. Adding scraper-specific extensions to schemas without modifying the core schema
2. Handling backward compatibility for scrapers if the core schema changes
3. Providing scraper-specific validation and conversion utilities
"""

from datetime import datetime
from typing import Dict, Any, List, Optional, Union, TypeVar, Type, cast

# Import the core schemas directly to avoid duplication
from app.schemas.event import (
    EventSourceEnum, EventTypeEnum, RegionEnum,
    EventBase, EventCreate, EventUpdate, EventResponse,
    AERCEvent, SERAEvent, UMECRAEvent,
    ContactInfo, EventDistance, LocationDetails,
    Coordinates, validate_event, SOURCE_SCHEMAS
)

# Type variable for event schemas
EventSchema = TypeVar('EventSchema', bound=EventBase)

# Re-export all imported symbols for backward compatibility
__all__ = [
    'EventSourceEnum', 'EventTypeEnum', 'RegionEnum', 'EventBase',
    'EventCreate', 'EventUpdate', 'EventResponse',
    'AERCEvent', 'SERAEvent', 'UMECRAEvent',
    'ContactInfo', 'EventDistance', 'LocationDetails',
    'Coordinates', 'validate_event', 'SOURCE_SCHEMAS',
    'convert_to_event_schema', 'validate_event_data'
]

def convert_to_event_schema(
    source_data: Dict[str, Any],
    source: str,
    schema_class: Optional[Type[EventSchema]] = None
) -> Dict[str, Any]:
    """
    Convert source-specific scraped data to the standard event schema format.

    This function is a general converter that ensures the source field is set.
    For source-specific conversions, each scraper should implement its own
    converter function that maps its unique fields to the common schema.

    Args:
        source_data: Raw data from the scraper
        source: The source identifier (e.g., 'AERC')
        schema_class: Optional specific schema class to use for validation

    Returns:
        Dict formatted according to the appropriate schema for the given source
    """
    # Ensure source is set correctly
    source_data['source'] = source

    # Add required datetime fields with proper formatting if they're strings
    if 'date_start' in source_data and isinstance(source_data['date_start'], str):
        # Try to parse the date string
        try:
            # If it's just a date (without time), append time to create a valid datetime
            if 'T' not in source_data['date_start'] and ' ' not in source_data['date_start']:
                source_data['date_start'] = f"{source_data['date_start']}T00:00:00"
        except Exception:
            # If parsing fails, leave it as is - the schema validator will handle it
            pass

    return source_data

def validate_event_data(
    data: Dict[str, Any],
    source: str,
    schema_class: Optional[Type[EventSchema]] = None
) -> EventSchema:
    """
    Validate and convert raw event data to the appropriate schema.

    Args:
        data: Event data dictionary to validate
        source: Source identifier (e.g., 'AERC')
        schema_class: Optional schema class to use instead of automatic selection

    Returns:
        Validated instance of the appropriate event schema

    Raises:
        ValueError: If validation fails
    """
    # If no specific schema class is provided, select based on source
    if schema_class is None:
        source_enum = EventSourceEnum(source)
        schema_class = cast(Type[EventSchema], SOURCE_SCHEMAS.get(source_enum, EventBase))

    # Validate using the model_validate method (Pydantic V2)
    try:
        return schema_class.model_validate(data)
    except Exception as e:
        raise ValueError(f"Invalid event data for source {source}: {e}")
