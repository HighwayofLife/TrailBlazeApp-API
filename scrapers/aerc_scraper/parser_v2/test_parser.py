#!/usr/bin/env python
"""
Test script for the HTML parser.
This script tests the new HTML parser against cached AERC calendar data,
and optionally compares results with the Gemini-based extraction.
"""

import json
import os
import sys
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from scrapers.aerc_scraper.parser_v2.html_parser import HTMLParser
from scrapers.aerc_scraper.gemini_api import GeminiAPI
from scrapers.aerc_scraper.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger("test_parser")

def load_cached_html() -> Optional[str]:
    """Load HTML from the most recent cache file."""
    cache_dir = Path("cache")
    
    if not cache_dir.exists():
        logger.error(f"Cache directory not found: {cache_dir}")
        return None
    
    # Find the most recent JSON cache file
    json_files = list(cache_dir.glob("*.json"))
    if not json_files:
        logger.error("No JSON cache files found")
        return None
    
    # Sort by modification time (newest first)
    latest_file = sorted(json_files, key=lambda f: f.stat().st_mtime, reverse=True)[0]
    logger.info(f"Using cache file: {latest_file}")
    
    try:
        with open(latest_file, 'r') as f:
            data = json.load(f)
            return data.get('value')
    except Exception as e:
        logger.error(f"Error loading cache file: {e}")
        return None

def save_extracted_data(data: List[Dict[str, Any]], filename: str) -> None:
    """Save extracted data to a JSON file."""
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    output_path = output_dir / filename
    
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    logger.info(f"Saved {len(data)} events to {output_path}")

def compare_results(
    html_parser_results: List[Dict[str, Any]],
    gemini_results: Optional[List[Dict[str, Any]]] = None
) -> None:
    """Compare results between HTML parser and optionally Gemini API."""
    html_count = len(html_parser_results)
    logger.info(f"HTML Parser extracted {html_count} events")
    
    # Count events with links
    html_with_website = sum(1 for e in html_parser_results if e.get('website'))
    html_with_flyer = sum(1 for e in html_parser_results if e.get('flyerUrl'))
    html_with_map = sum(1 for e in html_parser_results if e.get('mapLink'))
    
    logger.info(f"HTML Parser link coverage:")
    logger.info(f"  - Website links: {html_with_website}/{html_count} ({html_with_website/html_count:.1%})")
    logger.info(f"  - Flyer links: {html_with_flyer}/{html_count} ({html_with_flyer/html_count:.1%})")
    logger.info(f"  - Map links: {html_with_map}/{html_count} ({html_with_map/html_count:.1%})")
    
    # Compare with Gemini results if available
    if gemini_results:
        gemini_count = len(gemini_results)
        logger.info(f"Gemini API extracted {gemini_count} events")
        
        gemini_with_website = sum(1 for e in gemini_results if e.get('website'))
        gemini_with_flyer = sum(1 for e in gemini_results if e.get('flyerUrl'))
        gemini_with_map = sum(1 for e in gemini_results if e.get('mapLink'))
        
        logger.info(f"Gemini API link coverage:")
        logger.info(f"  - Website links: {gemini_with_website}/{gemini_count} ({gemini_with_website/gemini_count:.1%})")
        logger.info(f"  - Flyer links: {gemini_with_flyer}/{gemini_count} ({gemini_with_flyer/gemini_count:.1%})")
        logger.info(f"  - Map links: {gemini_with_map}/{gemini_count} ({gemini_with_map/gemini_count:.1%})")
        
        # Show differences
        logger.info("Comparison:")
        logger.info(f"  - Total events: {html_count} vs {gemini_count}")
        logger.info(f"  - Website links: {html_with_website} vs {gemini_with_website}")
        logger.info(f"  - Flyer links: {html_with_flyer} vs {gemini_with_flyer}")
        logger.info(f"  - Map links: {html_with_map} vs {gemini_with_map}")

async def run_gemini_extraction(html: str) -> List[Dict[str, Any]]:
    """Run extraction using Gemini API for comparison."""
    logger.info("Running Gemini API extraction for comparison")
    
    settings = get_settings()
    if not settings.gemini_api_key:
        logger.error("Gemini API key not set. Skipping Gemini extraction.")
        return []
    
    try:
        gemini_api = GeminiAPI(settings.gemini_api_key)
        results = await gemini_api.extract_events(html)
        logger.info(f"Gemini API extracted {len(results)} events")
        return results
    except Exception as e:
        logger.error(f"Error during Gemini extraction: {e}")
        return []

async def main():
    """Run the HTML parser test and comparison."""
    logger.info("Starting HTML parser test")
    
    # Load HTML from cache
    html = load_cached_html()
    if not html:
        logger.error("Failed to load HTML from cache. Exiting.")
        return
    
    # Parse with HTML parser
    parser = HTMLParser(debug_mode=True)
    html_results = parser.parse_html(html)
    
    # Save results
    save_extracted_data(html_results, "html_parser_results.json")
    
    # Compare with Gemini (optional)
    compare_gemini = os.environ.get("COMPARE_GEMINI", "false").lower() == "true"
    
    if compare_gemini:
        gemini_results = await run_gemini_extraction(html)
        if gemini_results:
            save_extracted_data(gemini_results, "gemini_results.json")
            compare_results(html_results, gemini_results)
    else:
        compare_results(html_results)
    
    # Print parser metrics
    logger.info("HTML Parser metrics:")
    for key, value in parser.get_metrics().items():
        logger.info(f"  - {key}: {value}")
    
    logger.info("HTML parser test completed")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 