"""Shared metrics collection and reporting module."""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from prometheus_client import Counter, Gauge, Histogram, CollectorRegistry

logger = logging.getLogger(__name__)

class MetricsCollector:
    """Collects and reports metrics with Prometheus integration."""
    
    def __init__(self, source: str, metrics_dir: str):
        """Initialize metrics collector."""
        self.source = source
        self.metrics_dir = Path(metrics_dir)
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self.start_time = datetime.now()
        
        # Initialize Prometheus registry and metrics
        self.registry = CollectorRegistry()
        
        # Event metrics
        self.events_found = Counter(
            'scraper_events_found_total',
            'Total number of events found',
            ['source'],
            registry=self.registry
        )
        self.events_valid = Counter(
            'scraper_events_valid_total',
            'Total number of valid events',
            ['source'],
            registry=self.registry
        )
        self.events_stored = Counter(
            'scraper_events_stored_total',
            'Total number of events stored',
            ['source', 'operation'],
            registry=self.registry
        )
        
        # Performance metrics
        self.processing_time = Histogram(
            'scraper_processing_seconds',
            'Time spent processing events',
            ['source', 'operation'],
            registry=self.registry
        )
        self.memory_usage = Gauge(
            'scraper_memory_bytes',
            'Memory usage in bytes',
            ['source'],
            registry=self.registry
        )
        
        # Error metrics
        self.errors = Counter(
            'scraper_errors_total',
            'Total number of errors',
            ['source', 'type'],
            registry=self.registry
        )
        
        # Component metrics
        self.network_metrics = {
            'requests': 0,
            'retries': 0,
            'failures': 0,
            'bytes_downloaded': 0,
            'avg_response_time': 0.0
        }
        
        self.validation_metrics = {
            'total': 0,
            'valid': 0,
            'invalid': 0,
            'validation_time': 0.0
        }
        
        self.storage_metrics = {
            'inserts': 0,
            'updates': 0,
            'failures': 0,
            'operation_time': 0.0
        }
        
        self.cache_metrics = {
            'hits': 0,
            'misses': 0,
            'errors': 0
        }
    
    def update_network_metrics(self, metrics: Dict[str, Any]) -> None:
        """Update network-related metrics."""
        self.network_metrics.update(metrics)
        
        # Update Prometheus metrics
        if 'bytes_downloaded' in metrics:
            self.processing_time.labels(
                source=self.source,
                operation='network'
            ).observe(metrics.get('avg_response_time', 0))
        
        if 'failures' in metrics:
            self.errors.labels(
                source=self.source,
                type='network'
            ).inc(metrics['failures'])
    
    def update_validation_metrics(self, metrics: Dict[str, Any]) -> None:
        """Update validation-related metrics."""
        self.validation_metrics.update(metrics)
        
        # Update Prometheus metrics
        if 'valid' in metrics:
            self.events_valid.labels(source=self.source).inc(metrics['valid'])
        
        if 'invalid' in metrics:
            self.errors.labels(
                source=self.source,
                type='validation'
            ).inc(metrics['invalid'])
    
    def update_storage_metrics(self, metrics: Dict[str, Any]) -> None:
        """Update storage-related metrics."""
        self.storage_metrics.update(metrics)
        
        # Update Prometheus metrics
        if 'inserts' in metrics:
            self.events_stored.labels(
                source=self.source,
                operation='insert'
            ).inc(metrics['inserts'])
        
        if 'updates' in metrics:
            self.events_stored.labels(
                source=self.source,
                operation='update'
            ).inc(metrics['updates'])
        
        if 'failures' in metrics:
            self.errors.labels(
                source=self.source,
                type='storage'
            ).inc(metrics['failures'])
    
    def update_cache_metrics(self, metrics: Dict[str, Any]) -> None:
        """Update cache-related metrics."""
        self.cache_metrics.update(metrics)
        
        # Update Prometheus metrics
        if 'errors' in metrics:
            self.errors.labels(
                source=self.source,
                type='cache'
            ).inc(metrics['errors'])
    
    def update_memory_usage(self, bytes_used: int) -> None:
        """Update memory usage metric."""
        self.memory_usage.labels(source=self.source).set(bytes_used)
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics."""
        return {
            'source': self.source,
            'start_time': self.start_time.isoformat(),
            'end_time': datetime.now().isoformat(),
            'network': self.network_metrics,
            'validation': self.validation_metrics,
            'storage': self.storage_metrics,
            'cache': self.cache_metrics,
            'total_events': {
                'found': self.events_found._value.get(),
                'valid': self.events_valid._value.get(),
                'stored': sum(
                    self.events_stored.labels(
                        source=self.source,
                        operation=op
                    )._value.get()
                    for op in ['insert', 'update']
                )
            },
            'errors': {
                error_type: self.errors.labels(
                    source=self.source,
                    type=error_type
                )._value.get()
                for error_type in ['network', 'validation', 'storage', 'cache']
            }
        }
    
    def save_metrics(self, run_id: Optional[str] = None) -> None:
        """Save metrics to file."""
        try:
            metrics = self.get_all_metrics()
            
            if run_id is None:
                run_id = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            filename = self.metrics_dir / f"{self.source}_{run_id}_metrics.json"
            
            with open(filename, 'w') as f:
                json.dump(metrics, f, indent=2)
            
            logger.info(f"Metrics saved to {filename}")
            
        except Exception as e:
            logger.error(f"Failed to save metrics: {str(e)}")
    
    def log_summary(self) -> None:
        """Log a summary of key metrics."""
        metrics = self.get_all_metrics()
        total_events = metrics['total_events']
        errors = metrics['errors']
        
        logger.info(
            f"Scraper Summary ({self.source}):\n"
            f"Events Found: {total_events['found']}\n"
            f"Events Valid: {total_events['valid']}\n"
            f"Events Stored: {total_events['stored']}\n"
            f"Total Errors: {sum(errors.values())}\n"
            f"Success Rate: {(total_events['valid'] / total_events['found'] * 100):.1f}% "
            f"(if events found > 0)\n"
            f"Run Time: {(datetime.now() - self.start_time).total_seconds():.1f}s"
        )