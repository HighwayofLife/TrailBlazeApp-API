"""
OpenAPI schema definitions for the events API.
These schemas document the structure of API requests and responses.

Event objects include the following fields related to multi-day events:
- is_multi_day_event: Boolean flag indicating if an event spans multiple days
- is_pioneer_ride: Boolean flag indicating if an event is a pioneer ride (3+ days)
- ride_days: Integer count of how many days the event spans
"""

# Get all events - 200 success response
list_events_200 = {
    "description": "Successfully retrieved events",
    "content": {
        "application/json": {
            "schema": {
                "type": "array",
                "items": {"$ref": "#/components/schemas/EventResponse"},
            }
        }
    }
}

# Create event - 201 created response
create_event_201 = {
    "description": "Event created successfully",
    "content": {
        "application/json": {
            "schema": {"$ref": "#/components/schemas/EventResponse"}
        }
    }
}

# Get single event - 200 success response
get_event_200 = {
    "description": "Successfully retrieved event details",
    "content": {
        "application/json": {
            "schema": {"$ref": "#/components/schemas/EventResponse"}
        }
    }
}

# Event not found - 404 response
event_not_found_404 = {
    "description": "Event not found",
    "content": {
        "application/json": {
            "schema": {
                "type": "object",
                "properties": {
                    "detail": {"type": "string", "example": "Event not found"}
                }
            }
        }
    }
}

# Update event - 200 success response
update_event_200 = {
    "description": "Event updated successfully",
    "content": {
        "application/json": {
            "schema": {"$ref": "#/components/schemas/EventResponse"}
        }
    }
}

# Delete event - 204 no content response
delete_event_204 = {
    "description": "Event deleted successfully"
}
