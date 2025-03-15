import asyncio
import sys
import logging
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# Configuration
MAX_RETRIES = 5
RETRY_DELAY = 3  # seconds

def get_database_url() -> str:
    """Get the appropriate database URL based on environment."""
    return os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost/trailblaze"
    )

async def test_database_connection() -> bool:
    """Test database connectivity and basic operations."""
    database_url = get_database_url()
    print(f"Testing database connection to {database_url}...")
    
    engine = create_async_engine(database_url)
    
    for attempt in range(MAX_RETRIES):
        try:
            print(f"Connection attempt {attempt+1}/{MAX_RETRIES}...")
            async with engine.connect() as conn:
                # Test simple query
                result = await conn.execute(text("SELECT 1 as test"))
                row = result.first()
                
                if row and row.test == 1:
                    print("✅ Successfully connected to the database!")
                    print("✅ Test query executed successfully!")
                    return True
                else:
                    print("❌ Connection succeeded but test query failed.")
        except Exception as e:
            print(f"❌ Connection attempt {attempt+1} failed: {str(e)}")
            if attempt < MAX_RETRIES - 1:
                print(f"Retrying in {RETRY_DELAY} seconds...")
                await asyncio.sleep(RETRY_DELAY)
            else:
                print("\nTROUBLESHOOTING TIPS:")
                print("1. Check if DATABASE_URL environment variable is set correctly")
                print("   Current value:", database_url)
                print("2. If using Docker, ensure you're using the service name 'db'")
                print("   Example: postgresql+asyncpg://postgres:postgres@db/trailblaze")
                print("3. If running locally, make sure PostgreSQL is running on port 5432")
    
    return False

async def main():
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Test database connection
    result = await test_database_connection()
    return 0 if result else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
