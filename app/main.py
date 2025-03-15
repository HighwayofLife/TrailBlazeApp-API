import logging.config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import get_settings
from app.logging_config import configure_logging
from app.middleware import RequestLoggingMiddleware
from app.database import create_db_and_tables

# Configure logging
logging.config.dictConfig(configure_logging())
logger = logging.getLogger("app.main")

# Get settings
settings = get_settings()

# Initialize FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    debug=settings.DEBUG,
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.add_middleware(RequestLoggingMiddleware)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.on_event("startup")
async def on_startup():
    """Startup tasks for the application."""
    logger.info("Starting TrailBlaze API")
    await create_db_and_tables()


@app.on_event("shutdown")
async def on_shutdown():
    """Shutdown tasks for the application."""
    logger.info("Shutting down TrailBlaze API")


@app.get("/", tags=["Health"])
async def health_check():
    """Root endpoint for health checks."""
    return {"status": "healthy", "message": "TrailBlaze API is running"}


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
