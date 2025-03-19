"""
AERC Event Data Validators.

This module provides validation functions for AERC event data. It ensures that
data extracted from the AERC website adheres to the expected structure and types
before being transformed into the application's data models.

The validators follow the schema definitions from app/schemas/event.py,
which serves as the single source of truth for event data structures.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
from urllib.parse import urlparse
from pydantic import HttpUrl, ValidationError

# Import from the centralized schema
from app.schemas import (
    EventSourceEnum,
    EventTypeEnum,
    AERCEvent,
    LocationDetails,
    Coordinates,
    ControlJudge
)

logger = logging.getLogger(__name__)


def validate_url(url: Optional[str]) -> Optional[HttpUrl]:
    """
    Validate and normalize a URL string.

    Args:
        url: URL string to validate

    Returns:
        Validated HttpUrl object or None if invalid

    Example:
        >>> validate_url("example.com")
        HttpUrl('https://example.com', scheme='https', host='example.com', tld='com', ...)
        >>> validate_url("not-a-url")
        None
    """
    if not url:
        return None

    # Skip validation for obviously invalid URLs
    if ' ' in url or not ('.' in url) or url == 'not-a-url':
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
    except (ValueError, ValidationError):
        return None


def validate_event(event_data: Dict[str, Any]) -> bool:
    """
    Validate event data against schema requirements.

    Checks if the required fields are present and if the data types
    are correct according to the AERCEvent schema.

    Args:
        event_data: Dictionary containing event data to validate

    Returns:
        True if validation passes, False otherwise

    Example:
        >>> validate_event({"name": "Test Event", "date_start": "2023-01-01", "source": "AERC"})
        True
    """
    required_fields = ["name", "date_start"]

    # Check required fields
    for field in required_fields:
        if field not in event_data or not event_data[field]:
            logger.warning(f"Required field missing: {field}")
            return False

    # Validate against AERCEvent schema
    try:
        # Since AERCEvent constructor will already validate most fields,
        # this is just an additional check to ensure the data is valid
        AERCEvent(
            # Set required fields
            name=event_data.get('name', ''),
            source=EventSourceEnum.AERC,
            event_type=EventTypeEnum.ENDURANCE,
            date_start=event_data.get('date_start', datetime.now()),
            location=event_data.get('location', ''),

            # Pass other fields as they are
            **{k: v for k, v in event_data.items()
               if k not in ['name', 'source', 'event_type', 'date_start', 'location']}
        )
        return True
    except (ValueError, ValidationError, TypeError) as e:
        logger.warning(f"Event validation failed: {e}")
        return False


def validate_location_details(location_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Validate location details against the LocationDetails schema.

    Args:
        location_data: Dictionary containing location data

    Returns:
        Validated location details dictionary or None if validation fails

    Example:
        >>> validate_location_details({"city": "Sonoita", "state": "AZ", "country": "USA"})
        {'city': 'Sonoita', 'state': 'AZ', 'country': 'USA'}
    """
    try:
        # Validate using LocationDetails schema
        location = LocationDetails(**location_data)
        # Return as dict for easier manipulation
        return location.model_dump()
    except (ValueError, ValidationError, TypeError) as e:
        logger.warning(f"Location details validation failed: {e}")
        return None


def validate_coordinates(coords_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Validate coordinates data against the Coordinates schema.

    Args:
        coords_data: Dictionary containing latitude and longitude

    Returns:
        Validated coordinates dictionary or None if validation fails

    Example:
        >>> validate_coordinates({"latitude": 31.6784, "longitude": -110.6255})
        {'latitude': 31.6784, 'longitude': -110.6255}
    """
    if not coords_data or 'latitude' not in coords_data or 'longitude' not in coords_data:
        return None

    try:
        # Validate using Coordinates schema
        coords = Coordinates(**coords_data)
        # Return as dict for easier manipulation
        return coords.model_dump()
    except (ValueError, ValidationError, TypeError) as e:
        logger.warning(f"Coordinates validation failed: {e}")
        return None


def validate_control_judges(judges_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Validate control judges data against the ControlJudge schema.

    Args:
        judges_data: List of dictionaries containing judge information

    Returns:
        List of validated judge dictionaries

    Example:
        >>> validate_control_judges([{"name": "Dr. Jane Smith", "role": "Head Control Judge"}])
        [{'name': 'Dr. Jane Smith', 'role': 'Head Control Judge'}]
    """
    validated_judges = []

    for judge_data in judges_data:
        try:
            # Validate using ControlJudge schema
            if isinstance(judge_data, dict) and 'name' in judge_data:
                # Ensure role field exists
                if 'role' not in judge_data:
                    judge_data['role'] = 'Control Judge'  # Default role

                judge = ControlJudge(**judge_data)
                validated_judges.append(judge.model_dump())
        except (ValueError, ValidationError, TypeError) as e:
            logger.warning(f"Control judge validation failed: {e}")

    return validated_judges
