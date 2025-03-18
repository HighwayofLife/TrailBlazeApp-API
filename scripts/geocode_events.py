#!/usr/bin/env python
"""
Script to geocode existing events in the database.

This script adds latitude and longitude coordinates to events 
that don't have them by using the geocoding enrichment service.

Usage:
    # Process just 3 events (default for testing)
    docker-compose run --rm api python -m scripts.geocode_events
    
    # Process a specific number of events
    docker-compose run --rm api python -m scripts.geocode_events --limit 10
    
    # Process all events that need geocoding
    docker-compose run --rm api python -m scripts.geocode_events --all
    
    # Use simplified geocoding approach
    docker-compose run --rm api python -m scripts.geocode_events --simple
"""

import asyncio
import argparse
import logging
import sys
import re
from typing import List, Optional, Tuple

import sqlalchemy as sa
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
import aiohttp

from app.database import async_session
from app.models import Event
from app.services.enrichment import GeocodingEnrichmentService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("geocode_events")

async def geocode_address_simple(address: str) -> Optional[Tuple[float, float]]:
    """
    Simplified geocoding function using OpenStreetMap Nominatim API directly.
    
    Args:
        address: The address to geocode
        
    Returns:
        Tuple of (latitude, longitude) or None if geocoding failed
    """
    if not address:
        logger.warning("Empty address provided for geocoding")
        return None
        
    # Clean up the address
    address = re.sub(r'\s+', ' ', address).strip()
    
    # Remove anything in parentheses
    address = re.sub(r'\([^)]*\)', '', address)
    
    # Extract the most likely address part if there's a dash or comma
    if " - " in address:
        parts = address.split(" - ")
        for part in parts:
            if re.search(r'\d+|\brd\b|\bst\b|\bave\b|\bhwy\b|\broute\b|\bcounty\b|\bpark\b', part, re.IGNORECASE):
                address = part.strip()
                break
    
    logger.info(f"Simple geocoding address: {address}")
    
    # Extract city and state information
    # Common US state abbreviations pattern
    us_state_pattern = r'(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY)'
    
    # Try to find city and state information
    city_state_match = re.search(r'([A-Za-z\s]+),?\s+' + us_state_pattern, address)
    
    # Create different address variations to try
    address_variations = [address]
    
    # Add city, state variation if found
    if city_state_match:
        city = city_state_match.group(1).strip()
        state = city_state_match.group(2)
        city_state = f"{city}, {state}, USA"
        address_variations.append(city_state)
        
        # Also add just the city name
        if city:
            address_variations.append(f"{city}, USA")
    
    # Extract just location names (non-numeric parts) as fallback
    location_names = re.findall(r'([A-Za-z\s]{3,})', address)
    for name in location_names:
        name = name.strip()
        if name and len(name) > 3 and name.lower() not in ['road', 'street', 'avenue', 'drive', 'lane', 'blvd', 'highway', 'north', 'south', 'east', 'west', 'limited', 'entries', 'ride', 'intro', 'each', 'day']:
            address_variations.append(name)
    
    # Add the specific locations by name if we can identify them
    if any(park in address.lower() for park in ['park', 'forest', 'mountain', 'trail', 'ranch']):
        park_names = re.findall(r'([A-Za-z\s]{3,}(?:Park|Forest|Mountain|Trail|Ranch))', address, re.IGNORECASE)
        for park in park_names:
            address_variations.append(park.strip())
    
    # Try each address variation
    for i, addr_var in enumerate(address_variations):
        if i > 0:
            logger.info(f"Trying address variation {i}: {addr_var}")
        
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    'q': addr_var,
                    'format': 'json',
                    'limit': 1,
                    'addressdetails': 1
                }
                headers = {
                    'User-Agent': 'TrailBlazeApp/1.0'
                }
                async with session.get('https://nominatim.openstreetmap.org/search', params=params, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and isinstance(data, list) and len(data) > 0:
                            lat = float(data[0]['lat'])
                            lon = float(data[0]['lon'])
                            logger.info(f"Successfully geocoded '{addr_var}' to: {lat}, {lon}")
                            return (lat, lon)
                        else:
                            logger.warning(f"No results found for address variation: {addr_var}")
                    else:
                        logger.error(f"Error geocoding address, status code: {response.status}")
                
                # Add a small delay to avoid rate limiting
                await asyncio.sleep(0.5)
                
        except Exception as e:
            logger.exception(f"Exception during simple geocoding: {str(e)}")
    
    # If we're here, all geocoding attempts failed
    return None

async def geocode_events(batch_size: int = 50, limit: Optional[int] = 3, simple_mode: bool = False) -> None:
    """
    Process events that don't have coordinates and geocode them.
    
    Args:
        batch_size: Number of events to process in each batch
        limit: Optional limit on total number of events to process.
              Defaults to 3 for initial testing. Set to None to process all events.
        simple_mode: Whether to use simplified geocoding approach
    """
    total_processed = 0
    total_geocoded = 0
    
    # Only create the service if we're not in simple mode
    service = None if simple_mode else GeocodingEnrichmentService()
    
    async with async_session() as session:
        # Get total count of events without coordinates
        query = select(sa.func.count()).select_from(Event).where(
            (Event.latitude.is_(None)) | (Event.longitude.is_(None))
        )
        result = await session.execute(query)
        total_events = result.scalar_one()
        
        if total_events == 0:
            logger.info("No events found that need geocoding.")
            return
        
        logger.info(f"Found {total_events} events without coordinates.")
        
        # Apply limit if specified
        if limit is not None:
            total_events = min(total_events, limit)
            logger.info(f"Will process up to {total_events} events due to limit.")
        
        # Process events in batches
        offset = 0
        while offset < total_events:
            # Determine batch size
            current_batch_size = min(batch_size, total_events - offset)
            
            # Query events without coordinates
            query = select(Event).where(
                (Event.latitude.is_(None)) | (Event.longitude.is_(None))
            ).offset(offset).limit(current_batch_size)
            
            result = await session.execute(query)
            events = result.scalars().all()
            
            if not events:
                break
                
            logger.info(f"Processing batch of {len(events)} events (offset: {offset})")
            
            # Process each event in the batch
            for i, event in enumerate(events):
                logger.info(f"Geocoding event {i+1}/{len(events)}: {event.name} - {event.location}")
                
                success = False
                if simple_mode:
                    # Use the simple geocoding method
                    if event.location:
                        coordinates = await geocode_address_simple(event.location)
                        if coordinates:
                            event.latitude, event.longitude = coordinates
                            success = True
                else:
                    # Use the full geocoding service
                    success = await service.enrich_event(event)
                
                total_processed += 1
                
                if success:
                    total_geocoded += 1
                    logger.info(f"Successfully geocoded: {event.name} - ({event.latitude}, {event.longitude})")
                else:
                    logger.warning(f"Failed to geocode: {event.name} - {event.location}")
            
            # Commit the batch
            await session.commit()
            logger.info(f"Committed batch of {len(events)} events")
            
            # Update offset for next batch
            offset += current_batch_size
    
    # Print summary
    logger.info(f"Geocoding complete. Processed {total_processed} events, successfully geocoded {total_geocoded}.")
    if total_processed > 0:
        logger.info(f"Success rate: {total_geocoded / total_processed * 100:.2f}% ({total_geocoded}/{total_processed})")

async def main():
    """Entry point for the script."""
    logger.info("Starting event geocoding process")
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Geocode events in the database')
    parser.add_argument('--limit', type=int, help='Maximum number of events to process (default: 3)')
    parser.add_argument('--all', action='store_true', help='Process all events that need geocoding')
    parser.add_argument('--batch-size', type=int, default=50, help='Batch size for processing (default: 50)')
    parser.add_argument('--simple', action='store_true', help='Use simplified geocoding approach')
    args = parser.parse_args()
    
    # Determine limit
    limit = None if args.all else (args.limit if args.limit is not None else 3)
    
    try:
        await geocode_events(batch_size=args.batch_size, limit=limit, simple_mode=args.simple)
        logger.info("Event geocoding completed successfully")
    except Exception as e:
        logger.exception(f"Error during geocoding: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 