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

async def check_block(height=1495702):
    """Check a specific block for demurrage rewards."""
    logger.info(f"Checking block {height} for demurrage rewards")
    logger.info(f"Using demurrage wallet address: {DEMURRAGE_WALLET}")
    
    # Check for demurrage
    has_demurrage, amount = await get_demurrage_for_block(height)
    
    if has_demurrage:
        logger.info(f"✅ FOUND DEMURRAGE: Block {height} contains {amount} ERG in demurrage rewards")
    else:
        logger.info(f"❌ NO DEMURRAGE: Block {height} does not contain demurrage rewards")
    
    return has_demurrage, amount

async def main():
    """Run the block check."""
    logger.info("===== Checking Specific Block for Demurrage =====")
    await check_block(1495702)
    logger.info("===== Check completed =====")

if __name__ == "__main__":
    asyncio.run(main()) 