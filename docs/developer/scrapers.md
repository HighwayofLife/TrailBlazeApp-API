# Scraper Development Guide

## Event Data Structure

When developing scrapers for different event sources, follow these guidelines to maintain consistency while accommodating different event types.

### Core Fields
Always populate these fields for all event types:
- name
- start_date
- end_date
- location_name
- organization (source organization)
- event_type (specific type of event)
- source (identifier for your scraper)

### Event-Specific Data
Store event-type-specific structured data in the `event_details` JSONB field:

```python
event_details = {
    # Semi-structured data specific to this event type
    "judges": [...],
    "trailConditions": "...",
    "specialRules": "...",
    # Any other fields specific to this event type
}
```

### Unstructured Information
Place any remaining unstructured information in the `notes` field.

## Example: Converting Source Data to Event Model

```python
def convert_to_db_events(source_events):
    db_events = []
    
    for event in source_events:
        # Extract core fields
        
        # Create event_details dictionary for semi-structured data
        event_details = {
            "key1": event.get("sourceField1"),
            "key2": event.get("sourceField2"),
            # etc.
        }
        
        # Create notes from any remaining useful information
        notes = "\n".join([
            f"Additional info: {event.get('additionalInfo')}",
            f"Other details: {event.get('otherDetails')}"
        ])
        
        db_event = Event(
            name=event.get("name"),
            # ...other core fields...
            event_type="Your Event Type",
            event_details=event_details,
            notes=notes,
            source="your_scraper_id"
        )
        
        db_events.append(db_event)
        
    return db_events
```

# ...existing documentation...
