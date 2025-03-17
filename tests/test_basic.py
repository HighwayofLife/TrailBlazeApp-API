import pytest
from fastapi.testclient import TestClient
from app.main import app

def test_app_exists():
    """Test that our FastAPI app exists."""
    assert app is not None

def test_app_has_title():
    """Test that our FastAPI app has a title."""
    assert app.title == "TrailBlaze API" 