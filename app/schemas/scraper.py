from typing import Optional
from pydantic import BaseModel


class ScraperResponse(BaseModel):
    """Schema for scraper info response."""
    id: str
    name: str
    status: str


class ScraperRun(BaseModel):
    """Schema for scraper run response."""
    scraper_id: str
    status: str
    message: str
