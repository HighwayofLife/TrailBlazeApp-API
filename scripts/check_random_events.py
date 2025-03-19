#!/usr/bin/env python
"""
Script to check random events in the database.
"""
import asyncio
import json
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

async def check_events():
    # Define database URL
    database_url = "postgresql+asyncpg://postgres:postgres@db/trailblaze"
    
    # Create engine and session
    engine = create_async_engine(database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Get the Event model
        from app.models.event import Event
        
        # Get 10 random events with all their data
        query = select(Event).order_by(func.random()).limit(10)
        result = await session.execute(query)
        events = result.scalars().all()
        
        for event in events:
            print(f'\nEvent ID: {event.id}')
            print(f'Name: {event.name}')
            print(f'Ride ID: {event.ride_id}')
            print(f'Distances: {event.distances}')
            print(f'Ride Manager: {event.ride_manager}')
            print(f'Location: {event.location}')
            print(f'Date: {event.date_start} to {event.date_end}')
            
            # Access event_details JSON field
            event_details = event.event_details or {}
            is_multi_day = event_details.get('is_multi_day_event', False)
            is_pioneer = event_details.get('is_pioneer_ride', False)
            ride_days = event_details.get('ride_days', 1)
            
            print(f'Multi-day: {is_multi_day}')
            print(f'Pioneer: {is_pioneer}')
            print(f'Ride Days: {ride_days}')
            
            print(f'Description: {event.description[:100]}...' if event.description and len(event.description) > 100 else event.description)
            print(f'Directions: {event.directions[:100]}...' if event.directions and len(event.directions) > 100 else event.directions)
            print(f'Judges: {event.judges}')
            
            # Get contact info from event_details
            contact_info = event_details.get('ride_manager_contact', {})
            print(f'Contact Info: {json.dumps(contact_info, indent=2, default=str)}')
            
            # Check for structured distances in event_details
            structured_distances = event_details.get('distances', [])
            if structured_distances:
                print(f'Structured Distances: {json.dumps(structured_distances, indent=2, default=str)}')

if __name__ == "__main__":
    asyncio.run(check_events()) 