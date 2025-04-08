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

async def check_blocks_range(start_height, end_height):
    """Check a range of blocks for demurrage rewards."""
    logger.info(f"Checking blocks from {start_height} to {end_height} for demurrage rewards")
    logger.info(f"Using demurrage wallet address: {DEMURRAGE_WALLET}")
    
    demurrage_blocks = []
    
    for height in range(start_height, end_height + 1):
        logger.info(f"Checking block {height}...")
        has_demurrage, amount = await get_demurrage_for_block(height)
        
        if has_demurrage:
            logger.info(f"✅ FOUND DEMURRAGE: Block {height} contains {amount} ERG in demurrage rewards")
            demurrage_blocks.append((height, amount))
        else:
            logger.info(f"Block {height}: No demurrage")
    
    # Summary
    if demurrage_blocks:
        logger.info(f"\n===== SUMMARY =====")
        logger.info(f"Found demurrage in {len(demurrage_blocks)} blocks:")
        for height, amount in demurrage_blocks:
            logger.info(f"Block {height}: {amount} ERG")
        logger.info(f"Total demurrage: {sum(amount for _, amount in demurrage_blocks)} ERG")
    else:
        logger.info(f"\n❌ No demurrage found in any blocks from {start_height} to {end_height}")
    
    return demurrage_blocks

async def main():
    """Run the block range check."""
    logger.info("===== Searching for Demurrage in Block Range =====")
    
    # Check recent blocks (adjust range as needed)
    # Default is to check the 10 blocks around the specified block
    target_block = 1495702
    start_height = target_block - 5
    end_height = target_block + 5
    
    await check_blocks_range(start_height, end_height)
    
    logger.info("===== Search completed =====")

if __name__ == "__main__":
    asyncio.run(main()) 