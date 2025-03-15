// ...existing code...
  }
}
```

**Response:**

```json
{
  "data": {
    "question": "What gear do I need for a 50-mile endurance ride?",
    "answer": "For a 50-mile endurance ride, you'll need essential gear including:\n\n1. Proper riding attire: Comfortable riding clothes, helmet, and appropriate footwear\n2. Hydration system: Water bottles or hydration pack\n3. First aid kit: For both you and your horse\n4. GPS or map: To follow the trail\n5. Snacks and electrolytes: To maintain energy throughout the ride\n6. Hoof protection: Shoes or boots appropriate for the terrain\n7. Weather protection: Depending on the forecast (sun protection, rain gear)\n8. Emergency items: Whistle, flashlight, emergency blanket\n9. Basic tool kit: For tack adjustments or repairs\n\nFor the Grizzly Mountain Endurance Ride specifically, the rocky terrain makes hoof protection mandatory, and the weather can change quickly in the mountains, so layered clothing is recommended."
  }
}
```

**Example Request:**

```bash
curl -X POST "https://api.trailblazeapp.com/v1/assistant/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What gear do I need for a 50-mile endurance ride?",
    "context": {
      "event_id": "123e4567-e89b-12d3-a456-426614174000"
    }
  }'
```

## Weather API

### Get Weather for Event

Retrieves weather forecast for a specific event.

**Endpoint:** `GET /v1/events/{event_id}/weather`

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| event_id | string (UUID) | ID of the event |

**Response:**

```json
{
  "data": {
    "event_id": "123e4567-e89b-12d3-a456-426614174000",
    "forecast": [
      {
        "date": "2023-09-15",
        "weather": "Partly Cloudy",
        "temp_high_f": 78,
        "temp_low_f": 52,
        "temp_high_c": 26,
        "temp_low_c": 11,
        "precipitation_chance": 20,
        "wind_speed_mph": 8,
        "wind_direction": "NW",
        "humidity": 45,
        "icon": "partly-cloudy-day"
      },
      {
        "date": "2023-09-16",
        "weather": "Sunny",
        "temp_high_f": 82,
        "temp_low_f": 54,
        "temp_high_c": 28,
        "temp_low_c": 12,
        "precipitation_chance": 10,
        "wind_speed_mph": 5,
        "wind_direction": "W",
        "humidity": 40,
        "icon": "clear-day"
      }
    ],
    "source": "OpenWeatherMap",
    "last_updated": "2023-09-14T14:30:00Z"
  }
}
```

**Example Request:**

```bash
curl -X GET "https://api.trailblazeapp.com/v1/events/123e4567-e89b-12d3-a456-426614174000/weather"
```

## Error Handling

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

### Common Error Codes

| Status Code | Error Code | Description |
|-------------|------------|-------------|
| 400 | INVALID_REQUEST | The request was malformed or contained invalid parameters |
| 400 | VALIDATION_ERROR | The request data failed validation |
| 404 | EVENT_NOT_FOUND | The specified event could not be found |
| 500 | INTERNAL_ERROR | An unexpected error occurred on the server |
| 500 | EXTERNAL_SERVICE_ERROR | An error occurred when calling an external service |

## Pagination

All collection endpoints support pagination using the following query parameters:

| Parameter | Description | Default | Maximum |
|-----------|-------------|---------|---------|
| page | Page number (1-based) | 1 | - |
| per_page | Number of items per page | 20 | 100 |

Pagination metadata is included in the response:

```json
{
  "items": [ ... ],
  "metadata": {
    "page": 1,
    "per_page": 20,
    "total": 42,
    "pages": 3
  }
}
```

## Rate Limiting

The API currently does not implement rate limiting, but excessive usage may be restricted in the future to ensure fair service to all users.

When implemented, rate limit information will be included in the response headers:

```
X-Rate-Limit-Limit: 100
X-Rate-Limit-Remaining: 95
X-Rate-Limit-Reset: 1632221382
```
