# Events API

## Event Object

An event object includes the following fields:

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Unique identifier for the event |
| name | String | Name of the event |
| description | Text | Description of the event |
| start_date | DateTime | Start date and time of the event |
| end_date | DateTime | End date and time of the event |
| location_name | String | Name of the event location |
| address | String | Street address of the event |
| city | String | City where the event is located |
| state | String | State where the event is located |
| country | String | Country where the event is located (default: "USA") |
| latitude | Float | Geographic latitude of the event location |
| longitude | Float | Geographic longitude of the event location |
| organization | String | Organization hosting the event (e.g., AERC, PNER, EDRA) |
| distances | Array[String] | Available ride distances |
| requirements | JSON | Special requirements or rules for the event |
| flyer_url | String | URL to the event flyer |
| website_url | String | URL to the event website |
| contact_name | String | Primary contact name |
| contact_email | String | Primary contact email |
| contact_phone | String | Primary contact phone number |
| ride_manager | String | Name of the ride manager |
| manager_contact | String | Contact information for the ride manager |
| event_type | String | Type of event (e.g., "AERC Endurance", "EDRA", "CTR") |
| event_details | JSONB | Semi-structured data specific to the event type |
| notes | Text | Additional unstructured notes about the event |
| external_id | String | External identifier from the source system |
| created_at | DateTime | When the event record was created |
| updated_at | DateTime | When the event record was last updated |
| is_canceled | Boolean | Whether the event has been canceled |
| is_verified | Boolean | Whether the event details have been verified |
| source | String | Source of the event data (e.g., "aerc_scraper") |

## Using the `event_details` Field

The `event_details` field is a JSONB field that stores semi-structured data specific to each event type. This provides flexibility while maintaining the ability to query specific fields.

### Example for AERC Events

```json
{
  "controlJudges": [
    {
      "role": "Head Control Judge",
      "name": "Dr. Jane Smith"
    }
  ],
  "directions": "Take Highway 101 North to Exit 25, then follow signs",
  "mapLink": "https://maps.google.com/?q=...",
  "hasIntroRide": true
}
```

### Example for CTR Events

```json
{
  "judges": [
    {
      "role": "Senior Judge",
      "name": "Bob Johnson"
    }
  ],
  "scoringSystem": "NATRC",
  "classes": ["Novice", "Open", "CP"],
  "amenities": ["Water", "Camping", "Stalls"]
}
```

## Filtering Events

You can filter events by standard fields and also by data within the `event_details` JSONB field.

Example query for events with intro rides:

```
GET /api/events?event_details->hasIntroRide=true
```

# ...existing documentation...
