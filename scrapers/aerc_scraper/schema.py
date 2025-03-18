"""Schema definitions for AERC event data.

This module provides both:
1. JSON schema for validating raw scraped data
2. Helper functions to convert AERC-specific data to the centralized app schema
"""

from typing import Dict, Any
from app.schemas.event import AERCEvent, EventSourceEnum

# JSON Schema for validating raw AERC data
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
        'tag': {'type': 'integer'},
        'is_canceled': {'type': 'boolean'}
    },
    'required': ['rideName', 'date', 'region', 'location']
}

def convert_to_app_schema(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert raw AERC data to the centralized app schema format.
    
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
    }
    
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
    
    # Handle control judges
    if raw_data.get('controlJudges'):
        result['judges'] = [
            {
                'name': j.get('name'),
                'role': j.get('role')
            }
            for j in raw_data.get('controlJudges', [])
        ]
    
    return result
