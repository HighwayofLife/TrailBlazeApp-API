#!/usr/bin/env python3
"""
Test the API endpoints directly.

This script tests the API endpoints directly by making HTTP requests
to a running API instance. It's useful for testing the API without
going through the test framework.
"""
import requests
import json
import sys
from datetime import datetime

# Base URL for the API
BASE_URL = "http://localhost:8000/api/v1"

def test_health():
    """Test the health endpoint."""
    url = f"{BASE_URL}/health"
    response = requests.get(url)
    
    if response.status_code == 200:
        print(f"✅ Health check passed: {response.json()}")
        return True
    else:
        print(f"❌ Health check failed: {response.status_code}")
        return False

def test_events():
    """Test the events endpoints."""
    # Test GET /events
    url = f"{BASE_URL}/events"
    response = requests.get(url)
    
    if response.status_code == 200:
        events = response.json()
        print(f"✅ GET /events returned {len(events)} events")
    else:
        print(f"❌ GET /events failed: {response.status_code}")
        return False
    
    # Test POST /events
    event_data = {
        "name": f"Test Event {datetime.now().isoformat()}",
        "location": "Test Location",
        "date_start": datetime.now().isoformat(),
        "region": "Test Region",
        "source": "TEST"
    }
    
    response = requests.post(url, json=event_data)
    
    if response.status_code == 201:
        event = response.json()
        print(f"✅ POST /events created event with ID {event['id']}")
        event_id = event["id"]
    else:
        print(f"❌ POST /events failed: {response.status_code}")
        return False
    
    # Test GET /events/{id}
    url = f"{BASE_URL}/events/{event_id}"
    response = requests.get(url)
    
    if response.status_code == 200:
        event = response.json()
        print(f"✅ GET /events/{event_id} returned event: {event['name']}")
    else:
        print(f"❌ GET /events/{event_id} failed: {response.status_code}")
        return False
    
    # Test PUT /events/{id}
    update_data = {
        "name": f"Updated Event {datetime.now().isoformat()}"
    }
    
    response = requests.put(url, json=update_data)
    
    if response.status_code == 200:
        event = response.json()
        print(f"✅ PUT /events/{event_id} updated event: {event['name']}")
    else:
        print(f"❌ PUT /events/{event_id} failed: {response.status_code}")
        return False
    
    # Test DELETE /events/{id}
    response = requests.delete(url)
    
    if response.status_code == 204:
        print(f"✅ DELETE /events/{event_id} deleted event")
    else:
        print(f"❌ DELETE /events/{event_id} failed: {response.status_code}")
        return False
    
    # Verify event was deleted
    response = requests.get(url)
    
    if response.status_code == 404:
        print(f"✅ GET /events/{event_id} verified event was deleted")
        return True
    else:
        print(f"❌ GET /events/{event_id} failed to verify deletion: {response.status_code}")
        return False

def main():
    """Run all API tests."""
    print("Testing TrailBlaze API...")
    
    tests = [
        ("Health Check", test_health),
        ("Events API", test_events)
    ]
    
    failed_tests = []
    
    for name, test_func in tests:
        print(f"\n--- Testing {name} ---")
        if not test_func():
            failed_tests.append(name)
    
    print("\n--- Test Summary ---")
    print(f"Total tests: {len(tests)}")
    print(f"Passed: {len(tests) - len(failed_tests)}")
    print(f"Failed: {len(failed_tests)}")
    
    if failed_tests:
        print("\nFailed tests:")
        for test in failed_tests:
            print(f"  - {test}")
        return 1
    else:
        print("\nAll tests passed!")
        return 0

if __name__ == "__main__":
    sys.exit(main())