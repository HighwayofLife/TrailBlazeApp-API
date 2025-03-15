import pytest
from unittest import mock
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai_service import get_ai_response
from app.crud.event import create_event
from app.schemas.event import EventCreate
from datetime import datetime


@pytest.mark.asyncio
async def test_ask_question_without_event(client: TestClient):
    """Test asking a question without an event context."""
    # Mock the AI service
    with mock.patch("app.api.v1.ai_assistant.get_ai_response") as mock_get_ai:
        mock_get_ai.return_value = "This is a test response."
        
        response = client.post(
            "/api/v1/ai/ask",
            json={"question": "What is endurance riding?"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "This is a test response."
        assert data["success"] is True


@pytest.mark.asyncio
async def test_ask_question_with_event(client: TestClient, db_session: AsyncSession):
    """Test asking a question with an event context."""
    # Create a test event
    event = EventCreate(
        name="Test Ride",
        location="Test Location",
        date_start=datetime.now(),
        region="Pacific Northwest",
        description="A test ride for testing"
    )
    
    db_event = await create_event(db_session, event)
    
    # Mock the AI service
    with mock.patch("app.api.v1.ai_assistant.get_ai_response") as mock_get_ai:
        mock_get_ai.return_value = "This ride requires hoof protection."
        
        response = client.post(
            "/api/v1/ai/ask",
            json={
                "question": "Do I need hoof protection for this ride?",
                "event_id": db_event.id
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "This ride requires hoof protection."
        assert data["success"] is True
        
        # Check if the event context was passed to the AI service
        args, kwargs = mock_get_ai.call_args
        assert "event_context" in kwargs
        assert kwargs["event_context"]["name"] == "Test Ride"


@pytest.mark.asyncio
async def test_ask_question_invalid_event(client: TestClient):
    """Test asking a question with an invalid event ID."""
    response = client.post(
        "/api/v1/ai/ask",
        json={
            "question": "Do I need hoof protection for this ride?",
            "event_id": 9999  # Non-existent ID
        }
    )
    
    assert response.status_code == 200  # Should still work, just without context
    data = response.json()
    assert "answer" in data
    assert data["success"] is True
