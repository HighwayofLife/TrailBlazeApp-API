#!/usr/bin/env python
import asyncio
import sys
import logging
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    # Use the same connection string as in the app
    database_url = "postgresql+asyncpg://postgres:postgres@db/trailblaze"
    
    # Create engine and session
    engine = create_async_engine(database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Check connection
        result = await session.execute(text("SELECT 1 as test"))
        row = result.first()
        print(f"Database connection test: {row.test if row else 'Failed'}")
        
        # Get table structure for events
        result = await session.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'events'
            ORDER BY ordinal_position
        """))
        columns = result.fetchall()
        
        print("\nEvents table structure:")
        print("=======================")
        for col in columns:
            print(f"{col[0]}: {col[1]}")
        
        # Check for specific field
        result = await session.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'events' AND column_name = 'geocoding_attempted'
        """))
        geocoding_field = result.first()
        print(f"\nGeocoding attempted field exists: {bool(geocoding_field)}")
        
        # Count events
        result = await session.execute(text("SELECT COUNT(*) FROM events"))
        count = result.scalar()
        print(f"\nTotal events in database: {count}")
        
        # Get a sample event
        if count > 0:
            result = await session.execute(text("SELECT * FROM events LIMIT 1"))
            event = result.mappings().first()
            print("\nSample event:")
            print("=============")
            for key, value in dict(event).items():
                print(f"{key}: {value}")

if __name__ == "__main__":
    asyncio.run(main()) 