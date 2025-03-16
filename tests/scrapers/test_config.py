"""Tests for shared configuration module."""

import os
import pytest
from pathlib import Path
import tempfile
import yaml

from scrapers.config import ScraperSettings
from scrapers.exceptions import ConfigError

@pytest.fixture
def valid_config():
    """Create valid configuration dictionary."""
    return {
        'database_url': 'postgresql://user:pass@localhost/db',
        'requests_per_second': 2.0,
        'max_burst_size': 10,
        'cache_dir': '/tmp/cache',
        'log_level': 'INFO',
        'use_ai_extraction': False
    }

@pytest.fixture
def config_file(valid_config):
    """Create temporary config file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.safe_dump(valid_config, f)
        return f.name

def test_valid_settings(valid_config):
    """Test valid settings initialization."""
    settings = ScraperSettings(**valid_config)
    assert settings.database_url == valid_config['database_url']
    assert settings.requests_per_second == valid_config['requests_per_second']
    assert settings.max_burst_size == valid_config['max_burst_size']

def test_invalid_database_url():
    """Test validation of database URL."""
    config = {
        'database_url': 'mysql://user:pass@localhost/db',
        'requests_per_second': 1.0
    }
    with pytest.raises(ConfigError, match="Database URL must be PostgreSQL"):
        ScraperSettings(**config)

def test_invalid_log_level():
    """Test validation of log level."""
    config = {
        'database_url': 'postgresql://user:pass@localhost/db',
        'log_level': 'INVALID'
    }
    with pytest.raises(ConfigError, match="Invalid log level"):
        ScraperSettings(**config)

def test_missing_gemini_key():
    """Test validation of Gemini API key when AI extraction is enabled."""
    config = {
        'database_url': 'postgresql://user:pass@localhost/db',
        'use_ai_extraction': True
    }
    with pytest.raises(ConfigError, match="Gemini API key required"):
        ScraperSettings(**config)

def test_load_from_yaml(config_file):
    """Test loading settings from YAML file."""
    settings = ScraperSettings.from_yaml(config_file)
    assert settings.database_url.startswith('postgresql://')
    assert isinstance(settings.requests_per_second, float)

def test_load_nonexistent_file():
    """Test loading from nonexistent file."""
    with pytest.raises(ConfigError, match="Config file not found"):
        ScraperSettings.from_yaml("nonexistent.yaml")

def test_load_invalid_yaml():
    """Test loading invalid YAML."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("invalid: yaml: content:")
        f.flush()
        
        with pytest.raises(ConfigError, match="Invalid YAML format"):
            ScraperSettings.from_yaml(f.name)

def test_environment_override(config_file, monkeypatch):
    """Test environment variable override."""
    monkeypatch.setenv('SCRAPER_DATABASE_URL', 'postgresql://env:pass@localhost/env_db')
    
    settings = ScraperSettings.from_yaml(config_file)
    assert settings.database_url == 'postgresql://env:pass@localhost/env_db'

def test_scraper_specific_settings(valid_config):
    """Test scraper-specific settings."""
    valid_config['scraper_settings'] = {
        'aerc': {
            'base_url': 'https://example.com',
            'timeout': 30
        }
    }
    
    settings = ScraperSettings(**valid_config)
    
    # Test getting settings
    assert settings.get_scraper_setting('aerc', 'base_url') == 'https://example.com'
    assert settings.get_scraper_setting('aerc', 'timeout') == 30
    assert settings.get_scraper_setting('aerc', 'nonexistent', 'default') == 'default'
    
    # Test updating settings
    settings.update_scraper_settings('aerc', {'new_setting': 'value'})
    assert settings.get_scraper_setting('aerc', 'new_setting') == 'value'
    assert settings.get_scraper_setting('aerc', 'base_url') == 'https://example.com'

def test_save_to_yaml(valid_config):
    """Test saving settings to YAML."""
    settings = ScraperSettings(**valid_config)
    
    with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as f:
        settings.to_yaml(f.name)
        
        # Load and verify
        with open(f.name) as f2:
            saved_config = yaml.safe_load(f2)
        
        assert saved_config['database_url'] == valid_config['database_url']
        assert saved_config['requests_per_second'] == valid_config['requests_per_second']

def test_save_yaml_error():
    """Test error handling when saving YAML."""
    settings = ScraperSettings(**valid_config)
    
    with pytest.raises(ConfigError, match="Failed to save config"):
        settings.to_yaml("/nonexistent/path/config.yaml")

def test_default_values():
    """Test default values are set correctly."""
    minimal_config = {
        'database_url': 'postgresql://user:pass@localhost/db'
    }
    
    settings = ScraperSettings(**minimal_config)
    assert settings.requests_per_second == 1.0
    assert settings.max_burst_size == 5
    assert settings.cache_ttl == 3600
    assert settings.log_level == "INFO"
    assert settings.use_ai_extraction is False

def test_value_constraints():
    """Test value constraints are enforced."""
    config = {
        'database_url': 'postgresql://user:pass@localhost/db',
        'requests_per_second': 0.05  # Too low
    }
    with pytest.raises(ValueError):
        ScraperSettings(**config)
    
    config['requests_per_second'] = 11.0  # Too high
    with pytest.raises(ValueError):
        ScraperSettings(**config)