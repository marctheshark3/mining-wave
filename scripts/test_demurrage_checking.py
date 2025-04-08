#!/usr/bin/env python3
import sys
import os
import asyncio
import logging

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import our utils
from utils.blockchain import get_demurrage_for_block, DEMURRAGE_WALLET

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_demurrage_checking(height=1495600):
    """Test demurrage checking for a block."""
    logger.info(f"Testing demurrage checking for block at height {height}")
    
    # Check for demurrage
    has_demurrage, amount = await get_demurrage_for_block(height)
    
    logger.info(f"Demurrage wallet address: {DEMURRAGE_WALLET}")
    logger.info(f"Block {height} has demurrage: {has_demurrage}")
    
    if has_demurrage:
        logger.info(f"Demurrage amount: {amount} ERG")
    else:
        logger.info("No demurrage found in this block")
    
    return has_demurrage, amount

async def main():
    """Run the demurrage checking test."""
    logger.info("===== Testing Demurrage Checking =====")
    
    # Try with a known block height
    await test_demurrage_checking(1495600)
    
    # Try with a few more recent blocks
    for i in range(1495700, 1495702):
        await test_demurrage_checking(i)
    
    logger.info("===== Testing completed =====")

if __name__ == "__main__":
    asyncio.run(main()) 