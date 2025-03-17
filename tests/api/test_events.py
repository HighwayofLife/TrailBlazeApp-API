import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

# Just test that the API endpoints respond correctly
# Skip actual data creation due to the database connection issues
def test_read_events(client: TestClient):
    """Test reading the events endpoint."""
    # Test the endpoint
    response = client.get("/api/v1/events/")
    
    # Now that the database is working, we expect a 200 response with a list
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # We don't assert the list is empty since there might be events from previous tests
    # Just check that we got a valid response

def test_create_event(client: TestClient):
    """Test creating a new event."""
    event_data = {
        "name": "New Test Event",
        "location": "Test Location",
        "date_start": datetime.now().isoformat(),
        "region": "Pacific Northwest",
        "distances": ["25", "50"],
        "source": "TEST"
    }
    
    response = client.post(
        "/api/v1/events/",
        json=event_data
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Test Event"
    assert "id" in data
    
    # Verify the event was created by getting it
    event_id = data["id"]
    response = client.get(f"/api/v1/events/{event_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "New Test Event"


def test_read_event(client):
    """Test reading a specific event."""
    # First create an event
    event_data = {
        "name": "Test Ride",
        "location": "Test Location",
        "date_start": datetime.now().isoformat(),
        "region": "Pacific Northwest",
        "source": "TEST"
    }
    
    # Create the event
    response = client.post("/api/v1/events/", json=event_data)
    assert response.status_code == 201
    event_id = response.json()["id"]
    
    # Test the endpoint
    response = client.get(f"/api/v1/events/{event_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Ride"
    assert data["id"] == event_id


def test_update_event(client):
    """Test updating an event."""
    # First create an event
    event_data = {
        "name": "Test Ride",
        "location": "Test Location",
        "date_start": datetime.now().isoformat(),
        "region": "Pacific Northwest",
        "source": "TEST"
    }
    
    # Create the event
    response = client.post("/api/v1/events/", json=event_data)
    assert response.status_code == 201
    event_id = response.json()["id"]
    
    # Update data
    update_data = {
        "name": "Updated Event Name",
        "description": "New description"
    }
    
    # Test the endpoint
    response = client.put(
        f"/api/v1/events/{event_id}",
        json=update_data
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Event Name"
    assert data["description"] == "New description"
    assert data["location"] == "Test Location"  # Should remain unchanged


def test_delete_event(client):
    """Test deleting an event."""
    # First create an event
    event_data = {
        "name": "Test Ride to Delete",
        "location": "Test Location",
        "date_start": datetime.now().isoformat(),
        "region": "Pacific Northwest",
        "source": "TEST"
    }
    
    # Create the event
    response = client.post("/api/v1/events/", json=event_data)
    assert response.status_code == 201
    event_id = response.json()["id"]
    
    # Test the endpoint
    response = client.delete(f"/api/v1/events/{event_id}")
    
    assert response.status_code == 204
    
    # Verify it's gone
    response = client.get(f"/api/v1/events/{event_id}")
    assert response.status_code == 404
