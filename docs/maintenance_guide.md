# Maintenance Guide

## Summary

This document provides guidelines and procedures for maintaining the TrailBlazeApp-API in production. It covers monitoring, logging, troubleshooting, updates, and performance optimization to ensure the application remains reliable and efficient.

## Table of Contents

- [Routine Maintenance Tasks](#routine-maintenance-tasks)
- [Monitoring](#monitoring)
- [Logging](#logging)
- [Troubleshooting](#troubleshooting)
- [Backup and Recovery](#backup-and-recovery)
- [Updates and Upgrades](#updates-and-upgrades)
- [Performance Optimization](#performance-optimization)
- [Security Maintenance](#security-maintenance)
- [API Versioning and Deprecation](#api-versioning-and-deprecation)
- [Cache Management](#cache-management)

## Routine Maintenance Tasks

### Daily Tasks

- Review error logs
- Monitor API usage and response times
- Check scraper status and logs
- Verify database connectivity

### Weekly Tasks

- Review system performance metrics
- Check for security advisories for dependencies
- Verify data integrity
- Backup database

### Monthly Tasks

- Analyze long-term performance trends
- Review and rotate API keys
- Test disaster recovery procedures
- Update documentation if needed

## Monitoring

### Key Metrics to Monitor

1. **System Health**
   - CPU usage
   - Memory usage
   - Disk space
   - Network traffic

2. **Application Metrics**
   - Request rates
   - Response times
   - Error rates
   - Endpoint usage statistics

3. **Database Metrics**
   - Query performance
   - Connection pool status
   - Disk usage
   - Replication lag (if applicable)

### Setting Up Monitoring

#### Prometheus Setup

1. **Install Prometheus Exporter:**

```python
# Install dependencies
pip install prometheus-client

# In app/middleware.py
from prometheus_client import Counter, Histogram
from fastapi import Request

# Define metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP Requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP Request Latency',
    ['method', 'endpoint']
)

# Add middleware to record metrics
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    
    duration = time.time() - start_time
    REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)
    
    REQUEST_COUNT.labels(
        method=request.method, 
        endpoint=request.url.path,
        status_code=response.status_code
    ).inc()
    
    return response
```

2. **Expose Metrics Endpoint:**

```python
# In app/main.py
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response

@app.get("/metrics")
async def metrics():
    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
```

#### Cloud Provider Monitoring

Configure monitoring using your cloud provider's tools:

- **Azure**: Application Insights
- **AWS**: CloudWatch
- **GCP**: Cloud Monitoring

### Setting Up Alerts

Create alerts for critical conditions:

1. **High Error Rate Alert:**
   - Trigger: Error rate > 5% in a 5-minute period
   - Action: Send notification and/or auto-scale

2. **Slow Response Alert:**
   - Trigger: 95th percentile response time > 500ms
   - Action: Send notification

3. **Disk Space Alert:**
   - Trigger: Disk space < 20%
   - Action: Send notification

## Logging

### Log Structure

Logs should include the following information:

- Timestamp
- Log level
- Service name
- Request ID (for tracing)
- User ID (if applicable)
- Message
- Additional context (JSON formatted)

### Log Configuration

```python
# In app/logging_config.py
import logging
import json
from pythonjsonlogger import jsonlogger

def setup_logging():
    logger = logging.getLogger()
    handler = logging.StreamHandler()
    
    formatter = jsonlogger.JsonFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    log_level = os.getenv("LOG_LEVEL", "INFO")
    logger.setLevel(getattr(logging, log_level))
    
    return logger
```

### Log Aggregation

Configure log aggregation using:

- **ELK Stack**: Elasticsearch, Logstash, Kibana
- **Cloud Provider Solutions**: Azure Log Analytics, AWS CloudWatch Logs, GCP Cloud Logging

## Troubleshooting

### Common Issues and Solutions

#### 1. API Endpoint Returns 500 Error

**Troubleshooting Steps:**
1. Check application logs for exceptions
2. Verify database connectivity
3. Check if external services (like Gemini API) are available
4. Review recent code changes

**Solution:**
- Fix the identified issue in the code
- Deploy a hotfix if necessary
- Consider implementing circuit breakers for external dependencies

#### 2. Slow API Responses

**Troubleshooting Steps:**
1. Check database query performance
2. Monitor system resources
3. Review API endpoint implementation
4. Check for N+1 query problems

**Solution:**
- Optimize database queries
- Add database indexes
- Implement caching
- Scale resources if needed

#### 3. Data Scraper Failures

**Troubleshooting Steps:**
1. Check scraper logs for errors
2. Verify source websites are accessible
3. Check if source website structure has changed

**Solution:**
- Update scraper to match new website structure
- Implement more robust error handling
- Set up notifications for scraper failures

### Debugging Tools

1. **Application Performance Monitoring (APM):**
   - New Relic
   - Datadog
   - Elastic APM

2. **Request Tracing:**
   - OpenTelemetry
   - Jaeger
   - Zipkin

## Backup and Recovery

### Database Backup Strategy

1. **Automated Regular Backups:**
   - Daily full backups
   - Hourly transaction log backups
   - Retention period: 30 days

2. **Manual Backups Before Major Changes:**
   - Before schema changes
   - Before large data imports

### Backup Implementation

```bash
# PostgreSQL backup script (for automation)
#!/bin/bash
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="/path/to/backups"
DB_NAME="trailblaze"
DB_USER="postgres"

# Create backup
pg_dump -U $DB_USER -d $DB_NAME -F c -f "$BACKUP_DIR/$DB_NAME-$TIMESTAMP.backup"

# Delete backups older than 30 days
find $BACKUP_DIR -name "*.backup" -type f -mtime +30 -delete
```

### Recovery Procedures

1. **For a single table or data issue:**

```bash
# Restore specific table
pg_restore -U $DB_USER -d $DB_NAME -t table_name backup_file.backup
```

2. **For complete database recovery:**

```bash
# Create empty database
createdb -U $DB_USER $DB_NAME

# Restore from backup
pg_restore -U $DB_USER -d $DB_NAME backup_file.backup
```

## Updates and Upgrades

### Dependency Updates

1. **Regular Security Updates:**
   - Review security advisories weekly
   - Apply critical patches immediately
   - Schedule regular updates for non-critical dependencies

2. **Major Version Upgrades:**
   - Test thoroughly in staging environment
   - Document breaking changes
   - Plan for backward compatibility

### Update Process

1. **Create an update plan:**
   - List dependencies to update
   - Note breaking changes
   - Plan for compatibility issues

2. **Update in development environment:**

```bash
# Update dependencies
pip install -U package-name

# Freeze updated requirements
pip freeze > requirements.txt
```

3. **Run tests and fix issues**
4. **Deploy to staging and test**
5. **Deploy to production**

## Performance Optimization

### Database Optimization

1. **Add Indexes:**
   - Identify slow queries using PostgreSQL query logs
   - Add appropriate indexes

```sql
-- Example: Adding an index to events table
CREATE INDEX idx_events_date ON events(date_start, date_end);
```

2. **Query Optimization:**
   - Use EXPLAIN ANALYZE to evaluate query performance
   - Rewrite inefficient queries
   - Consider materialized views for complex queries

### API Optimization

1. **Response Caching:**

```python
# Example using fastapi-cache
from fastapi_cache import FastAPICache
from fastapi_cache.decorator import cache

@router.get("/events")
@cache(expire=300)  # Cache for 5 minutes
async def get_events():
    # ...
```

2. **Pagination:**
   - Implement cursor-based pagination for large result sets
   - Limit maximum result size

3. **Async Operations:**
   - Use async IO for database operations and external API calls
   - Batch related operations where possible

## Security Maintenance

### Regular Security Tasks

1. **Dependency Scanning:**
   - Use tools like Safety, Dependabot, or Snyk
   - Schedule weekly scans

2. **API Key Rotation:**
   - Rotate API keys quarterly
   - Update keys in secure storage

3. **Access Review:**
   - Review access permissions monthly
   - Remove unused accounts
   - Enforce least privilege

### Security Patching

1. **Critical Vulnerabilities:**
   - Patch immediately
   - Deploy off-schedule if necessary

2. **Non-Critical Vulnerabilities:**
   - Include in regular update cycle
   - Document mitigation if patching is delayed

## API Versioning and Deprecation

### Versioning Strategy

We use URL-based versioning (e.g., `/v1/events`).

### Adding a New API Version

1. **Create new endpoint structure:**

```python
# In app/api/v2/endpoints/events.py
from fastapi import APIRouter, Depends
from app.schemas.event import EventResponse

router = APIRouter()

@router.get("/events", response_model=List[EventResponse])
async def get_events_v2():
    # New implementation
```

2. **Include in the API router:**

```python
# In app/api/v2/__init__.py
from fastapi import APIRouter
from app.api.v2.endpoints import events, assistant

api_router = APIRouter()
api_router.include_router(events.router, tags=["events"])
api_router.include_router(assistant.router, tags=["assistant"])
```

3. **Add to main application:**

```python
# In app/main.py
from app.api.v1 import api_router as api_router_v1
from app.api.v2 import api_router as api_router_v2

app.include_router(api_router_v1, prefix="/v1")
app.include_router(api_router_v2, prefix="/v2")
```

### Deprecating API Endpoints

1. **Mark as deprecated in OpenAPI:**

```python
from fastapi import APIRouter, Depends, HTTPException
import warnings

router = APIRouter()

@router.get("/old-endpoint", deprecated=True)
async def old_endpoint():
    """
    This endpoint is deprecated and will be removed in v3.
    Please use /new-endpoint instead.
    """
    warnings.warn("Using deprecated endpoint", DeprecationWarning)
    # Implementation
```

2. **Communicate timeline:**
   - Announce deprecation in documentation
   - Set concrete removal date
   - Provide migration path

## Cache Management

### Cache Strategy

The application uses a caching system to improve performance and reduce load on external services. This includes:

1. **HTML Source Caching**: Raw HTML responses from scraped websites
2. **Structured Data Caching**: Processed JSON data extracted from HTML
3. **API Response Caching**: Responses from external APIs (like Gemini)

### Cache Configuration

Cache behavior can be controlled through environment variables:

```bash
# Force cache refresh
SCRAPER_REFRESH=true

# Enable cache debugging
SCRAPER_DEBUG=true

# Enable validation checks
SCRAPER_VALIDATE=true
```

### Cache TTL Recommendations

Different types of data should have different Time-To-Live (TTL) settings:

1. **HTML Source Data**: 24 hours (refresh daily)
2. **Structured JSON Data**: 12 hours
3. **Database Comparison Results**: 6 hours
4. **External API Responses**: 7 days (for stable reference data)

### Managing Cache Manually

To clear the cache before running scrapers:

```bash
# Clear all cache
rm -rf cache/*

# Clear specific cache entries
rm -rf cache/aerc_calendar_*.json
```

### Cache Validation

The system should validate cached data by:

1. **Timestamp Validation**: Check if cached data is within TTL
2. **Count Validation**: Compare HTML row count to JSON event count
3. **Consistency Checks**: Ensure data format matches expected schema

### When to Force Cache Invalidation

Cache should be forcibly invalidated under these conditions:

1. **Schedule Changes**: When source websites update their schedules
2. **Manual Triggers**: During debugging or data verification
3. **Validation Failures**: When inconsistencies are detected
4. **Data Format Changes**: When source websites change their HTML structure

### Running Scrapers with Cache Control

```bash
# Run with default cache behavior
docker-compose exec manage python -m scrapers.run_scrapers aerc_calendar

# Run with cache refresh
docker-compose exec -e SCRAPER_REFRESH=true manage python -m scrapers.run_scrapers aerc_calendar

# Run with validation
docker-compose exec -e SCRAPER_VALIDATE=true manage python -m scrapers.run_scrapers aerc_calendar

# Run with debug logging and cache metrics
docker-compose exec -e SCRAPER_DEBUG=true manage python -m scrapers.run_scrapers aerc_calendar
```

### Verifying Cache Efficiency

Cache performance should be monitored to ensure optimal configuration:

1. **Cache Hit Rate**: Percentage of requests served from cache
2. **Cache Size**: Total storage used by cached data
3. **Cache Freshness**: Age distribution of cached entries
4. **Cache Validation Success Rate**: Percentage of cache entries passing validation

Regular monitoring of these metrics helps identify when cache parameters need adjustment.
