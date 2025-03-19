#!/usr/bin/env python
"""
Script to check the latest events in the database.
"""
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import json

async def main():
    """Check latest events in production database."""
    # Define database URL for the production database
    database_url = "postgresql+asyncpg://postgres:postgres@db/trailblaze"
    
    # Create engine and session
    engine = create_async_engine(database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Check connection
        from sqlalchemy import text
        result = await session.execute(text("SELECT 1 as test"))
        row = result.first()
        print(f"Database connection test: {row.test if row else 'Failed'}")
        
        # Get the Event model
        from app.models.event import Event
        
        # Get the latest 10 events
        query = select(Event).order_by(Event.created_at.desc()).limit(10)
        result = await session.execute(query)
        events = result.scalars().all()
        
        # Display event information
        for i, event in enumerate(events):
            print(f"\nEvent {i+1}:")
            print(f"ID: {event.id}")
            print(f"Name: {event.name}")
            print(f"Location: {event.location}")
            print(f"Date: {event.date_start}")
            print(f"Region: {event.region}")
            
            # Check location details in event_details
            location_details = event.event_details.get('location_details') if event.event_details else None
            print(f"Location details: {json.dumps(location_details, indent=2, default=str) if location_details else 'None'}")
            
            # Check has_intro_ride
            has_intro_ride = event.has_intro_ride
            has_intro_ride_in_details = event.event_details.get('has_intro_ride') if event.event_details else None
            print(f"has_intro_ride (field): {has_intro_ride}")
            print(f"has_intro_ride (details): {has_intro_ride_in_details}")
            
            # Check is_multi_day_event and is_pioneer_ride
            is_multi_day = event.event_details.get('is_multi_day_event') if event.event_details else None
            is_pioneer = event.event_details.get('is_pioneer_ride') if event.event_details else None
            print(f"is_multi_day_event: {is_multi_day}")
            print(f"is_pioneer_ride: {is_pioneer}")
            
            print(f"ride_id: {event.ride_id}")
            print("-" * 50)

if __name__ == "__main__":
    asyncio.run(main()) 