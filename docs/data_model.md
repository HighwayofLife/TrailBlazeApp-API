# Data Model

## Event

The Event model is designed to be flexible to support various types of endurance riding events from different organizations.

### Core Fields
These fields are standardized across all event types.

- **Basic Information**: id, name, description, etc.
- **Dates**: start_date, end_date
- **Location**: location_name, address, city, state, country, latitude, longitude
- **Organization**: organization (AERC, PNER, EDRA, etc.)

### Flexible Fields
These fields allow for variations between different event types:

- **event_type**: Identifies the kind of event (e.g., "AERC Endurance", "CTR", "Ride & Tie")
- **event_details**: A JSONB field that stores semi-structured data specific to each event type
- **notes**: Completely unstructured text information

### Event Details Structure
The `event_details` field should be structured according to the event type:

#### AERC Events
```json
{
  "controlJudges": [
    {
      "role": "Head Control Judge",
      "name": "Dr. Jane Smith"
    }
  ],
  "directions": "...",
  "mapLink": "https://...",
  "hasIntroRide": true
}
```

#### EDRA Events
```json
{
  "vets": [
    {
      "role": "Head Vet",
      "name": "Dr. John Doe"
    }
  ],
  "amenities": ["Water Available", "Horse Camping"],
  "trailDescription": "..."
}
```

# ...existing documentation...
