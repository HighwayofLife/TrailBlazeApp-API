import asyncio
import os
import logging
from typing import Generator

print("Loading conftest.py with test_event function")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.models.event import Event
from app.schemas.event import EventCreate

# Set test database URL
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@test-db/test_trailblaze"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=True,
    pool_pre_ping=True
)

# Create test session
test_async_session = sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)

# Create a logger
logger = logging.getLogger(__name__)

# Session and client for use in the tests
_test_client = None
_test_session = None

@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


# Initialize the test database
@pytest.fixture(scope="session", autouse=True)
async def initialize_test_db():
    """Initialize the test database."""
    # Make sure the test database exists and is accessible
    engine = test_engine
    
    try:
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        
        # Verify tables were created by checking one of them
        async with engine.begin() as conn:
            result = await conn.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'events')")
            exists = result.scalar()
            if not exists:
                raise Exception("Failed to create tables in the test database")
            
        logger.info("Test database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize test database: {str(e)}")
        raise
    
    yield
    
    # Clean up at the end of all tests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# Reset the database before each test
@pytest.fixture(autouse=True)
async def reset_test_db():
    """Reset the test database before each test."""
    # Clear all data from tables without dropping them
    async with test_engine.begin() as conn:
        # Get list of all tables
        tables = Base.metadata.sorted_tables
        for table in reversed(tables):
            await conn.execute(table.delete())
    
    yield


# Get a test client (not async)
@pytest.fixture
def client():
    """
    Get a test client. This uses a global test client for better performance.
    """
    # Override the database dependency
    async def override_get_db():
        async with test_async_session() as session:
            try:
                yield session
            finally:
                await session.close()
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Clean up
    app.dependency_overrides.pop(get_db, None)


# Helper to create test events (not a fixture)
async def create_test_event(db_session: AsyncSession, event: EventCreate) -> Event:
    """Create a test event directly."""
    db_event = Event(
        name=event.name,
        description=event.description,
        location=event.location,
        date_start=event.date_start,
        date_end=event.date_end,
        organizer=event.organizer,
        website=event.website,
        flyer_url=event.flyer_url,
        region=event.region,
        distances=event.distances,
        ride_manager=event.ride_manager,
        manager_email=event.manager_email,
        manager_phone=event.manager_phone,
        judges=event.judges,
        directions=event.directions,
        map_link=event.map_link,
        manager_contact=event.manager_contact,
        event_type=event.event_type,
        event_details=event.event_details,
        notes=event.notes,
        external_id=event.external_id,
        source=event.source,
    )
    
    db_session.add(db_event)
    await db_session.commit()
    await db_session.refresh(db_event)
    
    logger.info(f"Created test event: {db_event.id} - {db_event.name}")
    return db_event
