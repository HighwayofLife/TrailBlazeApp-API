"""Tests for shared database handler."""

import pytest
from datetime import datetime
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models.event import Event
from scrapers.database import DatabaseHandler
from scrapers.exceptions import DatabaseError

@pytest.fixture
def test_db_url():
    """Get test database URL."""
    return "postgresql+asyncpg://test:test@localhost:5432/test_db"

@pytest.fixture
async def test_engine(test_db_url):
    """Create test database engine."""
    engine = create_async_engine(test_db_url)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Event.metadata.create_all)
    
    yield engine
    
    # Drop tables
    async with engine.begin() as conn:
        await conn.run_sync(Event.metadata.drop_all)
    
    await engine.dispose()

@pytest.fixture
async def test_session(test_engine):
    """Create test database session."""
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session

@pytest.fixture
def db_handler(test_db_url):
    """Create database handler instance."""
    handler = DatabaseHandler(test_db_url)
    return handler

@pytest.fixture
def event_data():
    """Create test event data."""
    return {
        "name": "Test Event",
        "source": "AERC",
        "event_type": "endurance",
        "date_start": datetime.now(),
        "location": {
            "name": "Test Venue",
            "city": "Test City",
            "state": "CA"
        },
        "distances": [
            {
                "distance": "50 Miles",
                "date": datetime.now(),
                "start_time": "6:00 AM"
            }
        ],
        "contacts": [
            {
                "name": "John Doe",
                "email": "john@example.com",
                "role": "Ride Manager"
            }
        ]
    }

@pytest.mark.asyncio
async def test_store_new_event(db_handler, test_session, event_data):
    """Test storing a new event."""
    result = await db_handler.store_events([event_data], test_session)
    assert result['added'] == 1
    assert result['updated'] == 0
    
    # Verify event was stored
    query = text("SELECT COUNT(*) FROM events")
    result = await test_session.execute(query)
    count = result.scalar()
    assert count == 1

@pytest.mark.asyncio
async def test_update_existing_event(db_handler, test_session, event_data):
    """Test updating an existing event."""
    # First create an event
    event_data['external_id'] = "test123"
    await db_handler.store_events([event_data], test_session)
    
    # Update the event
    event_data['name'] = "Updated Event"
    result = await db_handler.store_events([event_data], test_session)
    
    assert result['updated'] == 1
    assert result['added'] == 0
    
    # Verify event was updated
    query = text("SELECT name FROM events WHERE external_id = :id")
    result = await test_session.execute(query, {"id": "test123"})
    name = result.scalar()
    assert name == "Updated Event"

@pytest.mark.asyncio
async def test_location_deduplication(db_handler, test_session, event_data):
    """Test that locations are deduplicated."""
    # Create two events with same location
    event2_data = event_data.copy()
    event2_data['name'] = "Second Event"
    
    await db_handler.store_events([event_data, event2_data], test_session)
    
    # Verify only one location was created
    query = text("SELECT COUNT(*) FROM locations")
    result = await test_session.execute(query)
    count = result.scalar()
    assert count == 1

@pytest.mark.asyncio
async def test_store_events_with_distances(db_handler, test_session, event_data):
    """Test storing events with distances."""
    # Add multiple distances
    event_data['distances'].append({
        "distance": "100 Miles",
        "date": datetime.now(),
        "start_time": "5:00 AM"
    })
    
    await db_handler.store_events([event_data], test_session)
    
    # Verify distances were stored
    query = text("SELECT COUNT(*) FROM event_distances")
    result = await test_session.execute(query)
    count = result.scalar()
    assert count == 2

@pytest.mark.asyncio
async def test_store_events_with_contacts(db_handler, test_session, event_data):
    """Test storing events with contacts."""
    # Add multiple contacts
    event_data['contacts'].append({
        "name": "Jane Doe",
        "role": "Control Judge"
    })
    
    await db_handler.store_events([event_data], test_session)
    
    # Verify contacts were stored
    query = text("SELECT COUNT(*) FROM event_contacts")
    result = await test_session.execute(query)
    count = result.scalar()
    assert count == 2

@pytest.mark.asyncio
async def test_store_events_error_handling(db_handler, test_session):
    """Test error handling during event storage."""
    # Invalid event data
    invalid_data = {
        "name": "Invalid Event",
        # Missing required fields
    }
    
    result = await db_handler.store_events([invalid_data], test_session)
    assert result['skipped'] == 1
    
    metrics = db_handler.get_metrics()
    assert metrics['errors'] == 1

@pytest.mark.asyncio
async def test_metrics_collection(db_handler, test_session, event_data):
    """Test metrics collection."""
    # Store multiple events
    event2_data = event_data.copy()
    event2_data['name'] = "Second Event"
    
    await db_handler.store_events([event_data, event2_data], test_session)
    
    metrics = db_handler.get_metrics()
    assert metrics['inserts'] == 2
    assert metrics['updates'] == 0
    assert 'operation_time' in metrics
    assert metrics['avg_batch_size'] == 2