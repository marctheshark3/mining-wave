#!/usr/bin/env python3
import sys
import os
import asyncio
import logging
import json

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import our utils
from utils.blockchain import get_block_by_height, get_block_transactions, DEMURRAGE_WALLET

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def examine_block_transactions(height=1495702):
    """Examine all transactions in a block in detail."""
    logger.info(f"Examining all transactions in block {height}")
    logger.info(f"Demurrage wallet address: {DEMURRAGE_WALLET}")
    
    # Get the block
    block = await get_block_by_height(height)
    if not block:
        logger.error(f"Block {height} not found")
        return None
    
    # Get block header info
    if isinstance(block, dict) and 'header' in block:
        header = block['header']
        logger.info(f"Block timestamp: {header.get('timestamp')}")
        logger.info(f"Block ID: {header.get('id')}")
    
    # Get transactions for the block
    transactions = await get_block_transactions(block)
    if not transactions:
        logger.error(f"No transactions found in block {height}")
        return None
    
    logger.info(f"Found {len(transactions)} transactions in block {height}")
    
    # Check each transaction for any outputs
    found_demurrage = False
    
    for i, tx in enumerate(transactions):
        if not isinstance(tx, dict):
            logger.warning(f"Transaction {i} is not a dictionary")
            continue
        
        tx_id = tx.get('id', 'unknown')
        logger.info(f"\nTransaction {i+1}: {tx_id}")
        
        # Check inputs/outputs
        if 'inputs' in tx:
            logger.info(f"  Inputs: {len(tx['inputs'])}")
        
        if 'outputs' in tx:
            outputs = tx['outputs']
            logger.info(f"  Outputs: {len(outputs)}")
            
            # Check each output
            for j, output in enumerate(outputs):
                if not isinstance(output, dict):
                    continue
                
                # Get output details
                recipient = output.get('address', 'unknown')
                value_nanoerg = output.get('value', 0)
                value_erg = value_nanoerg / 1000000000.0
                
                logger.info(f"    Output {j+1}: {value_erg} ERG to {recipient}")
                
                # Check if this is demurrage
                if recipient == DEMURRAGE_WALLET:
                    logger.info(f"    ✅ DEMURRAGE FOUND: {value_erg} ERG")
                    found_demurrage = True
    
    if not found_demurrage:
        logger.info("\n❌ No demurrage found in any transaction in this block")
    
    return transactions

async def main():
    """Run the examination."""
    logger.info("===== Examining Block Transactions =====")
    await examine_block_transactions(1495702)
    logger.info("===== Examination completed =====")

if __name__ == "__main__":
    asyncio.run(main()) 