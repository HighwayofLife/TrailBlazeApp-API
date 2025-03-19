"""
AERC Event Data Storage Operations.

This module provides database storage operations for AERC event data.
It handles the creation, updating, and retrieval of events in the database.

This module works with the schema definitions from app/schemas/event.py and
follows the database structure defined in the main application models.
"""
# pylint: disable=import-error

from typing import Dict, Any, Optional, Union, List
from datetime import datetime
import json
import logging
import psycopg2  # type: ignore
from psycopg2.extras import RealDictCursor  # type: ignore

from app.schemas import AERCEvent

from .data_transformers import prepare_event_data

logger = logging.getLogger(__name__)


class EventStorageHandler:
    """
    Handles database operations for AERC events.

    This class is responsible for storing event data in the database,
    including checking for existing events to prevent duplicates.
    """

    def __init__(self, connection=None):
        """
        Initialize the EventStorageHandler.

        Args:
            connection: Database connection object
        """
        self.connection = connection
        self.metrics = {
            "validation_errors": 0,
            "storage_errors": 0,
            "inserted_events": 0,
            "updated_events": 0
        }

    def store_event(self, event_data: Dict[str, Any]) -> Optional[int]:
        """
        Validate event data and store in the database.

        Args:
            event_data: Dictionary containing event data to store

        Returns:
            Event ID if stored successfully, None if failed

        Example:
            >>> handler = EventStorageHandler(connection)
            >>> event_id = handler.store_event({"name": "Test Event", "date_start": "2023-01-01"})
        """
        event_id = None

        try:
            # Skip if no database connection
            if not self.connection:
                logger.warning("No database connection provided")
                return None

            # Prepare data for database
            prepared_data = prepare_event_data(event_data)

            # Check if event already exists by ride_id
            ride_id = prepared_data.get('ride_id')
            existing_id = None

            if ride_id:
                existing_id = self._get_event_by_ride_id(ride_id)

            # If not found by ride_id, try to find by name and date
            if not existing_id:
                name = prepared_data.get('name')
                date = prepared_data.get('date_start')
                if name and date:
                    existing_id = self._get_event_by_name_date(name, date)

            # Create or update the event
            if existing_id:
                event_id = self._update_event(existing_id, prepared_data)
                self.metrics['updated_events'] += 1
                logger.info(f"Updated event with ID: {event_id}")
            else:
                event_id = self._create_event(prepared_data)
                self.metrics['inserted_events'] += 1
                logger.info(f"Inserted new event with ID: {event_id}")

            return event_id

        except (psycopg2.Error, ValueError) as e:
            logger.error(f"Error storing event: {str(e)}")
            self.metrics['storage_errors'] += 1
            return None

    def _get_event_by_ride_id(self, ride_id: str) -> Optional[int]:
        """
        Get event ID by ride_id.

        Args:
            ride_id: The ride ID to search for

        Returns:
            Event ID if found, None otherwise
        """
        try:
            query = "SELECT id FROM events WHERE ride_id = %s LIMIT 1"

            with self.connection.cursor() as cursor:
                cursor.execute(query, (ride_id,))
                result = cursor.fetchone()

                return result[0] if result else None

        except psycopg2.Error as e:
            logger.error(f"Error getting event by ride_id: {str(e)}")
            return None

    def _get_event_by_name_date(self, name: str, date: Union[str, datetime]) -> Optional[int]:
        """
        Get event ID by name and date.

        Args:
            name: Event name
            date: Event date (string or datetime)

        Returns:
            Event ID if found, None otherwise
        """
        try:
            # Convert string date to datetime if needed
            if isinstance(date, str):
                try:
                    date = datetime.strptime(date, '%Y-%m-%d')
                except ValueError:
                    # Try another format
                    try:
                        date = datetime.fromisoformat(date.replace('Z', '+00:00'))
                    except ValueError:
                        logger.error(f"Unable to parse date: {date}")
                        return None

            # Format date for SQL query
            date_str = date.strftime('%Y-%m-%d')

            query = """
                SELECT id FROM events
                WHERE name = %s
                AND date_start::date = %s::date
                LIMIT 1
            """

            with self.connection.cursor() as cursor:
                cursor.execute(query, (name, date_str))
                result = cursor.fetchone()

                return result[0] if result else None

        except psycopg2.Error as e:
            logger.error(f"Error getting event by name and date: {str(e)}")
            return None

    def _create_event(self, event_data: Dict[str, Any]) -> Optional[int]:
        """
        Create a new event in the database.

        Args:
            event_data: Dictionary containing event data

        Returns:
            New event ID if successful, None otherwise
        """
        try:
            # Build column lists and parameter placeholders
            columns = []
            placeholders = []
            values = []

            # Process all fields
            for key, value in event_data.items():
                # Skip None values
                if value is None:
                    continue

                # Handle JSON fields
                if key in ['distances', 'ride_manager_contact', 'control_judges', 'location_details', 'event_details']:
                    columns.append(key)
                    placeholders.append("%s")
                    values.append(json.dumps(value))
                    continue

                # Handle all other fields
                columns.append(key)
                placeholders.append("%s")
                values.append(value)

            # Add timestamps
            columns.append('created_at')
            placeholders.append("NOW()")
            columns.append('updated_at')
            placeholders.append("NOW()")

            # Build the query
            query = f"""
                INSERT INTO events ({', '.join(columns)})
                VALUES ({', '.join(placeholders)})
                RETURNING id
            """

            # Execute the query
            with self.connection.cursor() as cursor:
                cursor.execute(query, values)
                result = cursor.fetchone()
                self.connection.commit()

                return result[0] if result else None

        except psycopg2.Error as e:
            logger.error(f"Error creating event: {str(e)}")
            self.connection.rollback()
            return None

    def _update_event(self, event_id: int, event_data: Dict[str, Any]) -> Optional[int]:
        """
        Update an existing event in the database.

        Args:
            event_id: ID of the event to update
            event_data: Dictionary containing event data

        Returns:
            Updated event ID if successful, None otherwise
        """
        try:
            # Build update parts
            update_parts = []
            values = []

            # Process all fields
            for key, value in event_data.items():
                # Skip None values
                if value is None:
                    continue

                # Handle JSON fields
                if key in ['distances', 'ride_manager_contact', 'control_judges', 'location_details', 'event_details']:
                    update_parts.append(f"{key} = %s")
                    values.append(json.dumps(value))
                    continue

                # Handle all other fields
                update_parts.append(f"{key} = %s")
                values.append(value)

            # Add timestamp for update
            update_parts.append("updated_at = NOW()")

            # Add event_id to values
            values.append(event_id)

            # Build the query
            query = f"""
                UPDATE events
                SET {', '.join(update_parts)}
                WHERE id = %s
                RETURNING id
            """

            # Execute the query
            with self.connection.cursor() as cursor:
                cursor.execute(query, values)
                result = cursor.fetchone()
                self.connection.commit()

                return result[0] if result else None

        except psycopg2.Error as e:
            logger.error(f"Error updating event: {str(e)}")
            self.connection.rollback()
            return None

    def get_events(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get a list of events from the database.

        Args:
            limit: Maximum number of events to return
            offset: Offset for pagination

        Returns:
            List of event dictionaries
        """
        try:
            query = """
                SELECT * FROM events
                ORDER BY date_start DESC
                LIMIT %s OFFSET %s
            """

            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, (limit, offset))
                results = cursor.fetchall()

                return list(results)

        except psycopg2.Error as e:
            logger.error(f"Error getting events: {str(e)}")
            return []

    def get_event_by_id(self, event_id: int) -> Optional[Dict[str, Any]]:
        """
        Get an event by ID.

        Args:
            event_id: ID of the event to get

        Returns:
            Event dictionary if found, None otherwise
        """
        try:
            query = "SELECT * FROM events WHERE id = %s"

            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, (event_id,))
                result = cursor.fetchone()

                return dict(result) if result else None

        except psycopg2.Error as e:
            logger.error(f"Error getting event by ID: {str(e)}")
            return None
