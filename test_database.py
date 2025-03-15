import asyncio
import sys
import time
import subprocess
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# Configuration
DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost/trailblaze"
MAX_RETRIES = 5
RETRY_DELAY = 3  # seconds

def check_docker_status():
    """Check if the database container is running."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=trailblaze_db", "--format", "{{.Status}}"],
            capture_output=True,
            text=True
        )
        
        if "Up" in result.stdout:
            print("✅ PostgreSQL container is running")
            return True
        else:
            print("❌ PostgreSQL container is not running")
            return False
    except Exception as e:
        print(f"❌ Error checking Docker status: {e}")
        return False

async def test_database_connection():
    """Test database connectivity and basic operations."""
    print(f"Testing database connection to {DATABASE_URL}...")
    
    engine = create_async_engine(DATABASE_URL)
    
    for attempt in range(MAX_RETRIES):
        try:
            print(f"Connection attempt {attempt+1}/{MAX_RETRIES}...")
            async with engine.connect() as conn:
                # Test simple query
                result = await conn.execute(text("SELECT 1 as test"))
                row = result.first()
                
                if row and row.test == 1:
                    print("✓ Successfully connected to the database!")
                    print("✓ Test query executed successfully!")
                    return True
                else:
                    print("✗ Connection succeeded but test query failed.")
        except Exception as e:
            print(f"✗ Connection attempt {attempt+1} failed: {str(e)}")
            if attempt < MAX_RETRIES - 1:
                print(f"Retrying in {RETRY_DELAY} seconds...")
                await asyncio.sleep(RETRY_DELAY)
    
    print("✗ Failed to connect to the database after maximum retries.")
    return False

async def main():
    if not check_docker_status():
        print("Database container is not running. Please start it with docker-compose up -d")
        return 1
        
    result = await test_database_connection()
    return 0 if result else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
