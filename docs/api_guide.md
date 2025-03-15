// ...existing code...

#### Create Event

```
POST /events
```

Creates a new event.

**Request Body:**

```json
{
  "name": "New Mountain Ride",
  "description": "A beautiful ride through mountain trails",
  "location": "Mountain View, OR",
  "date_start": "2024-07-15T08:00:00",
  "date_end": "2024-07-16T18:00:00",
  "organizer": "Mountain Trail Riders",
  "website": "http://mountaintrailriders.org",
  "flyer_url": "http://mountaintrailriders.org/flyer2024.pdf",
  "region": "Pacific Northwest",
  "distances": ["25", "50"]
}
```

**Example Response:**

```json
{
  "id": 42,
  "name": "New Mountain Ride",
  "description": "A beautiful ride through mountain trails",
  "location": "Mountain View, OR",
  "date_start": "2024-07-15T08:00:00",
  "date_end": "2024-07-16T18:00:00",
  "organizer": "Mountain Trail Riders",
  "website": "http://mountaintrailriders.org",
  "flyer_url": "http://mountaintrailriders.org/flyer2024.pdf",
  "region": "Pacific Northwest",
  "distances": ["25", "50"],
  "created_at": "2023-12-01T10:30:00",
  "updated_at": null
}
```

#### Update Event

```
PUT /events/{event_id}
```

Updates an existing event. You only need to include the fields you want to update.

**Request Body:**

```json
{
  "description": "Updated description with new information",
  "website": "http://newwebsite.org"
}
```

**Example Response:**

```json
{
  "id": 42,
  "name": "New Mountain Ride",
  "description": "Updated description with new information",
  "location": "Mountain View, OR",
  "date_start": "2024-07-15T08:00:00",
  "date_end": "2024-07-16T18:00:00",
  "organizer": "Mountain Trail Riders",
  "website": "http://newwebsite.org",
  "flyer_url": "http://mountaintrailriders.org/flyer2024.pdf",
  "region": "Pacific Northwest",
  "distances": ["25", "50"],
  "created_at": "2023-12-01T10:30:00",
  "updated_at": "2023-12-02T14:25:00"
}
```

#### Delete Event

```
DELETE /events/{event_id}
```

Deletes an event. Returns 204 No Content on success.

### AI Assistant

#### Ask a Question

```
POST /ai/ask
```

Ask the AI assistant a question about endurance riding or a specific event.

**Request Body:**

```json
{
  "question": "What should I pack for an endurance ride?",
  "event_id": 42  // Optional: if you want context about a specific event
}
```

**Example Response:**

```json
{
  "answer": "For an endurance ride, you should pack: riding gear (helmet, comfortable clothing, appropriate footwear), equipment for your horse (saddle, bridle, girth, saddle pads, hoof protection, etc.), water and feed for your horse, electrolytes, first aid supplies for both you and your horse, a headlamp if you'll be riding in darkness, weather-appropriate clothing, and personal items like sunscreen and insect repellent. For the New Mountain Ride specifically, you'll want to bring extra water as the trail has limited water sources and hoof protection is recommended due to the rocky terrain.",
  "success": true
}
```

### Scrapers

#### List Scrapers

```
GET /scrapers
```

Lists all available scrapers.

**Example Response:**

```json
[
  {
    "id": "pner",
    "name": "PNER Website",
    "status": "active"
  },
  {
    "id": "aerc",
    "name": "AERC Calendar",
    "status": "active"
  },
  {
    "id": "facebook",
    "name": "Facebook Events",
    "status": "active"
  }
]
```

#### Run Scraper

```
POST /scrapers/run?scraper_id=pner
```

Triggers a specific scraper to run.

**Example Response:**

```json
{
  "scraper_id": "pner",
  "status": "running",
  "message": "Scraper 'pner' started successfully"
}
```

## Error Responses

The API uses standard HTTP status codes:

- `200 OK`: The request was successful
- `201 Created`: A new resource was created
- `204 No Content`: The request was successful but there is no content to return
- `400 Bad Request`: The request was invalid
- `404 Not Found`: The requested resource was not found
- `500 Internal Server Error`: Something went wrong on the server

Error responses include a JSON body with details:

```json
{
  "detail": "Error message explaining what went wrong"
}
```

## Rate Limiting

The API currently does not implement rate limiting, but excessive usage may be restricted in the future to ensure fair service to all users.
