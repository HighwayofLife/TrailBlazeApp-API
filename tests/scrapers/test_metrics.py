"""Tests for shared metrics collection module."""

import pytest
import json
from datetime import datetime
from pathlib import Path
from scrapers.metrics import MetricsCollector

@pytest.fixture
def metrics_dir(tmp_path):
    """Create temporary metrics directory."""
    metrics_dir = tmp_path / "metrics"
    metrics_dir.mkdir()
    return metrics_dir

@pytest.fixture
def collector(metrics_dir):
    """Create metrics collector instance."""
    return MetricsCollector("test_source", str(metrics_dir))

def test_initial_metrics_state(collector):
    """Test initial state of metrics."""
    metrics = collector.get_all_metrics()
    
    assert metrics['source'] == "test_source"
    assert isinstance(metrics['start_time'], str)
    assert isinstance(metrics['end_time'], str)
    
    # Check component metrics are initialized
    assert all(m == 0 for m in collector.network_metrics.values())
    assert all(m == 0 for m in collector.validation_metrics.values())
    assert all(m == 0 for m in collector.storage_metrics.values())
    assert all(m == 0 for m in collector.cache_metrics.values())

def test_update_network_metrics(collector):
    """Test updating network metrics."""
    network_data = {
        'requests': 10,
        'retries': 2,
        'failures': 1,
        'bytes_downloaded': 1000,
        'avg_response_time': 0.5
    }
    
    collector.update_network_metrics(network_data)
    metrics = collector.get_all_metrics()
    
    assert metrics['network'] == network_data
    # Check Prometheus counter
    error_count = collector.errors.labels(
        source="test_source",
        type="network"
    )._value.get()
    assert error_count == 1

def test_update_validation_metrics(collector):
    """Test updating validation metrics."""
    validation_data = {
        'total': 10,
        'valid': 8,
        'invalid': 2,
        'validation_time': 1.5
    }
    
    collector.update_validation_metrics(validation_data)
    metrics = collector.get_all_metrics()
    
    assert metrics['validation'] == validation_data
    # Check Prometheus counter
    valid_count = collector.events_valid.labels(
        source="test_source"
    )._value.get()
    assert valid_count == 8

def test_update_storage_metrics(collector):
    """Test updating storage metrics."""
    storage_data = {
        'inserts': 5,
        'updates': 3,
        'failures': 1,
        'operation_time': 2.0
    }
    
    collector.update_storage_metrics(storage_data)
    metrics = collector.get_all_metrics()
    
    assert metrics['storage'] == storage_data
    # Check Prometheus counters
    inserts = collector.events_stored.labels(
        source="test_source",
        operation="insert"
    )._value.get()
    updates = collector.events_stored.labels(
        source="test_source",
        operation="update"
    )._value.get()
    assert inserts == 5
    assert updates == 3

def test_update_cache_metrics(collector):
    """Test updating cache metrics."""
    cache_data = {
        'hits': 15,
        'misses': 5,
        'errors': 1
    }
    
    collector.update_cache_metrics(cache_data)
    metrics = collector.get_all_metrics()
    
    assert metrics['cache'] == cache_data
    # Check Prometheus counter
    error_count = collector.errors.labels(
        source="test_source",
        type="cache"
    )._value.get()
    assert error_count == 1

def test_update_memory_usage(collector):
    """Test updating memory usage metric."""
    memory_bytes = 1024 * 1024  # 1MB
    collector.update_memory_usage(memory_bytes)
    
    # Check Prometheus gauge
    memory_usage = collector.memory_usage.labels(
        source="test_source"
    )._value.get()
    assert memory_usage == memory_bytes

def test_save_metrics(collector, metrics_dir):
    """Test saving metrics to file."""
    # Add some test metrics
    collector.update_network_metrics({'requests': 10})
    collector.update_validation_metrics({'valid': 8})
    
    # Save with specific run ID
    run_id = "test_run"
    collector.save_metrics(run_id)
    
    # Check file exists and content
    metrics_file = metrics_dir / f"test_source_{run_id}_metrics.json"
    assert metrics_file.exists()
    
    with open(metrics_file) as f:
        saved_metrics = json.load(f)
    
    assert saved_metrics['source'] == "test_source"
    assert saved_metrics['network']['requests'] == 10
    assert saved_metrics['validation']['valid'] == 8

def test_log_summary(collector, caplog):
    """Test logging metrics summary."""
    # Add test metrics
    collector.update_validation_metrics({
        'total': 10,
        'valid': 8,
        'invalid': 2
    })
    collector.update_storage_metrics({
        'inserts': 5,
        'updates': 3
    })
    
    # Log summary
    collector.log_summary()
    
    # Check log output
    assert "Scraper Summary (test_source)" in caplog.text
    assert "Events Valid: 8" in caplog.text
    assert "Success Rate:" in caplog.text