"""
Metrics collection and reporting module for AERC scraper.
"""

import logging
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
import psutil
import time

logger = logging.getLogger(__name__)

class ScraperMetrics:
    """Collects and reports scraper metrics."""
    
    def __init__(self, start_time: datetime):
        """Initialize metrics collection."""
        self.start_time = start_time
        self.end_time: Optional[datetime] = None
        
        # Core metrics
        self.events_found = 0
        self.events_valid = 0
        self.events_added = 0
        self.events_updated = 0
        self.events_skipped = 0
        self.validation_errors = 0
        
        # Performance metrics
        self.memory_samples = []
        self.last_sample_time = time.time()
        self.sample_interval = 5  # Sample every 5 seconds
        
        # Create metrics directory
        self.metrics_dir = Path("logs/metrics")
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
    
    def update(self, metrics_dict: Dict[str, Any]) -> None:
        """Update metrics from component metrics dictionaries."""
        for key, value in metrics_dict.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        # Take memory sample if interval has passed
        current_time = time.time()
        if current_time - self.last_sample_time >= self.sample_interval:
            self._sample_memory()
            self.last_sample_time = current_time
    
    def _sample_memory(self) -> None:
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
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary format."""
        duration = None
        if self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()
        
        metrics_dict = {
            'timestamp': datetime.now().isoformat(),
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': duration,
            'events': {
                'found': self.events_found,
                'valid': self.events_valid,
                'added': self.events_added,
                'updated': self.events_updated,
                'skipped': self.events_skipped
            },
            'errors': {
                'validation': self.validation_errors
            },
            'performance': {
                'memory_samples': self.memory_samples
            }
        }
        
        if self.events_found > 0:
            metrics_dict['rates'] = {
                'success_rate': (self.events_valid / self.events_found) * 100,
                'events_per_second': self.events_found / duration if duration else 0
            }
        
        return metrics_dict
    
    def log_summary(self) -> None:
        """Log a summary of the metrics."""
        if not self.end_time:
            self.end_time = datetime.now()
        
        duration = (self.end_time - self.start_time).total_seconds()
        
        logger.info("=== Scraper Run Summary ===")
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info(f"Events found: {self.events_found}")
        logger.info(f"Valid events: {self.events_valid}")
        logger.info(f"Events added: {self.events_added}")
        logger.info(f"Events updated: {self.events_updated}")
        logger.info(f"Events skipped: {self.events_skipped}")
        logger.info(f"Validation errors: {self.validation_errors}")
        
        if self.events_found > 0:
            success_rate = (self.events_valid / self.events_found) * 100
            events_per_second = self.events_found / duration
            logger.info(f"Success rate: {success_rate:.1f}%")
            logger.info(f"Processing rate: {events_per_second:.1f} events/second")
        
        if self.memory_samples:
            peak_memory = max(sample['rss'] for sample in self.memory_samples)
            avg_memory = sum(sample['rss'] for sample in self.memory_samples) / len(self.memory_samples)
            logger.info(f"Peak memory usage: {peak_memory:.1f} MB")
            logger.info(f"Average memory usage: {avg_memory:.1f} MB")
    
    def save_to_file(self) -> None:
        """Save metrics to a JSON file."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"aerc_scraper_metrics_{timestamp}.json"
        filepath = self.metrics_dir / filename
        
        with filepath.open('w') as f:
            json.dump(self.to_dict(), f, indent=2)
        
        logger.info(f"Metrics saved to {filepath}")
    
    @staticmethod
    def load_from_file(filepath: str) -> Dict[str, Any]:
        """Load metrics from a JSON file."""
        with open(filepath, 'r') as f:
            return json.load(f)
    
    @classmethod
    def get_historical_metrics(cls, days: int = 7) -> Dict[str, Any]:
        """Get aggregate metrics from recent runs."""
        metrics_dir = Path("logs/metrics")
        if not metrics_dir.exists():
            return {}
        
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
        runs = []
        
        for file in metrics_dir.glob('aerc_scraper_metrics_*.json'):
            if file.stat().st_mtime >= cutoff:
                metrics = cls.load_from_file(str(file))
                runs.append(metrics)
        
        if not runs:
            return {}
        
        # Calculate aggregates
        total_runs = len(runs)
        total_events = sum(run['events']['found'] for run in runs)
        total_valid = sum(run['events']['valid'] for run in runs)
        total_added = sum(run['events']['added'] for run in runs)
        total_errors = sum(run['errors']['validation'] for run in runs)
        
        return {
            'period_days': days,
            'total_runs': total_runs,
            'last_run': max(run['timestamp'] for run in runs),
            'averages': {
                'events_per_run': total_events / total_runs,
                'success_rate': (total_valid / total_events * 100) if total_events > 0 else 0,
                'error_rate': (total_errors / total_events * 100) if total_events > 0 else 0
            },
            'totals': {
                'events_found': total_events,
                'events_valid': total_valid,
                'events_added': total_added,
                'validation_errors': total_errors
            }
        }