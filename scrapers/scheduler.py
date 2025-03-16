"""Background job scheduler for periodic tasks."""

import asyncio
from datetime import datetime
from typing import Callable, Optional, Any
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.job import Job

logger = logging.getLogger(__name__)

class ScraperScheduler:
    """Manages scheduled scraping jobs."""
    
    def __init__(self):
        """Initialize the scheduler."""
        self.scheduler = AsyncIOScheduler()
        self._running = False
    
    def start(self):
        """Start the scheduler."""
        if not self._running:
            self.scheduler.start()
            self._running = True
            logger.info("Scheduler started")
    
    def shutdown(self):
        """Shutdown the scheduler."""
        if self._running:
            self.scheduler.shutdown()
            self._running = False
            logger.info("Scheduler shutdown")
    
    def schedule_scraper(
        self,
        scraper_func: Callable,
        name: str,
        cron: str = "0 0 * * *",  # Daily at midnight by default
        **kwargs: Any
    ) -> Job:
        """Schedule a scraper job.
        
        Args:
            scraper_func: Async function to run
            name: Unique name for the job
            cron: Cron expression for scheduling
            **kwargs: Additional arguments to pass to the job
            
        Returns:
            The scheduled job
        """
        trigger = CronTrigger.from_crontab(cron)
        
        job = self.scheduler.add_job(
            scraper_func,
            trigger=trigger,
            id=name,
            name=name,
            kwargs=kwargs,
            replace_existing=True
        )
        
        logger.info(
            f"Scheduled {name} to run {cron}",
            job_id=job.id,
            next_run=job.next_run_time
        )
        
        return job
    
    def remove_job(self, job_id: str) -> None:
        """Remove a scheduled job.
        
        Args:
            job_id: ID of job to remove
        """
        self.scheduler.remove_job(job_id)
        logger.info(f"Removed job {job_id}")
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a scheduled job by ID.
        
        Args:
            job_id: ID of job to get
            
        Returns:
            The job if found, None otherwise
        """
        return self.scheduler.get_job(job_id)
    
    def get_jobs(self) -> list[Job]:
        """Get all scheduled jobs.
        
        Returns:
            List of all scheduled jobs
        """
        return self.scheduler.get_jobs()
    
    def modify_job(
        self,
        job_id: str,
        cron: Optional[str] = None,
        **kwargs: Any
    ) -> Optional[Job]:
        """Modify an existing job's schedule or arguments.
        
        Args:
            job_id: ID of job to modify
            cron: New cron expression (optional)
            **kwargs: New keyword arguments for the job
            
        Returns:
            Modified job if found, None otherwise
        """
        job = self.get_job(job_id)
        if not job:
            return None
            
        if cron:
            trigger = CronTrigger.from_crontab(cron)
            job.reschedule(trigger=trigger)
            
        if kwargs:
            job.modify(kwargs=kwargs)
            
        logger.info(
            f"Modified job {job_id}",
            next_run=job.next_run_time,
            kwargs=kwargs
        )
        
        return job
    
    async def run_job_now(self, job_id: str) -> None:
        """Run a job immediately, outside its schedule.
        
        Args:
            job_id: ID of job to run
            
        Raises:
            ValueError: If job not found
        """
        job = self.get_job(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
            
        await job.func(**job.kwargs)
        logger.info(f"Manually ran job {job_id}")
    
    @property
    def running(self) -> bool:
        """Whether the scheduler is running."""
        return self._running