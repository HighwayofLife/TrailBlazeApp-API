# Database Schema

The database schema is defined using Pydantic models and managed by SQLAlchemy.

## Event Table

The `events` table stores information about each endurance riding event.

| Column Name          | Data Type      | Description                                                                                                                                                                                                                            |
| -------------------- | -------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `id`                 | Integer        | Primary key, auto-incrementing.                                                                                                                                                                                                        |
| `name`               | String         | The name of the event.                                                                                                                                                                                                                 |
| `date_start`         | Date           | The start date of the event.                                                                                                                                                                                                            |
| `date_end`           | Date           | The end date of the event (can be the same as `date_start` for single-day events).                                                                                                                                                     |
| `location`           | String         | A textual representation of the event location (e.g., "City, State").                                                                                                                                                                    |
| `region`             | String         | The region the event belongs to (e.g., "SW", "NE").                                                                                                                                                                                     |
| `description`        | Text           | A description of the event.                                                                                                                                                                                                            |
| `website`            | String         | The URL of the event's website (if available).                                                                                                                                                                                          |
| `flyer_url`          | String         | The URL of the event's flyer (if available).                                                                                                                                                                                             |
| `distances`          | String[]       | An array of distance strings offered at the event (e.g., ["25 miles", "50 miles"]). Detailed distance data is stored in `event_details.distances`.                                                                                         |
| `ride_manager`       | String         | The name of the ride manager.                                                                                                                                                                                                          |
| `manager_email`      | String         | The email address of the ride manager.                                                                                                                                                                                                 |
| `manager_phone`      | String         | The phone number of the ride manager.                                                                                                                                                                                                  |
| `external_id`        | String         | An ID used to link the event to an external system (if applicable).                                                                                                                                                                     |
| `ride_id`            | String         | The original ID of the event from the source system (e.g., AERC tag ID).                                                                                                                                                                |
| `has_intro_ride`     | Boolean        | Indicates whether the event has an introductory ride option.                                                                                                                                                                            |
| `is_canceled`        | Boolean        | Indicates whether the event has been canceled.                                                                                                                                                                                          |
| `event_details`      | JSON           | A JSON object containing additional structured event details (see below).                                                                                                                                                               |
| `latitude`           | Float          | The latitude of the event location (if geocoding is successful).                                                                                                                                                                        |
| `longitude`          | Float          | The longitude of the event location (if geocoding is successful).                                                                                                                                                                       |
| `geocoding_attempted` | Boolean       | Indicates whether geocoding has been attempted for this event. `True` means an attempt was made (regardless of success). `False` means no attempt has been made.                                                                       |
| `source`             | String         | Identifies the data source (e.g., "AERC", "SERA").                                                                                                                                                                                      |
| `event_type`         | String         | The type of event (e.g., "endurance", "competitive_trail").                                                                                                                                                                             |

## Event Details JSON Structure

The `event_details` column stores structured data that may vary by event source. Common fields include:

```json
{
  "location_details": {
    "city": "City name",
    "state": "State code",
    "country": "Country"
  },
  "coordinates": {
    "latitude": 37.123,
    "longitude": -122.456
  },
  "map_link": "https://maps.google.com/...",
  "control_judges": [
    {"name": "Judge Name", "role": "Control Judge"}
  ],
  "distances": [
    {"distance": "50 miles", "date": "Mar 28, 2025", "start_time": "07:00 am"},
    {"distance": "25 miles", "date": "Mar 28, 2025", "start_time": "08:00 am"}
  ],
  "description": "Detailed event description",
  "directions": "Directions to the event"
}
```

Note that redundant fields like `coordinates` may exist both in the top-level columns and in the `event_details` JSON to support different query patterns. 