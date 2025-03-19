"""
Scraper schema definitions for TrailBlazeApp API.
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict


class ScraperResponse(BaseModel):
    """Schema for scraper info response."""
    id: str
    name: str
    status: str

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "aerc_scraper",
                "name": "AERC Scraper",
                "status": "idle"
            }
        }
    )


class ScraperRun(BaseModel):
    """Schema for scraper run response."""
    scraper_id: str
    status: str
    message: str

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "scraper_id": "aerc_scraper",
                "status": "success",
                "message": "Scraper completed successfully"
            }
        }
    )
