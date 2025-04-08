#!/usr/bin/env python3
# Debug the block structure from the Ergo node API

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

# Local node URL
NODE_API_BASE = "http://localhost:9053"

async def get_block_structure(height=1495600):
    """Get and print the detailed structure of a block"""
    try:
        logger.info(f"Getting block structure for height {height}")
        block_url = f"{NODE_API_BASE}/blocks/at/{height}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(block_url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Successfully retrieved block data: type={type(data)}")
                    
                    # If it's a list, check the content
                    if isinstance(data, list):
                        logger.info(f"Block data is a list with {len(data)} items")
                        if not data:
                            logger.error("Block data is an empty list")
                            return
                            
                        first_item = data[0]
                        logger.info(f"First block item type: {type(first_item)}")
                        
                        if isinstance(first_item, str):
                            # It's a list of block IDs
                            logger.info(f"Block ID: {first_item}")
                            
                            # Try to use this ID to get the full block
                            block_id = first_item
                            logger.info(f"\nUsing block ID to get full block: {block_id}")
                            full_block_url = f"{NODE_API_BASE}/blocks/{block_id}"
                            
                            async with session.get(full_block_url) as block_response:
                                if block_response.status == 200:
                                    block_data = await block_response.json()
                                    logger.info(f"Successfully retrieved full block: type={type(block_data)}")
                                    
                                    # Print the structure
                                    if isinstance(block_data, dict):
                                        logger.info("Block structure (top level keys):")
                                        for key in block_data:
                                            logger.info(f"- {key}: {type(block_data[key])}")
                                        
                                        # Detailed look at header
                                        if "header" in block_data:
                                            header = block_data["header"]
                                            logger.info(f"Header type: {type(header)}")
                                            if isinstance(header, dict):
                                                logger.info("Header structure:")
                                                for key, value in header.items():
                                                    logger.info(f"  - {key}: {value}")
                                else:
                                    logger.error(f"Failed to get full block: HTTP {block_response.status}")
                            
                            # Try to get transactions
                            logger.info(f"\nTesting transactions endpoint with block ID: {block_id}")
                            txs_url = f"{NODE_API_BASE}/blocks/{block_id}/transactions"
                            
                            async with session.get(txs_url) as txs_response:
                                if txs_response.status == 200:
                                    txs_data = await txs_response.json()
                                    logger.info(f"Successfully retrieved transactions: type={type(txs_data)}")
                                    if isinstance(txs_data, list):
                                        logger.info(f"Found {len(txs_data)} transactions")
                                        if txs_data:
                                            first_tx = txs_data[0]
                                            logger.info(f"First transaction type: {type(first_tx)}")
                                            if isinstance(first_tx, dict):
                                                logger.info("Transaction structure (top level keys):")
                                                for key in first_tx:
                                                    logger.info(f"- {key}: {type(first_tx[key])}")
                                else:
                                    logger.error(f"Failed to get transactions: HTTP {txs_response.status}")
                        elif isinstance(first_item, dict):
                            # Original handling for dict items
                            logger.info("Block structure (top level keys):")
                            for key in first_item:
                                logger.info(f"- {key}: {type(first_item[key])}")
                    elif isinstance(data, dict):
                        logger.info("Block data is a dictionary")
                        logger.info("Block structure (top level keys):")
                        for key in data:
                            logger.info(f"- {key}: {type(data[key])}")
                    else:
                        logger.error(f"Unexpected data type: {type(data)}")
                else:
                    logger.error(f"Failed to retrieve block: HTTP {response.status}")
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

async def main():
    """Run the debug script"""
    logger.info("===== Debugging Ergo Node Block Structure =====")
    
    # Test with a recent block
    await get_block_structure()
    
    logger.info("\n===== Debug completed =====")
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 