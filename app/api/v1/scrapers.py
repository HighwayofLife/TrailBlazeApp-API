from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database import get_db
from app.schemas.scraper import ScraperResponse, ScraperRun
from app.services.scraper_service import run_scraper
from app.logging_config import get_logger

router = APIRouter()
logger = get_logger("api.scrapers")


@router.get("/", response_model=List[ScraperResponse])
async def list_scrapers():
    """
    List all available scrapers.
    """
    try:
        scrapers = [
            {"id": "pner", "name": "PNER Website", "status": "active"},
            {"id": "aerc", "name": "AERC Calendar", "status": "active"},
            {"id": "facebook", "name": "Facebook Events", "status": "active"},
            # Add more scrapers as needed
        ]
        return scrapers
    except Exception as e:
        logger.error(f"Error listing scrapers: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/run", response_model=ScraperRun)
async def trigger_scraper(
    scraper_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger a scraper to run in the background.
    """
    try:
        # Validate scraper ID
        valid_scrapers = ["pner", "aerc", "facebook"]
        if scraper_id not in valid_scrapers:
            raise HTTPException(status_code=400, detail="Invalid scraper ID")
        
        # Run the scraper in the background
        background_tasks.add_task(run_scraper, scraper_id, db)
        
        return {
            "scraper_id": scraper_id,
            "status": "running",
            "message": f"Scraper '{scraper_id}' started successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering scraper {scraper_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to start scraper")
