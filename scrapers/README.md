# TrailBlaze Data Scrapers

This directory contains the data scrapers used to collect event information from various sources.

## Available Scrapers

- **AERC Calendar Scraper**: Enhanced scraper using Gemini AI to extract detailed event information

## Running Scrapers

Scrapers can be run individually or all at once using the `run_scrapers.py` script:

```bash
# Run all scrapers
python -m scrapers.run_scrapers

# Run a specific scraper
python -m scrapers.run_scrapers aerc_calendar
```

## AERC Calendar Scraper

The AERC Calendar Scraper is an enhanced scraper that uses the Google Gemini API to extract structured data from the AERC calendar website. It follows these steps:

1. Extracts season IDs from the AERC calendar page
2. Fetches calendar HTML using these season IDs
3. Cleans the HTML to prepare for processing
4. Uses Gemini API to extract structured data from the HTML
5. Converts the structured data to the database schema
6. Stores the events in the database

### Requirements

- Google Gemini API key (set in `.env` file as `GEMINI_API_KEY`)
- Python packages: `google-generativeai`, `aiohttp`, `beautifulsoup4`

### Fallback Mechanism

If the Gemini API extraction fails, the scraper will:
1. Retry with the more powerful `gemini-2.0-flash` model
2. If that also fails, use a regex-based fallback extraction method

## Adding New Scrapers

To add a new scraper:

1. Create a new module in the `scrapers` directory
2. Implement the scraper interface
3. Add the scraper to the `run_scraper` function in `app/services/scraper_service.py`
4. Add the scraper ID to the `scraper_ids` list in `scrapers/run_scrapers.py`
