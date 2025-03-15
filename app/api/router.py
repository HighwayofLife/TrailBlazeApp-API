from fastapi import APIRouter

from app.api.v1 import events, ai_assistant, scrapers

# Initialize API router
api_router = APIRouter()

# Include routers from different modules
api_router.include_router(events.router, prefix="/events", tags=["Events"])
api_router.include_router(ai_assistant.router, prefix="/ai", tags=["AI Assistant"])
api_router.include_router(scrapers.router, prefix="/scrapers", tags=["Scrapers"])
