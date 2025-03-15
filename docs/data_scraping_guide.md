# Data Scraping Guide

## Summary

This document provides detailed information about the event data scraping system used in the TrailBlazeApp-API. It covers the design, implementation, scheduling, error handling, and maintenance of the scrapers that collect event data from various sources.

## Table of Contents

- [Scraping Architecture](#scraping-architecture)
- [Supported Data Sources](#supported-data-sources)
- [Scraper Implementation](#scraper-implementation)
- [Scheduling and Automation](#scheduling-and-automation)
- [Data Processing and Storage](#data-processing-and-storage)
- [Error Handling and Monitoring](#error-handling-and-monitoring)
- [Adding New Scrapers](#adding-new-scrapers)
- [Maintenance and Updates](#maintenance-and-updates)

## Scraping Architecture

The data scraping system is designed as a separate service that runs independently of the main API. This separation allows for better scalability, fault isolation, and maintenance.

### Key Components

1. **Scraper Manager**: Coordinates the execution of individual scrapers and handles scheduling
2. **Individual Scrapers**: Each responsible for extracting data from a specific source
3. **Data Processor**: Normalizes and validates scraped data
4. **Storage Interface**: Handles storing processed data in the database

### System Flow

```
[Source Websites] → [Scrapers] → [Data Processor] → [Database] → [API]
```

## Supported Data Sources

The system currently scrapes the following data sources:

1. **PNER Website**
   - URL: https://www.pner.net/
   - Data: Event listings, dates, locations
   - Update frequency: Weekly

2. **AERC Ride Calendar**
   - URL: https://aerc.org/ride_calendar
   - Data: National ride listings, AERC sanctioned events
   - Update frequency: Weekly

3. **Ride Managers' Websites**
   - Various URLs based on event listings
   - Data: Detailed event information, flyer PDFs
   - Update frequency: Daily (for upcoming events)

4. **Facebook Pages**
   - Pages maintained by ride organizers
   - Data: Announcements, updates, photos
   - Update frequency: Daily (for upcoming events)

## Scraper Implementation

The scraping system is implemented using Python with the following libraries:

- **Beautiful Soup**: For HTML parsing
- **Scrapy**: For structured web scraping
- **Requests**: For simple HTTP requests
- **PyPDF2**: For extracting text from PDF flyers

### Base Scraper Class

All scrapers inherit from a common base class that provides shared functionality:

```python
# Base scraper class
class BaseScraper:
    def __init__(self, source_name: str, logger=None):
        self.source_name = source_name
        self.logger = logger or logging.getLogger(__name__)
        
    async def scrape(self) -> List[dict]:
        """
        Execute the scraping operation and return event data.
        Should be implemented by subclasses.
        """
        raise NotImplementedError
        
    async def process_results(self, raw_data: List[dict]) -> List[dict]:
        """
        Process the scraped data into a standard format.
        """
        processed_data = []
        for item in raw_data:
            try:
                processed_item = self.normalize_data(item)
                if self.validate_data(processed_item):
                    processed_data.append(processed_item)
            except Exception as e:
                self.logger.error(f"Error processing item: {e}")
                continue
        return processed_data
        
    def normalize_data(self, item: dict) -> dict:
        """
        Convert source-specific data into the standard format.
        """
        # Basic implementation - subclasses should enhance this
        return {
            "name": item.get("title", "Unknown Event"),
            "description": item.get("description", ""),
            "location": item.get("location", ""),
            "date_start": self.parse_date(item.get("start_date")),
            "date_end": self.parse_date(item.get("end_date")),
            "organizer": item.get("organizer", ""),
            "website": item.get("url", ""),
            "flyer_url": item.get("flyer_url", ""),
            "region": self.determine_region(item.get("location", "")),
            "distances": self.parse_distances(item.get("distances", [])),
            "source": self.source_name
        }
        
    def validate_data(self, item: dict) -> bool:
        """
        Validate that the item has all required fields.
        """
        required_fields = ["name", "location", "date_start"]
        return all(item.get(field) for field in required_fields)
        
    def parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """
        Parse date string into standard format.
        """
        # Implementation depends on source format
        pass
        
    def parse_distances(self, distances_data) -> List[str]:
        """
        Extract ride distances into a standard list.
        """
        # Implementation depends on source format
        pass
        
    def determine_region(self, location: str) -> str:
        """
        Determine the region based on location.
        """
        # Simple implementation - could be enhanced with geo lookup
        if not location:
            return "Unknown"
            
        northwest = ["washington", "oregon", "idaho", "montana", "bc", "british columbia"]
        for term in northwest:
            if term.lower() in location.lower():
                return "Pacific Northwest"
                
        # Additional regions could be added here
        return "Other"
```

### Example Scraper Implementation

Here's an example of a specific scraper for the PNER website:

```python
class PNERScraper(BaseScraper):
    def __init__(self, logger=None):
        super().__init__("PNER Website", logger)
        self.base_url = "https://www.pner.net/"
        self.calendar_url = f"{self.base_url}/calendar"
        
    async def scrape(self) -> List[dict]:
        self.logger.info(f"Scraping events from {self.calendar_url}")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.calendar_url)
                response.raise_for_status()
                
            soup = BeautifulSoup(response.text, "html.parser")
            events = []
            
            # Find event listings (simplified example)
            event_elements = soup.select(".event-listing")
            
            for element in event_elements:
                event = {}
                event["title"] = element.select_one(".event-title").text.strip()
                event["description"] = element.select_one(".event-description").text.strip()
                event["location"] = element.select_one(".event-location").text.strip()
                
                date_element = element.select_one(".event-date")
                event["start_date"] = date_element.get("data-start-date")
                event["end_date"] = date_element.get("data-end-date")
                
                event["organizer"] = element.select_one(".event-organizer").text.strip()
                event["url"] = element.select_one(".event-link")["href"]
                
                flyer_link = element.select_one(".event-flyer")
                event["flyer_url"] = flyer_link["href"] if flyer_link else None
                
                distances_text = element.select_one(".event-distances").text.strip()
                event["distances"] = distances_text.split(",")
                
                events.append(event)
                
            self.logger.info(f"Successfully scraped {len(events)} events from PNER")
            return events
            
        except Exception as e:
            self.logger.error(f"Error scraping PNER website: {e}")
            return []
            
    def parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        if not date_str:
            return None
            
        try:
            # Example format: "2023-09-15"
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            self.logger.warning(f"Could not parse date: {date_str}")
            return None
            
    def parse_distances(self, distances_data: List[str]) -> List[str]:
        result = []
        for distance in distances_data:
            # Clean and normalize
            clean = distance.strip().lower()
            
            # Extract numbers
            match = re.search(r'(\d+)', clean)
            if match:
                result.append(match.group(1))
                
        return result
```

## Scheduling and Automation

The scrapers are run on a schedule using a combination of cron jobs and the application scheduler:

### Schedule Configuration

The default schedule is defined in the application settings and can be overridden with environment variables:

```python
# Default schedule settings
SCRAPER_SETTINGS = {
    "pner_website": {
        "enabled": True,
        "schedule": "0 0 * * 0"  # Weekly on Sunday at midnight
    },
    "aerc_calendar": {
        "enabled": True,
        "schedule": "0 0 * * 1"  # Weekly on Monday at midnight
    },
    "ride_managers": {
        "enabled": True,
        "schedule": "0 12 * * *"  # Daily at noon
    },
    "facebook_pages": {
        "enabled": True,
        "schedule": "0 8,20 * * *"  # Twice daily at 8am and 8pm
    }
}
```

### Running the Scrapers

#### Manual Execution

Scrapers can be run manually using the CLI:

```bash
# Run all scrapers
python -m scrapers.run_scrapers

# Run a specific scraper
python -m scrapers.run_scrapers --source pner_website
```

#### Automated Execution

For production, the scrapers are run as scheduled tasks:

1. **Docker setup:**
   - Use a separate container for running scrapers
   - Mount a volume for sharing data with the API container

2. **Kubernetes setup:**
   - Use CronJob resources to schedule scraper execution
   - Set resource limits appropriate for scraping operations

## Data Processing and Storage

### Data Normalization

All scraped data goes through a normalization process to ensure consistency:

1. **Name standardization**: Consistent formatting of event names
2. **Date parsing**: Convert various date formats to ISO 8601
3. **Location processing**: Extract structured location data
4. **Region classification**: Assign events to appropriate regions
5. **Distance formatting**: Standardize distance representations

### Storage Process

Once normalized, data is stored in the database:

1. **Check for duplicates**: Compare with existing events to avoid duplication
2. **Update existing events**: If an event already exists, update with new information
3. **Add new events**: Insert completely new events
4. **Mark stale events**: Flag events that are no longer found in sources

```python
async def store_events(events: List[dict], db_session):
    """Store scraped events in the database."""
    for event_data in events:
        # Check for existing event
        existing_event = await crud.events.get_event_by_external_id(
            db_session, 
            event_data.get("external_id")
        )
        
        if existing_event:
            # Update existing event with new data
            event_update = EventUpdate(**event_data)
            await crud.events.update_event(
                db_session,
                event_id=existing_event.id,
                event_update=event_update
            )
            logger.info(f"Updated event: {event_data['name']}")
        else:
            # Create new event
            event_create = EventCreate(**event_data)
            await crud.events.create_event(db_session, event_create)
            logger.info(f"Created new event: {event_data['name']}")
```

## Error Handling and Monitoring

### Error Types

The scraping system handles various types of errors:

1. **Network errors**: Failed connections to source websites
2. **Parsing errors**: Issues extracting data from HTML/PDF
3. **Validation errors**: Scraped data failing validation rules
4. **Storage errors**: Database issues when storing data

### Logging and Alerts

The system generates detailed logs for monitoring and debugging:

```python
# Setup logging
logging.config.dictConfig({
    'version': 1,
    'formatters': {
        'default': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'default',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/scraper.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'formatter': 'default',
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console', 'file'],
    }
})
```

For critical errors, the system can send alerts via email or other notification channels.

## Adding New Scrapers

To add a new data source:

1. **Create a new scraper class** that inherits from BaseScraper
2. **Implement the scrape() method** to extract data from the source
3. **Override normalization methods** if source data requires special handling
4. **Register the scraper** in the scraper manager
5. **Configure the schedule** for the new scraper
6. **Test thoroughly** with sample data from the new source

### Example: Adding a New Scraper

```python
# 1. Create the scraper class
class NewOrganizationScraper(BaseScraper):
    def __init__(self, logger=None):
        super().__init__("New Organization", logger)
        self.base_url = "https://example.org/events"
        
    async def scrape(self) -> List[dict]:
        # Implementation for scraping the new source
        pass
        
    # Override other methods as needed

# 2. Register the scraper in the manager
SCRAPERS = {
    "pner_website": PNERScraper,
    "aerc_calendar": AERCScraper,
    "ride_managers": RideManagersScraper,
    "facebook_pages": FacebookPagesScraper,
    "new_organization": NewOrganizationScraper  # Add the new scraper
}

# 3. Configure the schedule
SCRAPER_SETTINGS.update({
    "new_organization": {
        "enabled": True,
        "schedule": "0 1 * * *"  # Daily at 1am
    }
})
```

## Maintenance and Updates

### Handling Website Changes

When source websites change their structure:

1. **Detect the change** through monitoring and logging
2. **Update the scraper code** to match the new structure
3. **Test with the new structure** to ensure data is extracted correctly
4. **Deploy the updated scraper**

### Performance Optimization

For better performance and reliability:

1. **Use asynchronous requests** to speed up scraping multiple sources
2. **Implement polite scraping** with delays between requests
3. **Set appropriate timeouts** to handle unresponsive sources
4. **Use caching** to reduce load on source websites
5. **Implement retries** for transient errors

### Backup Data Sources

To ensure continuity if primary sources are unavailable:

1. **Identify alternative sources** for each data type
2. **Implement fallback scrapers** that activate when primary scrapers fail
3. **Maintain an archive** of previously scraped data
4. **Create a manual data entry interface** for critical information
