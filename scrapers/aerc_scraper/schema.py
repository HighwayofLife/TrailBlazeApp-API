"""
AERC-specific schema and conversion utilities.

This module provides:
1. A JSON schema for validating raw AERC data
2. Conversion utilities to transform AERC-specific data to the centralized app schema
3. Helper functions for AERC-specific data validation and processing

All AERC-specific schema logic should be contained in this module to keep
the core schema definitions clean and source-agnostic.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple, cast
from datetime import datetime, date
import re

# Import from shared schema module rather than directly from app
from scrapers.schema import AERCEvent, EventSourceEnum, validate_event_data

# Configure logger
logger = logging.getLogger(__name__)

# JSON Schema for validating raw AERC data
# This is used to validate data before conversion to Pydantic models
AERC_EVENT_SCHEMA = {
    'type': 'object',
    'properties': {
        'rideName': {'type': 'string'},
        'date': {'type': 'string', 'format': 'date'},
        'region': {'type': 'string'},
        'location': {'type': 'string'},
        'distances': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'distance': {'type': 'string'},
                    'date': {'type': 'string', 'format': 'date'},
                    'startTime': {'type': 'string'}
                },
                'required': ['distance', 'date']
            }
        },
        'rideManager': {'type': 'string'},
        'rideManagerContact': {
            'type': 'object',
            'properties': {
                'name': {'type': 'string'},
                'email': {'type': 'string', 'format': 'email'},
                'phone': {'type': 'string'}
            }
        },
        'controlJudges': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'role': {'type': 'string'},
                    'name': {'type': 'string'}
                },
                'required': ['role', 'name']
            }
        },
        'mapLink': {'type': 'string'},
        'hasIntroRide': {'type': 'boolean'},
        'tag': {'type': ['integer', 'string']},  # Some systems return it as string
        'is_canceled': {'type': 'boolean'},
        'description': {'type': 'string'},
        'directions': {'type': 'string'},
        'website': {'type': 'string'},
        'flyer_url': {'type': 'string'},
        'location_details': {
            'type': 'object',
            'properties': {
                'city': {'type': 'string'},
                'state': {'type': 'string'},
                'country': {'type': 'string'}
            }
        },
        'coordinates': {
            'type': 'object',
            'properties': {
                'latitude': {'type': 'number'},
                'longitude': {'type': 'number'}
            }
        },
        'ride_days': {'type': 'integer'},
        'is_multi_day_event': {'type': 'boolean'},
        'is_pioneer_ride': {'type': 'boolean'}
    },
    'required': ['rideName', 'date', 'region', 'location']
}

def convert_to_app_schema(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert raw AERC data to the centralized app schema format.

    This function handles AERC-specific field mappings and data transformations
    to match the expectations of the AERCEvent schema.

    Args:
        raw_data: Raw data from the AERC scraper

    Returns:
        Dict formatted according to the AERCEvent schema
    """
    # Create mapping from AERC-specific fields to app schema fields
    result = {
        'name': raw_data.get('rideName'),
        'source': EventSourceEnum.AERC,
        'event_type': 'endurance',
        'date_start': raw_data.get('date'),
        'location': raw_data.get('location'),
        'region': raw_data.get('region'),
        'ride_manager': raw_data.get('rideManager'),
        'map_link': raw_data.get('mapLink'),
        'has_intro_ride': raw_data.get('hasIntroRide', False),
        'is_canceled': raw_data.get('is_canceled', False),
        'ride_id': str(raw_data.get('tag')) if raw_data.get('tag') else None,
        'description': raw_data.get('description'),
        'directions': raw_data.get('directions'),
        'website': raw_data.get('website'),
        'flyer_url': raw_data.get('flyer_url'),
    }

    # Handle optional multi-day event data if provided
    if 'ride_days' in raw_data:
        result['ride_days'] = raw_data.get('ride_days')
    if 'is_multi_day_event' in raw_data:
        result['is_multi_day_event'] = raw_data.get('is_multi_day_event')
    if 'is_pioneer_ride' in raw_data:
        result['is_pioneer_ride'] = raw_data.get('is_pioneer_ride')

    # Otherwise calculate based on distance dates if available
    elif 'distances' in raw_data and isinstance(raw_data['distances'], list):
        unique_dates = set()
        for d in raw_data['distances']:
            if 'date' in d:
                unique_dates.add(d['date'])

        days = len(unique_dates)
        if days > 0:
            result['ride_days'] = days
            result['is_multi_day_event'] = days > 1
            result['is_pioneer_ride'] = days >= 3

    # Handle structured data
    if raw_data.get('distances'):
        result['distances'] = [
            {
                'distance': d.get('distance'),
                'date': d.get('date'),
                'start_time': d.get('startTime')
            }
            for d in raw_data.get('distances', [])
        ]

    # Handle contact information
    if raw_data.get('rideManagerContact'):
        contact = raw_data.get('rideManagerContact')
        result['manager_email'] = contact.get('email')
        result['manager_phone'] = contact.get('phone')

    # Handle control judges - map to specific field used in AERCEvent
    if raw_data.get('controlJudges'):
        result['control_judges'] = [
            {
                'name': j.get('name'),
                'role': j.get('role')
            }
            for j in raw_data.get('controlJudges', [])
        ]

    # Handle location details
    if raw_data.get('location_details'):
        result['location_details'] = raw_data.get('location_details')

    # Handle coordinates
    if raw_data.get('coordinates'):
        result['coordinates'] = raw_data.get('coordinates')
        # Also set top-level latitude/longitude for compatibility
        if 'latitude' in raw_data.get('coordinates', {}):
            result['latitude'] = raw_data['coordinates']['latitude']
        if 'longitude' in raw_data.get('coordinates', {}):
            result['longitude'] = raw_data['coordinates']['longitude']

    return result

def validate_aerc_event(data: Dict[str, Any]) -> AERCEvent:
    """
    Validate and convert raw AERC data to an AERCEvent instance.

    Args:
        data: Raw AERC event data

    Returns:
        Validated AERCEvent instance

    Raises:
        ValueError: If validation fails
    """
    # First convert to app schema format
    converted_data = convert_to_app_schema(data)

    # Then validate with Pydantic model
    return cast(AERCEvent, validate_event_data(converted_data, 'AERC', AERCEvent))

def extract_ride_id_from_url(url: str) -> Optional[str]:
    """
    Extract AERC ride ID from a URL.

    Args:
        url: URL possibly containing a ride ID

    Returns:
        Extracted ride ID or None if not found
    """
    # Common patterns for ride IDs in URLs
    patterns = [
        r'ride/(\d+)',
        r'ride_id=(\d+)',
        r'tag=(\d+)'
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return None

def parse_aerc_date(date_str: str) -> Optional[date]:
    """
    Parse an AERC-formatted date string.

    AERC dates can come in various formats including:
    - "Mar 28, 2025"
    - "2025-03-28"
    - "03/28/2025"

    Args:
        date_str: Date string to parse

    Returns:
        Parsed date object or None if parsing fails
    """
    formats = [
        "%b %d, %Y",  # Mar 28, 2025
        "%Y-%m-%d",   # 2025-03-28
        "%m/%d/%Y",   # 03/28/2025
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue

    logger.warning(f"Could not parse date: {date_str}")
    return None
