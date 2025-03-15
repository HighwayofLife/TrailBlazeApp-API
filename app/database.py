import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from datetime import datetime, timedelta
import logging

from app.config import get_settings

settings = get_settings()

# Create async engine for the database
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
)

# Create sessionmaker
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Base model class
Base = declarative_base()

async def get_db() -> AsyncSession:
    """Get a database session.
    
    Yields:
        AsyncSession: Database session
    """
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def create_db_and_tables():
    """Create database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def init_db():
    try:
        # Create a test connection to verify database is accessible
        async with engine.begin() as conn:
            # Import models and drop all tables if they exist
            from .models import Base  # Import Base from models package
            from .models.event import Event  # Import Event model specifically
            await conn.run_sync(Base.metadata.drop_all)
            # Create tables
            await conn.run_sync(Base.metadata.create_all)
            logging.info("Database connection successful and tables created")
            
        # Add sample data for testing
        await populate_sample_data()
    except Exception as e:
        logging.error(f"Database connection failed: {e}")
        logging.error(f"Using connection string (without password): postgresql+asyncpg://{DB_USER}:***@{DB_HOST}:{DB_PORT}/{DB_NAME}")
        logging.error("Please ensure PostgreSQL is running and accessible")
        raise

async def populate_sample_data():
    from .models.event import Event  # Import here to avoid circular imports
    
    async with async_session() as session:
        # Check if we already have events to avoid duplicates
        result = await session.execute(text("SELECT COUNT(*) FROM events"))
        count = result.scalar()
        
        if count == 0:
            logging.info("Adding sample events to database")
            now = datetime.now()
            
            sample_events = [
                Event(
                    name="Trail Cleanup Day",
                    description="Join us for our monthly trail cleanup event!",
                    location_name="Mountain View Park",
                    address="123 Mountain View Rd",
                    city="Boulder",
                    state="CO",
                    country="USA",
                    start_date=now + timedelta(days=7),
                    end_date=now + timedelta(days=7, hours=3),
                    organization="PNER",
                    is_verified=True,
                    distances=[25, 50]
                ),
                Event(
                    name="Night Hike Adventure",
                    description="Experience the trails under the stars with our guided night hike.",
                    location_name="Cedar Ridge Trail",
                    address="456 Cedar Ridge Blvd",
                    city="Bend",
                    state="OR",
                    country="USA",
                    start_date=now + timedelta(days=14, hours=20),
                    end_date=now + timedelta(days=14, hours=22),
                    organization="AERC",
                    is_verified=True,
                    distances=[100]
                ),
                Event(
                    name="Mountain Biking Workshop",
                    description="Learn mountain biking skills for all levels.",
                    location_name="Rockville Bike Park",
                    address="789 Rockville Pike",
                    city="Moab",
                    state="UT",
                    country="USA",
                    start_date=now + timedelta(days=21, hours=10),
                    end_date=now + timedelta(days=21, hours=16),
                    organization="EDRA",
                    is_verified=False,
                    distances=[25, 50, 75]
                ),
            ]
            
            session.add_all(sample_events)
            await session.commit()
            logging.info(f"Added {len(sample_events)} sample events to database")
