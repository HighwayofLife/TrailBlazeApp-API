# Data Enrichment Strategy: Service-Oriented Post-Process (Final)

## 1. Introduction

This document outlines the **finalized and refined strategy** for enriching event data in the TrailBlazeApp API, now adopting a **service-oriented post-process** approach. We will use **separate services** for:

*   **Geocoding Service:**  Responsible for adding latitude and longitude to events. This service will be invoked primarily for new events or when event locations are updated.
*   **Website/Flyer Enrichment Service:** Responsible for fetching website/flyer content and using Gemini AI to extract detailed event information. This service will run regularly to keep event details up-to-date.

**Our primary goals remain to:**

*   **Minimize API Costs:**  Efficiently use geocoding and Gemini APIs, focusing on caching and reliable result saving.
*   **Maintainability and Scalability:**  Decouple enrichment from scraping and further decouple geocoding from website/flyer processing into separate services for a more robust and scalable architecture.
*   **Reliability:** Ensure robust error handling and data persistence throughout the enrichment process for both services.
*   **Efficient Updates:** Implement a strategy for regular website/flyer updates and handle location updates and re-geocoding effectively.

## 2. Chosen Strategy: Service-Oriented Post-Process (Refined Option 1)

We have refined **Option 1: Combined Post-Process** into a **Service-Oriented Post-Process** strategy, which provides a more modular and scalable architecture.

**Description:**

*   **Scraping Phase:** Scrapers remain focused on extracting basic event data and storing it in the database.
*   **Post-Processing Services:** We will have **two distinct post-processing services**:
    *   **Geocoding Service (`geocode_events.py` - Refined):**  This service will be invoked primarily for new events or when an event's location is updated. It will be responsible *only* for geocoding.
    *   **Website/Flyer Enrichment Service (`enrich_website_flyer.py` - New):** This new service will run regularly on a schedule to fetch website/flyer content and enrich event details using Gemini AI.

**Workflow:**

1.  **Scrapers Run:** Independent scrapers extract basic event data and save it to the database.
2.  **Geocoding Service (`geocode_events.py` - Refined) - On-Demand or Location Update Trigger:**
    *   **Triggered on New Event Creation:** When a new event is added to the database without `latitude` or `longitude`, the Geocoding Service is triggered.
    *   **Triggered on Location Update:** If an event's `location` field is updated, the Geocoding Service is re-triggered for that event.
    *   **Queries for Events Needing Geocoding:** Selects events from the database that are missing GPS coordinates (i.e., `latitude` or `longitude` is NULL).
    *   **Geocoding:** Uses the `GeocodingService` to geocode event locations in batches.
    *   **Data Update and Persistence:** Updates the `latitude` and `longitude` fields in the `events` table. Ensures reliable saving of geocoding results.
    *   **Caching:** Leverages caching within `GeocodingService` to minimize redundant geocoding API calls.

3.  **Website/Flyer Enrichment Service (`enrich_website_flyer.py` - New) - Scheduled Regular Runs:**
    *   **Scheduled Execution:** This service runs regularly (e.g., nightly) via cron or a scheduler.
    *   **Queries for Events Needing Website/Flyer Enrichment:** Selects events based on criteria like `event_details` being outdated or needing initial enrichment, and the tiered update cadence logic (nightly/weekly checks based on event date proximity and `last_website_check_at` timestamps).
    *   **Website/Flyer Processing:** Fetches website/flyer content for selected events.
    *   **Gemini AI Enrichment:** Makes batched Gemini API calls to extract detailed information from website/flyer content.
    *   **Data Update and Persistence:** Updates the `event_details` JSONB field and potentially other relevant fields in the `events` table. Ensures reliable saving of Gemini API results.
    *   **Tiered Update Cadence:** Implements logic for tiered update frequency (nightly for events within 3 months, weekly for events further out), checking `last_website_check_at` timestamps to avoid redundant processing.
    *   **Caching:** Leverages caching for website/flyer content and potentially Gemini API responses to minimize API calls and improve performance.

**Rationale for Choosing Service-Oriented Post-Process:**

*   **Cost-Effective API Usage:** Both services prioritize batch processing and aggressive caching to minimize API costs.
*   **Microservice Architecture Alignment:**  This strategy fully embraces a microservice architecture with distinct, focused services for scraping, geocoding, and website/flyer enrichment. This enhances modularity, scalability, and independent deployability.
*   **Code Reusability and Sharing:**  Shared code (services, models, utilities) is even more critical in this service-oriented approach. We will ensure proper organization and documentation of shared components.
*   **Optimized Update Cadence:** Separating website/flyer enrichment allows for a dedicated service to manage the regular update cadence efficiently, independent of geocoding.
*   **Scalability and Resource Management:**  Separating services allows for independent scaling and resource allocation. Website/flyer enrichment, being more resource-intensive, can be scaled separately from the lighter-weight geocoding service.
*   **Clearer Responsibilities:** Each service has a well-defined responsibility, making the system easier to understand, develop, and maintain.

**Handling Location Updates and Re-Geocoding:**

*   **Location Change Detection:** We need to implement logic to detect when an event's `location` field is updated. This could be done:
    *   **Within the API Update Event Endpoint:** When the API endpoint for updating an event is called, compare the new `location` value with the existing one. If it has changed, trigger the Geocoding Service for that event.
    *   **Database Triggers (Potentially More Complex):**  PostgreSQL triggers could be used to automatically detect changes to the `location` column and enqueue a geocoding task. This might be overkill for now, but is an option for future consideration.
*   **Re-Geocoding Process:** When a location change is detected, the Geocoding Service will be invoked for that specific event. The service will:
    *   Geocode the new `location`.
    *   Update the `latitude` and `longitude` fields in the `events` table for that event.
    *   Invalidate any cached geocoding results for the old location (if caching is implemented by location string).

## 3. Updated Initial Development and Test Plan (Geocoding Service Focus)

Our initial development and testing phase will now focus on the **Geocoding Service (`geocode_events.py`)** and its on-demand/location-update triggering mechanism.

**Steps:**

1.  **Refine `geocode_events.py` for Geocoding Service Role:**
    *   Update `geocode_events.py` to focus *solely* on geocoding. Remove any website/flyer processing logic (if any was mistakenly added).
    *   Ensure it efficiently queries for events needing geocoding (based on NULL `latitude`/`longitude`).
    *   Implement robust error handling, logging, and caching within the service.

2.  **Implement On-Demand Geocoding Trigger (API Endpoint):**
    *   Modify the API endpoint for updating events (`/api/v1/events/{event_id}`) in `app/routers/events.py` and the corresponding CRUD function (`app/crud/events.py`).
    *   Within the update logic, add a check: if the `location` field is being updated, trigger the `geocode_events.py` script (or a function within it) to re-geocode the event.  For initial simplicity, you can directly call the geocoding function within the API endpoint. For a more robust approach in the future, consider using a task queue to offload the geocoding task.

3.  **Initial Test - On-Demand Geocoding:**
    *   Manually create or update an event via the API, ensuring the `location` field is set or changed.
    *   Verify that the Geocoding Service is triggered automatically after the event update.
    *   Check that the `latitude` and `longitude` fields in the database are correctly updated for the event.
    *   Examine logs to confirm the geocoding process and any errors.

4.  **Batch Geocoding Test (Initial Data Load):**
    *   Run the `geocode_events.py` script directly (via `docker-compose run --rm api python -m scripts.geocode_events`) to batch geocode all existing events that are missing location data.
    *   Verify that the script processes all relevant events and updates their coordinates.
    *   Monitor logs and database updates.

5.  **Remove Limitation and Full Geocoding Processing:**  Ensure `geocode_events.py` processes all events needing geocoding without artificial limitations.

6.  **Monitor and Refine Geocoding Service:** Monitor the performance and reliability of the Geocoding Service. Refine error handling, caching, and API interaction as needed.

## 4. Next Steps (Beyond Geocoding Service)

After establishing the Geocoding Service, we will proceed with developing the **Website/Flyer Enrichment Service (`enrich_website_flyer.py`)**:

1.  **Create `enrich_website_flyer.py` Script:** Develop the new script in `scripts/` to handle website/flyer fetching, Gemini API integration, `event_details` enrichment, and the tiered update cadence logic.

2.  **Schedule `enrich_website_flyer.py`:** Configure a cron job to run this service regularly.

3.  **Implement Tiered Update Cadence in `enrich_website_flyer.py`:**  Implement the logic for nightly/weekly checks based on event date proximity and `last_website_check_at` timestamps (or `updated_at`).

4.  **Caching in Website/Flyer Enrichment Service:** Implement caching for website/flyer content and Gemini API responses within `enrich_website_flyer.py`.

5.  **Error Handling and Monitoring for Both Services:**  Enhance error handling and set up monitoring for both the Geocoding Service and the Website/Flyer Enrichment Service.

6.  **Documentation Update:** Update all relevant documentation to reflect the service-oriented architecture, the two separate post-processing services, their workflows, configuration, and update strategies.

## 5. Conclusion

By adopting this **Service-Oriented Post-Process** strategy, we are building a more scalable, maintainable, and cost-effective data enrichment pipeline. Separating geocoding and website/flyer processing into distinct services allows for optimized resource management, independent scaling, and a clearer separation of concerns, aligning with best practices for microservice architectures. This refined strategy provides a robust and flexible foundation for enriching event data and ensuring its ongoing accuracy and completeness. 