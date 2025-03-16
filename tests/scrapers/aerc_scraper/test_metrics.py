"""Tests for metrics collection module."""

import pytest
import json
from datetime import datetime, timedelta
import os
from pathlib import Path
import shutil
from scrapers.aerc_scraper.metrics import ScraperMetrics

@pytest.fixture
def metrics_dir():
    """Create and clean up test metrics directory."""
    dir_path = Path("tests/metrics")
    dir_path.mkdir(parents=True, exist_ok=True)
    yield dir_path
    shutil.rmtree(dir_path)

@pytest.fixture
def test_metrics():
    """Create metrics instance with test start time."""
    return ScraperMetrics(start_time=datetime.now())

def test_metrics_initialization(test_metrics):
    """Test metrics initialization."""
    assert test_metrics.start_time is not None
    assert test_metrics.end_time is None
    assert test_metrics.events_found == 0
    assert test_metrics.events_valid == 0
    assert test_metrics.validation_errors == 0
    assert test_metrics.memory_samples == []

def test_metrics_update(test_metrics):
    """Test updating metrics from component metrics."""
    component_metrics = {
        'events_found': 10,
        'events_valid': 8,
        'validation_errors': 2,
        'events_added': 5,
        'events_updated': 3
    }
    
    test_metrics.update(component_metrics)
    
    assert test_metrics.events_found == 10
    assert test_metrics.events_valid == 8
    assert test_metrics.validation_errors == 2
    assert test_metrics.events_added == 5
    assert test_metrics.events_updated == 3

def test_memory_sampling(test_metrics):
    """Test memory sampling."""
    # Force multiple memory samples
    for _ in range(3):
        test_metrics._sample_memory()
    
    assert len(test_metrics.memory_samples) == 3
    for sample in test_metrics.memory_samples:
        assert 'timestamp' in sample
        assert 'rss' in sample
        assert 'vms' in sample
        assert 'percent' in sample

def test_metrics_to_dict(test_metrics):
    """Test conversion to dictionary format."""
    # Set some test values
    test_metrics.events_found = 10
    test_metrics.events_valid = 8
    test_metrics.end_time = datetime.now()
    
    metrics_dict = test_metrics.to_dict()
    
    assert metrics_dict['timestamp']
    assert metrics_dict['start_time']
    assert metrics_dict['end_time']
    assert metrics_dict['duration_seconds'] > 0
    assert metrics_dict['events']['found'] == 10
    assert metrics_dict['events']['valid'] == 8
    assert 'performance' in metrics_dict

def test_metrics_save_to_file(test_metrics, metrics_dir):
    """Test saving metrics to file."""
    test_metrics.metrics_dir = metrics_dir
    test_metrics.save_to_file()
    
    # Check if file was created
    files = list(metrics_dir.glob('aerc_scraper_metrics_*.json'))
    assert len(files) == 1
    
    # Verify file content
    with files[0].open('r') as f:
        saved_metrics = json.load(f)
        assert saved_metrics['events']['found'] == test_metrics.events_found

def test_load_from_file(test_metrics, metrics_dir):
    """Test loading metrics from file."""
    # Save some test metrics
    test_metrics.metrics_dir = metrics_dir
    test_metrics.events_found = 10
    test_metrics.save_to_file()
    
    # Find the saved file
    files = list(metrics_dir.glob('aerc_scraper_metrics_*.json'))
    loaded_metrics = ScraperMetrics.load_from_file(str(files[0]))
    
    assert loaded_metrics['events']['found'] == 10

def test_get_historical_metrics(metrics_dir):
    """Test retrieving historical metrics."""
    # Create multiple metrics files with different dates
    metrics1 = ScraperMetrics(start_time=datetime.now() - timedelta(days=1))
    metrics1.events_found = 10
    metrics1.events_valid = 8
    metrics1.metrics_dir = metrics_dir
    metrics1.save_to_file()
    
    metrics2 = ScraperMetrics(start_time=datetime.now())
    metrics2.events_found = 15
    metrics2.events_valid = 12
    metrics2.metrics_dir = metrics_dir
    metrics2.save_to_file()
    
    history = ScraperMetrics.get_historical_metrics(days=7)
    
    assert history['total_runs'] == 2
    assert history['totals']['events_found'] == 25
    assert history['totals']['events_valid'] == 20
    assert history['averages']['events_per_run'] == 12.5

def test_log_summary(test_metrics, caplog):
    """Test logging metrics summary."""
    # Set test values
    test_metrics.events_found = 10
    test_metrics.events_valid = 8
    test_metrics.events_added = 5
    test_metrics.events_updated = 3
    test_metrics.validation_errors = 2
    test_metrics.end_time = datetime.now()
    
    # Add memory samples
    test_metrics._sample_memory()
    test_metrics._sample_memory()
    
    test_metrics.log_summary()
    
    # Check log contents
    assert "Scraper Run Summary" in caplog.text
    assert "Events found: 10" in caplog.text
    assert "Valid events: 8" in caplog.text
    assert "Success rate" in caplog.text
    assert "Processing rate" in caplog.text
    assert "Peak memory usage" in caplog.text

def test_metrics_with_empty_results(test_metrics):
    """Test metrics with empty results."""
    test_metrics.end_time = datetime.now()
    metrics_dict = test_metrics.to_dict()
    
    assert metrics_dict['events']['found'] == 0
    assert metrics_dict['events']['valid'] == 0
    assert 'rates' not in metrics_dict

def test_metrics_rate_calculations(test_metrics):
    """Test rate calculations."""
    test_metrics.events_found = 100
    test_metrics.events_valid = 80
    test_metrics.end_time = datetime.now() + timedelta(seconds=10)
    
    metrics_dict = test_metrics.to_dict()
    
    assert metrics_dict['rates']['success_rate'] == 80.0
    assert metrics_dict['rates']['events_per_second'] > 0