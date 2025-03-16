"""
Metrics collection for AERC scraper performance monitoring.
"""

import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import json
import os
import logging
import psutil

logger = logging.getLogger(__name__)

@dataclass
class ScraperMetrics:
    start_time: datetime
    end_time: Optional[datetime] = None
    http_requests: int = 0
    http_errors: int = 0
    request_retries: int = 0
    events_found: int = 0
    events_valid: int = 0
    events_added: int = 0
    events_updated: int = 0
    events_skipped: int = 0
    calendar_rows_found: int = 0
    validation_errors: int = 0
    gemini_calls: int = 0
    gemini_errors: int = 0
    fallback_used: bool = False
    memory_samples: List[Dict[str, float]] = None
    
    def __post_init__(self):
        self.memory_samples = []
    
    def sample_memory(self) -> Dict[str, float]:
        """Take a sample of current memory usage."""
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        sample = {
            'timestamp': datetime.now().isoformat(),
            'rss': memory_info.rss / 1024 / 1024,  # RSS in MB
            'vms': memory_info.vms / 1024 / 1024,  # VMS in MB
            'percent': process.memory_percent()
        }
        self.memory_samples.append(sample)
        return sample
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary format."""
        return {
            "scrape_date": self.start_time.isoformat(),
            "duration_seconds": (self.end_time - self.start_time).total_seconds() if self.end_time else None,
            "http_requests": self.http_requests,
            "http_errors": self.http_errors,
            "request_retries": self.request_retries,
            "calendar_rows_found": self.calendar_rows_found,
            "events_found": self.events_found,
            "events_valid": self.events_valid,
            "events_added": self.events_added,
            "events_updated": self.events_updated,
            "events_skipped": self.events_skipped,
            "validation_errors": self.validation_errors,
            "gemini_calls": self.gemini_calls,
            "gemini_errors": self.gemini_errors,
            "fallback_used": self.fallback_used,
            "success_rate": (self.events_valid / self.events_found * 100) if self.events_found > 0 else 0,
            "processing_rate": (self.events_valid / self.calendar_rows_found * 100) if self.calendar_rows_found > 0 else 0,
            "memory_samples": self.memory_samples
        }
    
    def log_summary(self) -> None:
        """Log a summary of the metrics."""
        if not self.end_time:
            self.end_time = datetime.now()
            
        logger.info("Scraper run completed. Metrics summary:")
        logger.info(f"Duration: {(self.end_time - self.start_time).total_seconds():.2f} seconds")
        logger.info(f"Calendar rows found: {self.calendar_rows_found}")
        logger.info(f"Events extracted: {self.events_found}")
        logger.info(f"Valid events: {self.events_valid}")
        logger.info(f"Events added: {self.events_added}")
        logger.info(f"Events updated: {self.events_updated}")
        logger.info(f"Events skipped: {self.events_skipped}")
        logger.info(f"Validation errors: {self.validation_errors}")
        logger.info(f"HTTP requests: {self.http_requests} (errors: {self.http_errors}, retries: {self.request_retries})")
        logger.info(f"Gemini API calls: {self.gemini_calls} (errors: {self.gemini_errors})")
        logger.info(f"Fallback extraction used: {self.fallback_used}")
        
        if self.events_found > 0:
            logger.info(f"Event validation rate: {self.events_valid / self.events_found * 100:.1f}%")
        if self.calendar_rows_found > 0:
            logger.info(f"Calendar processing rate: {self.events_valid / self.calendar_rows_found * 100:.1f}%")
        
        if self.memory_samples:
            peak_memory = max(sample['rss'] for sample in self.memory_samples)
            avg_memory = sum(sample['rss'] for sample in self.memory_samples) / len(self.memory_samples)
            logger.info(f"Peak memory usage: {peak_memory:.2f} MB")
            logger.info(f"Average memory usage: {avg_memory:.2f} MB")
    
    def save_to_file(self, metrics_dir: str = "logs/metrics") -> None:
        """Save metrics to a JSON file."""
        os.makedirs(metrics_dir, exist_ok=True)
        
        filename = f"aerc_scraper_metrics_{self.start_time.strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(metrics_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
        
        logger.info(f"Metrics saved to {filepath}")

def get_metrics_summary(metrics_dir: str = "logs/metrics", days: int = 7) -> Dict[str, Any]:
    """Get a summary of metrics from recent scraper runs."""
    cutoff_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
    
    metrics_files = []
    for filename in os.listdir(metrics_dir):
        if filename.startswith('aerc_scraper_metrics_') and filename.endswith('.json'):
            filepath = os.path.join(metrics_dir, filename)
            if os.path.getctime(filepath) >= cutoff_date:
                with open(filepath) as f:
                    metrics_files.append(json.load(f))
    
    if not metrics_files:
        return {}
    
    # Calculate averages
    total_runs = len(metrics_files)
    avg_metrics = {
        "avg_duration": sum(m["duration_seconds"] for m in metrics_files) / total_runs,
        "avg_events_found": sum(m["events_found"] for m in metrics_files) / total_runs,
        "avg_success_rate": sum(m["success_rate"] for m in metrics_files) / total_runs,
        "total_events_added": sum(m["events_added"] for m in metrics_files),
        "total_events_updated": sum(m["events_updated"] for m in metrics_files),
        "runs_with_errors": sum(1 for m in metrics_files if m["http_errors"] > 0 or m["gemini_errors"] > 0),
        "fallback_usage_rate": sum(1 for m in metrics_files if m["fallback_used"]) / total_runs * 100
    }
    
    return {
        "period_days": days,
        "total_runs": total_runs,
        "last_run": max(m["scrape_date"] for m in metrics_files),
        "metrics": avg_metrics
    }