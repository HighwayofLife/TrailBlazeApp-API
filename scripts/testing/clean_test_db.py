#!/usr/bin/env python3
"""
Clean the test database by truncating all tables.

This script connects to the test database and truncates all tables
to ensure a clean state for running tests.
"""
import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the correct Base and models
from app.models.base import Base
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

async def clean_test_db():
    """Clean the test database by truncating all tables."""
    logger.info("Starting test database cleanup...")
    
    engine = create_async_engine(
        'postgresql+asyncpg://postgres:postgres@test-db/test_trailblaze',
        echo=True  # Enable SQL logging
    )
    
    try:
        async with engine.begin() as conn:
            # First check if we can connect
            result = await conn.execute(text("SELECT 1"))
            logger.info(f"Database connection test: {result.scalar()}")
            
            # Get list of all tables
            result = await conn.execute(
                text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
            )
            tables = [row[0] for row in result.fetchall()]
            logger.info(f"Tables in database: {tables}")
            
            if not tables:
                logger.info("No tables found to clean")
            else:
                # Disable foreign key constraints temporarily
                await conn.execute(text("SET session_replication_role = 'replica';"))
                
                # Truncate all tables
                for table in tables:
                    await conn.execute(text(f'TRUNCATE TABLE "{table}" CASCADE;'))
                
                # Re-enable foreign key constraints
                await conn.execute(text("SET session_replication_role = 'origin';"))
                
                logger.info("All tables truncated successfully")
    except Exception as e:
        logger.error(f"Error cleaning test database: {str(e)}")
        raise
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(clean_test_db()) 