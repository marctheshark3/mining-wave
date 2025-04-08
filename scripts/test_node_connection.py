#!/usr/bin/env python3
# Test script to verify our local node connection

import asyncio
import aiohttp
import json
import sys
import os
import logging

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import our utils
from utils.blockchain import get_block_by_height, get_block_transactions

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Local node URL
NODE_API_BASE = "http://localhost:9053"

async def test_node_connection():
    """Test connection to the node API."""
    logger.info("Testing connection to node API")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{NODE_API_BASE}/info") as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info("Successfully connected to node API")
                    logger.info(f"Node information:")
                    logger.info(f"- Network type: {data.get('network')}")
                    logger.info(f"- Current height: {data.get('fullHeight')}")
                    logger.info(f"- Headers height: {data.get('headersHeight')}")
                    logger.info(f"- Peers count: {data.get('peersCount')}")
                    logger.info(f"- Unconfirmed count: {data.get('unconfirmedCount')}")
                    logger.info(f"- Difficulty: {data.get('difficulty')}")
                    logger.info(f"- State type: {data.get('stateType')}")
                    return True
                else:
                    logger.error(f"Failed to connect to node API: HTTP {response.status}")
                    return False
    except Exception as e:
        logger.error(f"Error connecting to node API: {str(e)}")
        return False

async def test_get_block(height=1495600):
    """Test retrieving a block from the node API."""
    logger.info(f"Testing block retrieval for height {height}")
    try:
        block_data = await get_block_by_height(height)
        if block_data:
            # Check if we have a block ID either at top level or in header
            block_id = None
            if isinstance(block_data, dict):
                if 'id' in block_data:
                    block_id = block_data['id']
                elif 'header' in block_data and isinstance(block_data['header'], dict) and 'id' in block_data['header']:
                    block_id = block_data['header']['id']
                    
            if block_id:
                logger.info(f"Successfully retrieved block {height} with ID: {block_id}")
            else:
                logger.warning(f"Retrieved block {height} but could not find ID")
            
            return block_data
        else:
            logger.error(f"Failed to retrieve block {height}")
            return None
    except Exception as e:
        logger.error(f"Error retrieving block {height}: {str(e)}")
        return None

async def test_get_block_transactions(block_data):
    """Test retrieving transactions for a block."""
    if not block_data:
        logger.error("No block data provided")
        return None
        
    try:
        # Check if we have a block ID either at top level or in header
        block_id = None
        if isinstance(block_data, dict):
            if 'id' in block_data:
                block_id = block_data['id']
            elif 'header' in block_data and isinstance(block_data['header'], dict) and 'id' in block_data['header']:
                block_id = block_data['header']['id']
                
        if not block_id:
            logger.error("No block ID found in block data")
            return None
            
        logger.info(f"Testing transaction retrieval for block ID: {block_id}")
        
        transactions = await get_block_transactions(block_data)
        if transactions:
            logger.info(f"Successfully retrieved {len(transactions)} transactions for block")
            return transactions
        else:
            logger.error("Failed to retrieve block transactions")
            return None
    except Exception as e:
        logger.error(f"Error retrieving block transactions: {str(e)}")
        return None

async def main():
    """Run all tests."""
    logger.info("===== Starting Node API Tests =====")
    
    # Test node connection
    connection_ok = await test_node_connection()
    if not connection_ok:
        logger.error("Failed to connect to node API. Aborting remaining tests.")
        return
    
    # Test block retrieval
    block_data = await test_get_block()
    if not block_data:
        logger.error("Failed to retrieve block. Aborting remaining tests.")
        return
    
    # Test transaction retrieval
    transactions = await test_get_block_transactions(block_data)
    if not transactions:
        logger.warning("Failed to retrieve block transactions.")
    
    logger.info("===== All tests completed =====")

if __name__ == "__main__":
    asyncio.run(main()) 