"""Tests for database handler module."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.event import EventCreate
from scrapers.aerc_scraper.database import DatabaseHandler
from scrapers.aerc_scraper.exceptions import DatabaseError

@pytest.fixture
def db_handler():
    """Create database handler instance."""
    return DatabaseHandler()

@pytest.fixture
def mock_db():
    """Create mock database session."""
    return MagicMock(spec=AsyncSession)

@pytest.fixture
def sample_db_events():
    """Create sample database events."""
    return [
        EventCreate(
            name="Test Event 1",
            date_start=datetime(2024, 3, 15),
            date_end=datetime(2024, 3, 15),
            location="Test Location 1",
            region="W",
            event_type="endurance",
            description="Test description",
            distances=["50"],
            source="AERC"
        ),
        EventCreate(
            name="Test Event 2",
            date_start=datetime(2024, 3, 16),
            date_end=datetime(2024, 3, 16),
            location="Test Location 2",
            region="W",
            event_type="endurance",
            description="Test description 2",
            distances=["100"],
            source="AERC"
        )
    ]

@pytest.mark.asyncio
async def test_store_new_events(db_handler, mock_db, sample_db_events):
    """Test storing new events."""
    # Mock get_events to return empty list (no existing events)
    with patch('app.crud.event.get_events', return_value=[]):
        # Mock create_event
        with patch('app.crud.event.create_event') as mock_create:
            await db_handler.store_events(sample_db_events, mock_db)
            
            assert mock_create.call_count == len(sample_db_events)
            assert db_handler.get_metrics()['added'] == 2
            assert db_handler.get_metrics()['errors'] == 0

@pytest.mark.asyncio
async def test_store_existing_events(db_handler, mock_db, sample_db_events):
    """Test handling existing events."""
    # Mock get_events to return existing events
    with patch('app.crud.event.get_events', return_value=sample_db_events):
        await db_handler.store_events(sample_db_events, mock_db)
        
        assert db_handler.get_metrics()['updated'] == 2
        assert db_handler.get_metrics()['added'] == 0

@pytest.mark.asyncio
async def test_handle_database_error(db_handler, mock_db, sample_db_events):
    """Test handling database errors."""
    # Mock get_events to raise an exception
    with patch('app.crud.event.get_events', side_effect=Exception("Database error")):
        with pytest.raises(DatabaseError):
            await db_handler.store_events(sample_db_events, mock_db)
        
        assert db_handler.get_metrics()['errors'] > 0

@pytest.mark.asyncio
async def test_store_empty_events(db_handler, mock_db):
    """Test storing empty events list."""
    result = await db_handler.store_events([], mock_db)
    
    assert result['added'] == 0
    assert result['updated'] == 0
    assert result['errors'] == 0

@pytest.mark.asyncio
async def test_partial_success(db_handler, mock_db, sample_db_events):
    """Test partial success scenario."""
    # Mock get_events to succeed
    with patch('app.crud.event.get_events', return_value=[]):
        # Mock create_event to fail for second event
        async def mock_create_event(db, event):
            if event.name == "Test Event 2":
                raise Exception("Database error")
        
        with patch('app.crud.event.create_event', side_effect=mock_create_event):
            await db_handler.store_events(sample_db_events, mock_db)
            
            assert db_handler.get_metrics()['added'] == 1
            assert db_handler.get_metrics()['errors'] == 1

@pytest.mark.asyncio
async def test_metrics_collection(db_handler, mock_db, sample_db_events):
    """Test accurate metrics collection."""
    # Setup mixed scenario: one new, one existing, one error
    events = sample_db_events + [
        EventCreate(
            name="Error Event",
            date_start=datetime(2024, 3, 17),
            date_end=datetime(2024, 3, 17),
            location="Error Location",
            region="W",
            event_type="endurance",
            source="AERC"
        )
    ]
    
    # Mock get_events to return one existing event
    with patch('app.crud.event.get_events', return_value=[sample_db_events[0]]):
        # Mock create_event to fail for the error event
        async def mock_create_event(db, event):
            if event.name == "Error Event":
                raise Exception("Database error")
        
        with patch('app.crud.event.create_event', side_effect=mock_create_event):
            await db_handler.store_events(events, mock_db)
            
            metrics = db_handler.get_metrics()
            assert metrics['added'] == 1  # Second event
            assert metrics['updated'] == 1  # First event
            assert metrics['errors'] == 1  # Error event

@pytest.mark.asyncio
async def test_duplicate_detection(db_handler, mock_db):
    """Test duplicate event detection."""
    # Create two events with same name and date
    duplicate_events = [
        EventCreate(
            name="Same Event",
            date_start=datetime(2024, 3, 15),
            date_end=datetime(2024, 3, 15),
            location="Same Location",
            region="W",
            event_type="endurance",
            source="AERC"
        ),
        EventCreate(
            name="Same Event",
            date_start=datetime(2024, 3, 15),
            date_end=datetime(2024, 3, 15),
            location="Same Location",
            region="W",
            event_type="endurance",
            source="AERC"
        )
    ]
    
    # Mock get_events to return the first event
    with patch('app.crud.event.get_events', return_value=[duplicate_events[0]]):
        await db_handler.store_events(duplicate_events, mock_db)
        
        assert db_handler.get_metrics()['updated'] == 1
        assert db_handler.get_metrics()['skipped'] == 1