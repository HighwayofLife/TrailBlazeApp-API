"""
Common fixtures for AERC scraper tests.

This file provides pytest fixtures that can be shared across test files.
"""

import sys
import pytest
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

# Add project root to path
project_root = str(Path(__file__).parents[3])
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import required components
from scrapers.aerc_scraper.parser_v2.html_parser import HTMLParser
from scrapers.aerc_scraper.data_handler import DataHandler
from scrapers.aerc_scraper.database import DatabaseHandler
from app.models.event import Event as DBEvent

# Path to HTML samples
HTML_SAMPLES_DIR = Path(__file__).parent / "html_samples"

def load_html_sample(filename: str) -> str:
    """Load HTML sample from a file."""
    file_path = HTML_SAMPLES_DIR / filename
    if not file_path.exists():
        raise FileNotFoundError(f"Sample file not found: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

@pytest.fixture
def parser():
    """Return an instance of the HTML parser."""
    return HTMLParser(debug_mode=True)

@pytest.fixture
def data_handler():
    """Return an instance of the data handler."""
    return DataHandler()

@pytest.fixture
def db_handler():
    """Return an instance of the database handler."""
    return DatabaseHandler()

@pytest.fixture
def mock_db():
    """Create a mock database."""
    mock_db = AsyncMock(spec=AsyncSession)
    
    # Add execute method to mock database
    async def mock_execute(query):
        mock_result = AsyncMock()
        mock_result.scalar.return_value = 1
        mock_result.all.return_value = []
        return mock_result
    
    mock_db.execute = mock_execute
    mock_db.commit = AsyncMock()
    
    return mock_db

@pytest.fixture
def stored_events():
    """Track events that get stored in the database."""
    return {}

@pytest.fixture
def mock_existing_event():
    """Create a mock existing event."""
    mock_existing = MagicMock(spec=DBEvent)
    mock_existing.id = 999
    mock_existing.name = "Original Old Pueblo"  # Match sample name
    mock_existing.location = "Tucson, AZ"
    mock_existing.is_canceled = False
    return mock_existing 