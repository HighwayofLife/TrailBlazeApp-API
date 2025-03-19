"""
AERC Event Data Handler.

This module serves as the main entry point for AERC event data processing.
It coordinates the validation, transformation, and storage of AERC event data
by delegating to specialized modules for each responsibility.

The data handler implements the following workflow:
1. Validate raw event data from the AERC parser
2. Transform the data into structured Pydantic models
3. Convert the data to the appropriate format for database storage
4. Store the data in the database, handling duplicates appropriately

This module adheres to the schema definitions in app/schemas/event.py,
which serves as the single source of truth for event data structures.
"""

import logging
from typing import Dict, Any, Optional, List

from app.schemas import AERCEvent, EventCreate

# Import from specialized modules
from .data_validators import validate_event, validate_url
from .data_transformers import (
    transform_to_aerc_event,
    aerc_event_to_event_create,
    extract_and_format_event_details,
    prepare_event_data
)
from .data_storage import EventStorageHandler

logger = logging.getLogger(__name__)


class DataHandler:
    """
    Handles the validation, transformation, and storage of AERC event data.

    This class serves as the main entry point for processing AERC event data.
    It coordinates between validators, transformers, and storage handlers
    to provide a simplified API for the AERC scraper.

    Attributes:
        storage_handler: Handler for database storage operations
        metrics: Dictionary tracking validation and storage metrics
    """

    def __init__(self, connection=None):
        """
        Initialize the DataHandler.

        Args:
            connection: Optional database connection for storage operations
        """
        self.storage_handler = EventStorageHandler(connection) if connection else None
        self.metrics = {
            "validation_errors": 0,
            "transformation_errors": 0,
            "storage_errors": 0,
            "inserted_events": 0,
            "updated_events": 0
        }

    @staticmethod
    def extract_event_details(raw_event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and format additional event details from raw event data.

        Args:
            raw_event: Raw event data

        Returns:
            Dictionary of additional event details

        Example:
            >>> DataHandler.extract_event_details({"coordinates": {"latitude": 31.6784, "longitude": -110.6255}})
            {'coordinates': {'latitude': 31.6784, 'longitude': -110.6255}}
        """
        return extract_and_format_event_details(raw_event)

    @classmethod
    def transform_and_validate(cls, raw_event: Dict[str, Any]) -> Optional[AERCEvent]:
        """
        Transform raw event data into AERCEvent object and validate it.

        Args:
            raw_event: Raw event data from parser

        Returns:
            Validated AERCEvent object or None if validation fails

        Example:
            >>> raw_data = {"name": "Test Event", "date_start": "2023-01-01", "location": "Test Location"}
            >>> event = DataHandler.transform_and_validate(raw_data)
        """
        try:
            # Transform the raw event data into an AERCEvent object
            aerc_event = transform_to_aerc_event(raw_event)
            return aerc_event
        except ValueError as e:
            logger.warning(f"Event validation failed: {str(e)}")
            return None

    @staticmethod
    def to_event_create(aerc_event: AERCEvent) -> Optional[EventCreate]:
        """
        Convert AERCEvent to EventCreate model for database insertion.

        Args:
            aerc_event: Validated AERCEvent object

        Returns:
            EventCreate object or None if conversion fails

        Example:
            >>> from app.schemas import AERCEvent
            >>> from datetime import datetime
            >>> aerc_event = AERCEvent(name="Test Event", date_start=datetime.now(), location="Test Location")
            >>> event_create = DataHandler.to_event_create(aerc_event)
        """
        try:
            return aerc_event_to_event_create(aerc_event)
        except ValueError as e:
            logger.warning(f"Failed to convert to EventCreate: {str(e)}")
            return None

    def process_event(self, raw_event: Dict[str, Any]) -> Optional[int]:
        """
        Process a single event through the entire validation, transformation, and storage workflow.

        Args:
            raw_event: Raw event data from parser

        Returns:
            Event ID if successfully stored, None otherwise

        Example:
            >>> handler = DataHandler(db_connection)
            >>> event_id = handler.process_event({"name": "Test Event", "date_start": "2023-01-01"})
        """
        try:
            # Validate and transform to AERCEvent
            aerc_event = self.transform_and_validate(raw_event)
            if not aerc_event:
                self.metrics["validation_errors"] += 1
                return None

            # Convert to EventCreate for database insertion
            event_create = self.to_event_create(aerc_event)
            if not event_create:
                self.metrics["transformation_errors"] += 1
                return None

            # Store in database if connection available
            if self.storage_handler:
                event_id = self.storage_handler.store_event(event_create.model_dump())
                if event_id:
                    # Update metrics from storage handler
                    self.metrics["inserted_events"] = self.storage_handler.metrics["inserted_events"]
                    self.metrics["updated_events"] = self.storage_handler.metrics["updated_events"]
                    self.metrics["storage_errors"] = self.storage_handler.metrics["storage_errors"]
                return event_id
            else:
                logger.info("No database connection, skipping storage")
                return None

        except (ValueError, TypeError) as e:
            logger.error(f"Error processing event: {str(e)}")
            return None

    def process_events(self, raw_events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process multiple events and return statistics.

        Args:
            raw_events: List of raw event data dictionaries

        Returns:
            Dictionary with processing statistics

        Example:
            >>> handler = DataHandler(db_connection)
            >>> stats = handler.process_events([{"name": "Event 1"}, {"name": "Event 2"}])
            >>> print(stats)
            {'processed': 2, 'successful': 1, 'failed': 1, ...}
        """
        stats = {
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "metrics": self.metrics.copy()
        }

        for raw_event in raw_events:
            stats["processed"] += 1
            event_id = self.process_event(raw_event)

            if event_id:
                stats["successful"] += 1
            else:
                stats["failed"] += 1

        # Update final metrics in stats
        stats["metrics"] = self.metrics.copy()

        return stats

    def validate_url(self, url: str) -> Optional[str]:
        """
        Validate a URL string.

        Args:
            url: URL string to validate

        Returns:
            Validated URL string or None if invalid

        Example:
            >>> handler = DataHandler()
            >>> validated_url = handler.validate_url("example.com")
            >>> print(validated_url)
            https://example.com
        """
        validated_url = validate_url(url)
        return str(validated_url) if validated_url else None
