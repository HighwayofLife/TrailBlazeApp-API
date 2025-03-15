import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.event import create_event
from app.schemas.event import EventCreate


@pytest.mark.asyncio
async def test_read_events(client: TestClient, db_session: AsyncSession):
    """Test reading a list of events."""
    # Create test events
    event1 = EventCreate(
        name="Test Ride 1",
        location="Test Location 1",
        date_start=datetime.now(),
        region="Pacific Northwest",
        distances=["25", "50"]
    )
    event2 = EventCreate(
        name="Test Ride 2",
        location="Test Location 2",
        date_start=datetime.now() + timedelta(days=10),
        region="Pacific Northwest",
        distances=["25", "50", "100"]
    )
    
    await create_event(db_session, event1)
    await create_event(db_session, event2)
    
    # Test the endpoint
    response = client.get("/api/v1/events/")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "Test Ride 1"
    assert data[1]["name"] == "Test Ride 2"


@pytest.mark.asyncio
async def test_create_event(client: TestClient):
    """Test creating a new event."""
    event_data = {
        "name": "New Test Event",
        "location": "Test Location",
        "date_start": datetime.now().isoformat(),
        "region": "Pacific Northwest",
        "distances": ["25", "50"]
    }
    
    response = client.post(
        "/api/v1/events/",
        json=event_data
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Test Event"
    assert "id" in data


@pytest.mark.asyncio
async def test_read_event(client: TestClient, db_session: AsyncSession):
    """Test reading a specific event."""
    # Create a test event
    event = EventCreate(
        name="Test Ride",
        location="Test Location",
        date_start=datetime.now(),
        region="Pacific Northwest"
    )
    
    db_event = await create_event(db_session, event)
    
    # Test the endpoint
    response = client.get(f"/api/v1/events/{db_event.id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Ride"
    assert data["id"] == db_event.id


@pytest.mark.asyncio
async def test_update_event(client: TestClient, db_session: AsyncSession):
    """Test updating an event."""
    # Create a test event
    event = EventCreate(
        name="Test Ride",
        location="Test Location",
        date_start=datetime.now(),
        region="Pacific Northwest"
    )
    
    db_event = await create_event(db_session, event)
    
    # Update data
    update_data = {
        "name": "Updated Event Name",
        "description": "New description"
    }
    
    # Test the endpoint
    response = client.put(
        f"/api/v1/events/{db_event.id}",
        json=update_data
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Event Name"
    assert data["description"] == "New description"
    assert data["location"] == "Test Location"  # Should remain unchanged


@pytest.mark.asyncio
async def test_delete_event(client: TestClient, db_session: AsyncSession):
    """Test deleting an event."""
    # Create a test event
    event = EventCreate(
        name="Test Ride to Delete",
        location="Test Location",
        date_start=datetime.now(),
        region="Pacific Northwest"
    )
    
    db_event = await create_event(db_session, event)
    
    # Test the endpoint
    response = client.delete(f"/api/v1/events/{db_event.id}")
    
    assert response.status_code == 204
    
    # Verify it's gone
    response = client.get(f"/api/v1/events/{db_event.id}")
    assert response.status_code == 404
