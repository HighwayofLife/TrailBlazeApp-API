#!/usr/bin/env python
"""
Script to check the event data stored in the database.
"""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import json

async def main():
    """Check event data in production database."""
    # Define database URL for the production database
    database_url = "postgresql+asyncpg://postgres:postgres@db/trailblaze"
    
    # Create engine and session
    engine = create_async_engine(database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Check connection
        result = await session.execute(text("SELECT 1 as test"))
        row = result.first()
        print(f"Database connection test: {row.test if row else 'Failed'}")
        
        # Check events count
        result = await session.execute(text("SELECT COUNT(*) FROM events"))
        count = result.scalar()
        print(f"\nTotal events in database: {count}")
        
        # Get fields with null and non-null counts
        print("\nField non-null counts:")
        print("=====================")
        
        # Get column names
        result = await session.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'events'
            ORDER BY ordinal_position
        """))
        columns = [row[0] for row in result.fetchall()]
        
        # Count non-null values for each column
        for column in columns:
            result = await session.execute(text(f"""
                SELECT COUNT(*) 
                FROM events 
                WHERE {column} IS NOT NULL
            """))
            non_null_count = result.scalar()
            percentage = (non_null_count / count) * 100 if count > 0 else 0
            print(f"{column}: {non_null_count}/{count} ({percentage:.1f}%)")
        
        # Sample events for inspection
        print("\nSample events (first 3):")
        print("=====================")
        result = await session.execute(text("""
            SELECT id, name, location, date_start, region, event_details
            FROM events 
            LIMIT 3
        """))
        samples = result.fetchall()
        for i, (id, name, location, date_start, region, event_details) in enumerate(samples):
            print(f"\nEvent {i+1}:")
            print(f"ID: {id}")
            print(f"Name: {name}")
            print(f"Location: {location}")
            print(f"Date: {date_start}")
            print(f"Region: {region}")
            print(f"Details: {json.dumps(event_details, indent=2, default=str) if event_details else 'None'}")
            
            # If we have event_details, analyze its structure
            if event_details:
                print("Event details keys:")
                for key in event_details.keys():
                    print(f"  - {key}")
        
        # Check location and location_details
        print("\nLocation details check:")
        print("=====================")
        result = await session.execute(text("""
            SELECT id, name, location, event_details
            FROM events 
            WHERE event_details IS NOT NULL
            LIMIT 5
        """))
        location_samples = result.fetchall()
        for id, name, location, event_details in location_samples:
            print(f"\nEvent ID: {id}")
            print(f"Name: {name}")
            print(f"Location field: {location}")
            
            # Extract location_details if available
            location_details = event_details.get('location_details') if event_details else None
            print(f"Location details: {json.dumps(location_details, indent=2, default=str) if location_details else 'None'}")
            
            # Check for specific fields in event_details
            fields_to_check = ['has_intro_ride', 'is_multi_day_event', 'is_pioneer_ride', 'ride_days']
            for field in fields_to_check:
                value = event_details.get(field, 'Not present')
                print(f"{field}: {value}")

if __name__ == "__main__":
    asyncio.run(main()) 