import requests
import time
import sys
import json
from typing import Dict, Any, List, Optional

# Configuration
BASE_URL = "http://localhost:8000"
MAX_RETRIES = 10
RETRY_DELAY = 3  # seconds

class APITester:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.results: Dict[str, Dict[str, Any]] = {}
        self.total_tests = 0
        self.passed_tests = 0

    def wait_for_api(self) -> bool:
        """Wait for the API to become available."""
        print("Waiting for API to become available...")
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.get(f"{self.base_url}/")
                if response.status_code == 200:
                    print(f"API is available after {attempt+1} attempts!")
                    return True
            except requests.RequestException:
                pass
            
            print(f"Attempt {attempt+1}/{MAX_RETRIES} failed. Retrying in {RETRY_DELAY}s...")
            time.sleep(RETRY_DELAY)
        
        print("Failed to connect to API after maximum retries.")
        return False

    def run_test(self, name: str, method: str, endpoint: str, 
                expected_status: int = 200, 
                data: Optional[Dict[str, Any]] = None, 
                headers: Optional[Dict[str, str]] = None) -> bool:
        """Run a test against an API endpoint."""
        self.total_tests += 1
        url = f"{self.base_url}{endpoint}"
        print(f"\nRunning test: {name}")
        print(f"  {method} {url}")
        
        try:
            if method.lower() == 'get':
                response = requests.get(url, headers=headers)
            elif method.lower() == 'post':
                response = requests.post(url, json=data, headers=headers)
            elif method.lower() == 'put':
                response = requests.put(url, json=data, headers=headers)
            elif method.lower() == 'delete':
                response = requests.delete(url, headers=headers)
            else:
                print(f"  Unsupported method: {method}")
                return False
            
            status_passed = response.status_code == expected_status
            
            result = {
                "status_code": response.status_code,
                "expected_status_code": expected_status,
                "passed": status_passed,
                "response": response.text[:200] + "..." if len(response.text) > 200 else response.text
            }
            
            self.results[name] = result
            
            if status_passed:
                print(f"  ✓ Status code: {response.status_code}")
                self.passed_tests += 1
            else:
                print(f"  ✗ Status code: {response.status_code}, expected: {expected_status}")
                
            print(f"  Response: {response.text[:100]}..." if len(response.text) > 100 else f"  Response: {response.text}")
            return status_passed
            
        except requests.RequestException as e:
            print(f"  ✗ Request failed: {str(e)}")
            self.results[name] = {
                "passed": False,
                "error": str(e)
            }
            return False

    def print_summary(self):
        """Print test results summary."""
        print("\n" + "="*50)
        print("TEST RESULTS SUMMARY")
        print("="*50)
        
        for name, result in self.results.items():
            if result.get("passed"):
                print(f"✓ {name}")
            else:
                print(f"✗ {name}")
                if "error" in result:
                    print(f"  Error: {result['error']}")
                else:
                    print(f"  Expected status: {result['expected_status_code']}")
                    print(f"  Actual status: {result['status_code']}")
        
        print("-"*50)
        print(f"Tests passed: {self.passed_tests}/{self.total_tests} "
              f"({self.passed_tests/self.total_tests*100:.1f}%)")
        print("="*50)

def main():
    tester = APITester(BASE_URL)
    
    # Wait for the API to be available
    if not tester.wait_for_api():
        print("Could not connect to API. Exiting.")
        return 1
    
    # Test root endpoint
    tester.run_test("Root endpoint", "GET", "/", 200)
    
    # Test API endpoints
    tester.run_test("API docs", "GET", "/docs", 200)
    tester.run_test("Events endpoint", "GET", "/v1/events", 200)

    # Print test summary
    tester.print_summary()
    
    # Return exit code based on test results
    return 0 if tester.passed_tests == tester.total_tests else 1

if __name__ == "__main__":
    sys.exit(main())