#!/usr/bin/env python3
"""
Test script for Pool API endpoints
Tests all pool endpoints without requiring API key authentication
"""

import asyncio
import aiohttp
import json
import sys
import time
from pathlib import Path
from typing import Dict, Any, List

# Add the parent directory to the path so we can import modules
sys.path.append(str(Path(__file__).parent.parent))

from utils.logging import logger

class PoolAPITester:
    """Test class for Pool API endpoints"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.session = None
        self.test_results = []
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_endpoint(self, endpoint: str, method: str = "GET", expected_status: int = 200, 
                          data: Dict = None, headers: Dict = None) -> Dict[str, Any]:
        """Test a single endpoint"""
        url = f"{self.base_url}{endpoint}"
        test_result = {
            "endpoint": endpoint,
            "method": method,
            "url": url,
            "success": False,
            "status_code": None,
            "response_data": None,
            "error": None,
            "response_time": None
        }
        
        try:
            start_time = time.time()
            
            if method.upper() == "GET":
                async with self.session.get(url, headers=headers) as response:
                    test_result["status_code"] = response.status
                    test_result["response_data"] = await response.json()
            elif method.upper() == "POST":
                async with self.session.post(url, json=data, headers=headers) as response:
                    test_result["status_code"] = response.status
                    test_result["response_data"] = await response.json()
            
            test_result["response_time"] = time.time() - start_time
            test_result["success"] = test_result["status_code"] == expected_status
            
        except Exception as e:
            test_result["error"] = str(e)
            test_result["response_time"] = time.time() - start_time
        
        self.test_results.append(test_result)
        return test_result
    
    async def test_all_pool_endpoints(self):
        """Test all pool endpoints"""
        logger.info("Starting Pool API endpoint tests...")
        
        # Test basic pool info endpoint
        await self.test_endpoint("/pool/info")
        
        # Test individual information endpoints
        await self.test_endpoint("/pool/api-url")
        await self.test_endpoint("/pool/software")
        await self.test_endpoint("/pool/fee")
        await self.test_endpoint("/pool/location")
        await self.test_endpoint("/pool/url")
        await self.test_endpoint("/pool/coin")
        await self.test_endpoint("/pool/status")
        
        # Test reload endpoint (POST)
        await self.test_endpoint("/pool/reload", method="POST")
        
        # Test rate limiting by making multiple rapid requests
        logger.info("Testing rate limiting...")
        for i in range(5):
            await self.test_endpoint("/pool/info")
            await asyncio.sleep(0.1)  # Small delay between requests
    
    def validate_response_structure(self, endpoint: str, response_data: Dict) -> List[str]:
        """Validate the structure of endpoint responses"""
        errors = []
        
        if endpoint == "/pool/info":
            required_fields = ["name", "location", "contact_email", "coin", "pool_url", 
                             "api_url", "software_type", "fee_percentage", "status"]
            for field in required_fields:
                if field not in response_data:
                    errors.append(f"Missing required field: {field}")
            
            if "coin" in response_data:
                coin_fields = ["symbol", "name", "algorithm"]
                for field in coin_fields:
                    if field not in response_data["coin"]:
                        errors.append(f"Missing coin field: {field}")
        
        elif endpoint in ["/pool/api-url", "/pool/software", "/pool/location", "/pool/url"]:
            if "value" not in response_data:
                errors.append("Missing 'value' field in response")
        
        elif endpoint == "/pool/fee":
            required_fields = ["fee_percentage", "currency"]
            for field in required_fields:
                if field not in response_data:
                    errors.append(f"Missing required field: {field}")
        
        elif endpoint == "/pool/coin":
            required_fields = ["symbol", "name", "algorithm"]
            for field in required_fields:
                if field not in response_data:
                    errors.append(f"Missing required field: {field}")
        
        elif endpoint == "/pool/status":
            required_fields = ["status", "name", "location", "last_updated"]
            for field in required_fields:
                if field not in response_data:
                    errors.append(f"Missing required field: {field}")
        
        elif endpoint == "/pool/reload":
            if "message" not in response_data:
                errors.append("Missing 'message' field in response")
        
        return errors
    
    def print_test_results(self):
        """Print comprehensive test results"""
        total_tests = len(self.test_results)
        successful_tests = sum(1 for result in self.test_results if result["success"])
        
        print(f"\n{'='*60}")
        print(f"POOL API TEST RESULTS")
        print(f"{'='*60}")
        print(f"Total Tests: {total_tests}")
        print(f"Successful: {successful_tests}")
        print(f"Failed: {total_tests - successful_tests}")
        print(f"Success Rate: {(successful_tests/total_tests)*100:.1f}%")
        print(f"{'='*60}")
        
        for result in self.test_results:
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            print(f"{status} {result['method']} {result['endpoint']}")
            print(f"    Status: {result['status_code']}")
            print(f"    Response Time: {result['response_time']:.3f}s")
            
            if result["error"]:
                print(f"    Error: {result['error']}")
            elif result["response_data"]:
                # Validate response structure
                validation_errors = self.validate_response_structure(
                    result["endpoint"], 
                    result["response_data"]
                )
                if validation_errors:
                    print(f"    Validation Errors: {', '.join(validation_errors)}")
                else:
                    print(f"    Response: Valid structure")
                    
                # Show sample response data (truncated)
                response_str = json.dumps(result["response_data"], indent=2)
                if len(response_str) > 200:
                    response_str = response_str[:200] + "..."
                print(f"    Data: {response_str}")
            print()
    
    async def test_error_scenarios(self):
        """Test error scenarios and edge cases"""
        logger.info("Testing error scenarios...")
        
        # Test non-existent endpoint
        await self.test_endpoint("/pool/nonexistent", expected_status=404)
        
        # Test invalid methods
        await self.test_endpoint("/pool/info", method="POST", expected_status=405)
        
        # Test without pool configuration file (if applicable)
        # This would require temporarily moving the config file
        
    async def test_performance(self):
        """Test endpoint performance"""
        logger.info("Testing endpoint performance...")
        
        # Test concurrent requests
        tasks = []
        for _ in range(10):
            tasks.append(self.test_endpoint("/pool/info"))
        
        start_time = time.time()
        await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        print(f"\nPerformance Test Results:")
        print(f"10 concurrent requests completed in {total_time:.3f}s")
        print(f"Average response time: {total_time/10:.3f}s")

async def main():
    """Main test function"""
    try:
        async with PoolAPITester() as tester:
            # Run all tests
            await tester.test_all_pool_endpoints()
            await tester.test_error_scenarios()
            await tester.test_performance()
            
            # Print results
            tester.print_test_results()
            
    except Exception as e:
        logger.error(f"Test suite failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 