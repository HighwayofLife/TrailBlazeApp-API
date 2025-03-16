# Events API Documentation

## Event Object

An event object includes the following fields:

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Unique identifier for the event |
| name | String | Name of the event |
| description | String | Description of the event |
| location | String | Location of the event |
| date_start | Date | Start date of the event |
| date_end | Date | End date of the event |
| organizer | String | Organization hosting the event |
| website | String | Website URL for the event |
| flyer_url | String | URL to the event flyer |
| region | String | Geographic region of the event |
| distances | Array[String] | Available ride distances |
| source | String | Source of the event data |
| ride_manager | String | Name of the ride manager |
| manager_email | String | Email of the ride manager |
| manager_phone | String | Phone number of the ride manager |
| judges | Array[String] | List of judges for the event |
| directions | String | Directions to the event location |
| map_link | String | Link to a map for directions |
| external_id | String | External identifier from the source system |
