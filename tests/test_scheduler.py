"""Tests for the scheduler module."""

import pytest
import asyncio
from datetime import datetime, timedelta
from scrapers.scheduler import ScraperScheduler

async def dummy_scraper(**kwargs):
    """Dummy scraper function for testing."""
    return kwargs

@pytest.fixture
async def scheduler():
    """Fixture providing a scheduler instance."""
    scheduler = ScraperScheduler()
    yield scheduler
    scheduler.shutdown()

@pytest.mark.asyncio
async def test_scheduler_start_stop(scheduler):
    """Test starting and stopping the scheduler."""
    assert not scheduler.running
    scheduler.start()
    assert scheduler.running
    scheduler.shutdown()
    assert not scheduler.running

@pytest.mark.asyncio
async def test_schedule_job(scheduler):
    """Test scheduling a job."""
    scheduler.start()
    job = scheduler.schedule_scraper(
        dummy_scraper,
        "test_job",
        "*/5 * * * *",  # Every 5 minutes
        test_arg="value"
    )
    
    assert job is not None
    assert job.id == "test_job"
    assert job.kwargs == {"test_arg": "value"}
    
    # Verify job is retrievable
    retrieved_job = scheduler.get_job("test_job")
    assert retrieved_job is not None
    assert retrieved_job.id == "test_job"

@pytest.mark.asyncio
async def test_remove_job(scheduler):
    """Test removing a scheduled job."""
    scheduler.start()
    job = scheduler.schedule_scraper(
        dummy_scraper,
        "test_job",
        "*/5 * * * *"
    )
    
    assert scheduler.get_job("test_job") is not None
    scheduler.remove_job("test_job")
    assert scheduler.get_job("test_job") is None

@pytest.mark.asyncio
async def test_modify_job(scheduler):
    """Test modifying a job's schedule and arguments."""
    scheduler.start()
    job = scheduler.schedule_scraper(
        dummy_scraper,
        "test_job",
        "0 0 * * *",
        arg1="old"
    )
    
    modified_job = scheduler.modify_job(
        "test_job",
        cron="*/10 * * * *",  # Every 10 minutes
        arg1="new",
        arg2="added"
    )
    
    assert modified_job is not None
    assert modified_job.kwargs == {"arg1": "new", "arg2": "added"}

@pytest.mark.asyncio
async def test_run_job_now(scheduler):
    """Test running a job immediately."""
    scheduler.start()
    test_args = {"test_arg": "value"}
    
    scheduler.schedule_scraper(
        dummy_scraper,
        "test_job",
        "0 0 * * *",
        **test_args
    )
    
    await scheduler.run_job_now("test_job")

@pytest.mark.asyncio
async def test_get_jobs(scheduler):
    """Test getting all scheduled jobs."""
    scheduler.start()
    
    # Schedule multiple jobs
    job1 = scheduler.schedule_scraper(
        dummy_scraper,
        "job1",
        "0 0 * * *"
    )
    job2 = scheduler.schedule_scraper(
        dummy_scraper,
        "job2",
        "0 12 * * *"
    )
    
    jobs = scheduler.get_jobs()
    assert len(jobs) == 2
    job_ids = {job.id for job in jobs}
    assert job_ids == {"job1", "job2"}

@pytest.mark.asyncio
async def test_invalid_job_id(scheduler):
    """Test operations with invalid job IDs."""
    scheduler.start()
    
    with pytest.raises(ValueError):
        await scheduler.run_job_now("nonexistent_job")
    
    assert scheduler.modify_job("nonexistent_job") is None