# Data Enrichment Strategy: Geocoding and Website/Flyer Processing

## 1. Introduction

This document outlines the strategy for enriching event data in the TrailBlazeApp API. The primary goal is to enhance the quality and completeness of event information by adding:

*   **Geocoding (GPS Coordinates):**  Latitude and longitude to enable location-based features.
*   **Website/Flyer Processing:**  Detailed information extracted from event websites and flyers using Gemini AI to enrich event details beyond the basic scraped data.

We need to decide the optimal timing and approach for these enrichment processes, considering factors like scraper efficiency, maintainability, error handling, and the need for ongoing event updates.

## 2. Options for Data Enrichment Timing

We have considered three main options for when to perform geocoding and website/flyer processing:

### 2.1. Option 1: Combined Post-Process (Recommended)

**Description:**

*   **Scraping Phase:** The scraper focuses solely on extracting basic event data (name, location, dates, URLs, flyer URLs) from the source HTML page and stores this initial data in the database.
*   **Post-Processing Phase:** A single, dedicated post-processing script (`enrich_events.py`) is executed after scraping. This script handles both geocoding and website/flyer processing in a batch manner.

**Workflow:**

1.  **Scraper Runs:** Extracts basic event data and saves to the database.
2.  **`enrich_events.py` Script Runs (Post-Process):**
    *   Queries the database for events needing enrichment (e.g., missing GPS coordinates or detailed `event_details`).
    *   Geocodes event locations using the `GeocodingService`.
    *   Fetches website/flyer content for each event.
    *   Makes Gemini API calls to extract detailed information from website/flyer content.
    *   Updates the `event_details` JSONB field and potentially other relevant fields in the `events` table.
    *   Implements tiered update cadence logic (nightly for events within 3 months, weekly for events further out).

**Pros:**

*   **Simplified Workflow:** Clear separation of scraping and enrichment, with enrichment consolidated into a single post-processing step.
*   **Batch Efficiency:** Allows for efficient batch processing of both geocoding and Gemini API calls, optimizing API usage and potentially reducing costs.
*   **Decoupled Scraping:** The scraper remains lightweight and focused on initial data extraction, making it faster and easier to maintain.
*   **Centralized Enrichment Logic:** All enrichment logic (geocoding and website/flyer processing) is located in one script, improving maintainability and updates.
*   **Efficient Update Cadence:**  The post-process script can efficiently implement the tiered update frequency based on event date proximity.

**Cons:**

*   **Longer Post-Processing Time:** The `enrich_events.py` script will take longer to execute as it performs both geocoding and website/flyer processing. However, this is acceptable if it runs nightly.
*   **Potential Bottleneck in Post-Process:** If the volume of events and website/flyer processing grows significantly, the post-processing script itself could become a bottleneck. This can be addressed later with scaling strategies if needed.

### 2.2. Option 2: Staged Post-Processing

**Description:**

*   **Scraping Phase:**  Same as Option 1 - scraper extracts basic data.
*   **Post-Processing Phase 1 (Geocoding):**  The `geocode_events.py` script is run first to quickly add GPS coordinates to events.
*   **Post-Processing Phase 2 (Website/Flyer Enrichment):** A separate script (`enrich_website_flyer.py`) is run afterwards, focusing solely on website/flyer processing and Gemini API calls.

**Workflow:**

1.  **Scraper Runs:** Extracts basic event data and saves to the database.
2.  **`geocode_events.py` Script Runs (Post-Process - Geocoding):** Adds GPS coordinates to events.
3.  **`enrich_website_flyer.py` Script Runs (Post-Process - Website/Flyer):**
    *   Queries the database for events needing website/flyer enrichment.
    *   Fetches website/flyer content.
    *   Makes Gemini API calls to extract detailed information.
    *   Updates `event_details` and other fields.
    *   Implements tiered update cadence logic.

**Pros:**

*   **Further Decoupling:**  Even greater separation of concerns. Geocoding and website/flyer processing are completely independent processes.
*   **Potentially Faster Initial Geocoding:** Geocoding is performed quickly in the first post-process, making basic location-based features available sooner.
*   **Scalability for Enrichment:** If website/flyer processing becomes a major bottleneck, this second post-process could be scaled independently.

**Cons:**

*   **More Complex Workflow:** Two post-processing steps to manage and schedule.
*   **Slightly Increased Management Overhead:** Requires managing two separate scripts and their scheduling.

### 2.3. Option 3: In-Scrape Website/Flyer Processing (Not Recommended)

**Description:**

*   Integrate website/flyer processing and Gemini API calls directly within the scraper's main loop. Geocoding could also be done within the scraper.

**Cons:**

*   **Increased Scraper Complexity:** The scraper becomes significantly more complex, handling scraping, geocoding, website/flyer processing, and Gemini API interactions.
*   **Potential Scraper Slowdown:**  Website/flyer processing and Gemini API calls are time-consuming. Integrating them into the scraper will make the scraping process much slower and potentially more prone to timeouts and errors.
*   **Error Handling Coupling:** Error handling for scraping, geocoding, and website/flyer processing becomes tightly coupled within the scraper, making it harder to debug and manage.
*   **Reduced Maintainability:** A monolithic scraper is harder to maintain, test, and update compared to decoupled processes.

## 3. Challenges

Implementing data enrichment will present several challenges:

*   **Gemini API Rate Limits and Costs:**  Website/flyer processing will likely involve a significant number of Gemini API calls. We need to be mindful of API rate limits and costs. Batching Gemini API calls (as suggested in `next_steps_prompt.md`) and efficient data handling will be crucial.
*   **Geocoding Service Reliability:** Geocoding services can have rate limits, downtime, and accuracy issues. Robust error handling, retries, and potentially caching are necessary in the `GeocodingService`.
*   **Website/Flyer Content Variability:** Websites and flyers have diverse structures and formats.  Gemini AI prompts and extraction logic will need to be robust enough to handle this variability. We may need to refine prompts and parsing strategies iteratively.
*   **Data Consistency and Updates:**  Ensuring data consistency across updates and handling cases where website/flyer information changes frequently will require careful design of the update cadence and data storage.
*   **Error Monitoring and Logging:**  Comprehensive logging and error monitoring will be essential to track the success and failure rates of both geocoding and website/flyer processing, allowing for timely issue resolution.

## 4. Recommended Approach

**Option 1: Combined Post-Process** is the recommended approach for the following reasons:

*   **Best Balance of Simplicity and Efficiency:** It provides a clear separation of concerns while keeping the enrichment workflow manageable in a single post-processing script.
*   **Suitable for Nightly Cadence:** Given the nightly cron schedule for scraping, the longer post-processing time of the combined script is acceptable.
*   **Optimized Batch Processing:**  Allows for efficient batching of both geocoding and Gemini API calls, which is crucial for managing API usage and costs.
*   **Maintainability:**  Keeps the scraper focused and the enrichment logic centralized, improving long-term maintainability.

While Option 2 offers even more decoupling, the added complexity of managing two post-processing scripts is not justified at this stage, especially given that Option 1 provides a good balance and can be optimized further if needed. Option 3 is explicitly not recommended due to its significant drawbacks.

## 5. Next Steps

1.  **Implement `enrich_events.py` Script:** Create a new Python script in the `scripts/` directory named `enrich_events.py`. This script should:
    *   Import and utilize the `GeocodingService` to geocode events.
    *   Implement logic to fetch website and flyer content for events.
    *   Use the Gemini API (via `ai_service.py`) to process website/flyer content and extract detailed event information.
    *   Update the `event_details` JSONB field and potentially other relevant fields in the `events` table.
    *   Implement the tiered update cadence logic (nightly/weekly checks).
    *   Include robust error handling and logging.

2.  **Schedule `enrich_events.py`:** Configure a cron job (or similar scheduling mechanism) to run `scripts/enrich_events.py` nightly, shortly after the scraper cron job is scheduled to complete.

3.  **Testing and Refinement:** Thoroughly test the `enrich_events.py` script, including:
    *   Testing geocoding accuracy and error handling.
    *   Validating website/flyer processing and Gemini API integration.
    *   Verifying the tiered update cadence logic.
    *   Monitoring API usage and costs.
    *   Refine Gemini prompts and extraction logic based on testing and data review.

4.  **Documentation Update:** Update the project documentation (including `data_model.md`, `data_scraping_guide.md`, and potentially a new `data_enrichment_guide.md`) to reflect the data enrichment process, the `enrich_events.py` script, configuration options, and the update cadence strategy.

## 6. Suggestions and Considerations

*   **Caching:** Implement caching mechanisms at various levels (geocoding results, website/flyer content, Gemini API responses if feasible) to reduce redundant API calls and improve performance.
*   **Asynchronous Processing:**  Within `enrich_events.py`, utilize asynchronous operations (e.g., `asyncio`, `aiohttp`) to handle network requests and Gemini API calls concurrently, maximizing efficiency.
*   **Monitoring and Alerting:** Set up monitoring for the `enrich_events.py` script to track its execution time, success/failure rates, and API usage. Implement alerting for critical errors or performance issues.
*   **Future Scalability:**  If data volume or processing complexity increases significantly, consider more advanced scaling strategies for the post-processing, such as:
    *   Task queues (e.g., Celery, Redis Queue) to distribute enrichment tasks across workers.
    *   Database optimizations for handling larger datasets and update loads.
    *   Exploring more efficient or cost-effective geocoding and AI services.
*   **Data Quality Monitoring:**  Implement processes to periodically review the quality of enriched data and identify areas for improvement in scraping, geocoding, or website/flyer processing logic.

## 7. Conclusion

By adopting the **Combined Post-Process** approach and following the outlined next steps, we can effectively implement data enrichment for TrailBlazeApp API, enhancing event data with geocoding and detailed information from websites and flyers. This strategy prioritizes maintainability, efficiency, and scalability while providing a robust framework for ongoing event updates. 