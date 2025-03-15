"""
Schema definitions for the AERC scraper.
"""

# Schema for Gemini-based structured data extraction
AERC_EVENT_SCHEMA = """
{
  "type": "array",
  "items": {
    "type": "object",
    "properties": {
      "rideName": {
        "type": "string",
        "description": "Name of the endurance ride"
      },
      "region": {
        "type": "string",
        "description": "Geographic region of the ride (e.g., NW)"
      },
      "date": {
        "type": "string",
        "format": "date",
        "description": "Date of the ride (YYYY-MM-DD)"
      },
      "distances": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "distance": {
              "type": "string",  
              "description": "Distance of the ride (e.g., '25', '50', '75', '100')"
            },
            "date": {
              "type": "string",
              "format": "date",
              "description": "Date that distance is offered (YYYY-MM-DD)."
            },
            "startTime": {
              "type": "string",
              "format": "time",
              "description": "Start time for the ride distance (HH:MM am/pm)"
            }
          }
        }
      },
      "hasIntroRide": {
        "type": "boolean",
        "description": "Indicates if an introductory ride is offered"
      },
      "location": {
        "type": "string",
        "description": "Location of the ride"
      },
      "website": {
        "type": "string",
        "format": "url",
        "description": "URL of the ride's website (if available)"
      },
      "rideManager": {
        "type": "string",
        "description": "Name of the ride manager"
      },
      "rideManagerContact": {
        "type": "object",
        "properties": {
          "name":  { "type": "string" },
          "phone": { "type": "string" },
          "email": {
            "type": "string",
            "format": "email"
          }
        }
      },
      "controlJudges": {
        "type": "array",
        "items": {
            "type": "object",
            "properties" : {
                "role" : { "type": "string"},
                "name" : { "type" : "string"}
            }
        }
      },
      "directions": {
        "type": "string",
        "description": "Detailed directions to the ride location (if available)"
      },
      "mapLink": {
        "type": "string",
        "format": "url",
        "description": "Link to a map for directions (optional)."
      },
      "description": {
        "type" : "string",
        "description" : "Additional descriptive text/notes"
      },
      "tag": {
        "type": "integer",
        "description": "Unique identifier (tag) for the ride."
      }
    }
  }
}
"""
