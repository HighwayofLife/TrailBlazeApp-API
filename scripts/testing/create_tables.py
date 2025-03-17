#!/usr/bin/env python3
"""
Create tables in the test database.

This script creates all necessary tables in the test database
using the SQLAlchemy models defined in the application.
"""
import asyncio
import logging
import inspect

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the correct Base and models
from app.models.base import Base
from app.models.event import Event, Announcement
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Log model information
logger.info(f"Imported Event model: {Event}")
logger.info(f"Imported Announcement model: {Announcement}")

# Check if the models are properly registered with Base
logger.info(f"Base metadata tables: {list(Base.metadata.tables.keys())}")
logger.info(f"Event table name: {Event.__tablename__}")
logger.info(f"Announcement table name: {Announcement.__tablename__}")

async def create_tables():
    """Create all tables in the test database."""
    logger.info("Starting table creation...")
    
    engine = create_async_engine(
        'postgresql+asyncpg://postgres:postgres@test-db/test_trailblaze',
        echo=True  # Enable SQL logging
    )
    
    try:
        async with engine.begin() as conn:
            # First check if we can connect
            result = await conn.execute(text("SELECT 1"))
            logger.info(f"Database connection test: {result.scalar()}")
            
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            
            # Verify tables were created
            result = await conn.execute(
                text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
            )
            tables = [row[0] for row in result.fetchall()]
            logger.info(f"Tables in database: {tables}")
            
            if not tables:
                logger.error("No tables were created!")
            else:
                logger.info("Tables created successfully")
    except Exception as e:
        logger.error(f"Error creating tables: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(create_tables()) 