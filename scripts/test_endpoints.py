#!/usr/bin/env python3
# Test different Ergo node API endpoint formats to find the correct one

import asyncio
import aiohttp
import json
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test different base URLs and formats
BASE_URLS = [
    "http://localhost:9030",
    "http://localhost:9053",
    "http://127.0.0.1:9030",
    "http://127.0.0.1:9053"
]

# Test different endpoint paths
INFO_ENDPOINTS = [
    "/info",
    "/node/info",
    "/api/info",
    "/api/node/info"
]

BLOCK_ENDPOINTS = [
    "/blocks/at/1000000",
    "/blocks/1000000",
    "/api/blocks/at/1000000",
    "/api/blocks/1000000"
]

async def test_endpoint(base_url, endpoint):
    """Test a specific API endpoint"""
    full_url = f"{base_url}{endpoint}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(full_url, timeout=5) as response:
                if response.status == 200:
                    try:
                        data = await response.json()
                        logger.info(f"✅ SUCCESS: {full_url} - Status: {response.status}")
                        return True, data
                    except:
                        logger.info(f"⚠️ PARTIAL: {full_url} - Status: {response.status} but not valid JSON")
                        return False, None
                else:
                    logger.info(f"❌ FAILED: {full_url} - Status: {response.status}")
                    return False, None
    except aiohttp.ClientError as e:
        logger.info(f"❌ ERROR: {full_url} - Connection error: {str(e)}")
        return False, None
    except asyncio.TimeoutError:
        logger.info(f"⏱️ TIMEOUT: {full_url} - Request timed out")
        return False, None
    except Exception as e:
        logger.info(f"❌ ERROR: {full_url} - Unexpected error: {str(e)}")
        return False, None

async def main():
    """Test all combinations of base URLs and endpoints"""
    logger.info("===== Testing Different Ergo Node API Endpoint Formats =====")
    
    # Test info endpoints
    logger.info("\n----- Testing Info Endpoints -----")
    info_results = []
    for base_url in BASE_URLS:
        for endpoint in INFO_ENDPOINTS:
            success, data = await test_endpoint(base_url, endpoint)
            if success:
                info_results.append((base_url, endpoint, data))
    
    # Test block endpoints
    logger.info("\n----- Testing Block Endpoints -----")
    block_results = []
    for base_url in BASE_URLS:
        for endpoint in BLOCK_ENDPOINTS:
            success, data = await test_endpoint(base_url, endpoint)
            if success:
                block_results.append((base_url, endpoint, data))
    
    # Report successful configurations
    logger.info("\n===== SUCCESSFUL CONFIGURATIONS =====")
    if info_results:
        logger.info("\n----- Info Endpoint Successes -----")
        for base_url, endpoint, _ in info_results:
            logger.info(f"✅ {base_url}{endpoint}")
    
    if block_results:
        logger.info("\n----- Block Endpoint Successes -----")
        for base_url, endpoint, _ in block_results:
            logger.info(f"✅ {base_url}{endpoint}")
    
    if not info_results and not block_results:
        logger.info("❌ No successful endpoint configurations found.")
    
    logger.info("\n===== Test completed =====")
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 