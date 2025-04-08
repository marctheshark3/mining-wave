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

# Known demurrage blocks and amounts from explorer
KNOWN_DEMURRAGE = {
    1495702: 4.9863,
    1495300: 0.8888,
    1495201: 0.3963,
    1495133: 1.6798,
    1494969: 1.1863,
    1494873: 1.4038,
    1494175: 1.185
}

async def check_block_detailed(height):
    """Check a block for demurrage payments with detailed output."""
    logger.info(f"Checking block {height} for demurrage rewards")
    
    # Get the block
    block = await get_block_by_height(height)
    if not block:
        logger.error(f"Block {height} not found")
        return False, 0.0
    
    # Get block header info
    if isinstance(block, dict) and 'header' in block:
        header = block['header']
        logger.info(f"Block timestamp: {header.get('timestamp')}")
        block_id = header.get('id')
        logger.info(f"Block ID: {block_id}")
    else:
        block_id = "unknown"
    
    # Get transactions for the block
    transactions = await get_block_transactions(block)
    if not transactions:
        logger.error(f"No transactions found in block {height}")
        return False, 0.0
    
    logger.info(f"Found {len(transactions)} transactions in block {height}")
    
    # Expected demurrage amount for this block
    expected_amount = KNOWN_DEMURRAGE.get(height, 0)
    logger.info(f"Expected demurrage amount: {expected_amount} ERG")
    
    # Check each transaction for outputs to our demurrage wallet
    total_demurrage = 0.0
    found_demurrage = False
    
    for i, tx in enumerate(transactions):
        if not isinstance(tx, dict):
            continue
            
        tx_id = tx.get('id', 'unknown')
        
        # Check outputs
        if 'outputs' in tx:
            outputs = tx['outputs']
            
            for output in outputs:
                if not isinstance(output, dict):
                    continue
                
                # Get output details
                recipient = output.get('address', 'unknown')
                value_nanoerg = output.get('value', 0)
                value_erg = value_nanoerg / 1000000000.0
                
                # Check if this is demurrage to our wallet
                if recipient == DEMURRAGE_WALLET:
                    logger.info(f"✅ DEMURRAGE FOUND in transaction {tx_id}: {value_erg} ERG")
                    total_demurrage += value_erg
                    found_demurrage = True
                elif recipient == "unknown" and abs(value_erg - expected_amount) < 0.0001:
                    # If address is unknown but amount matches expected demurrage
                    logger.info(f"⚠️ POSSIBLE DEMURRAGE in transaction {tx_id}: {value_erg} ERG (address unknown but amount matches)")
                    
    # Final result
    if found_demurrage:
        logger.info(f"✅ CONFIRMED: Block {height} contains {total_demurrage} ERG in demurrage rewards")
        
        # Check if amount matches expectation
        if abs(total_demurrage - expected_amount) < 0.0001:
            logger.info(f"✅ Amount matches expected {expected_amount} ERG")
        else:
            logger.info(f"⚠️ Amount differs from expected {expected_amount} ERG")
            
        return True, total_demurrage
    else:
        # If we have expected amount but didn't find demurrage, look for transactions with that amount
        if expected_amount > 0:
            logger.info(f"⚠️ Expected demurrage of {expected_amount} ERG but couldn't find exact wallet match")
            logger.info(f"Checking for transactions with amount {expected_amount} ERG")
            
            for i, tx in enumerate(transactions):
                if not isinstance(tx, dict) or 'outputs' not in tx:
                    continue
                    
                for output in tx['outputs']:
                    if not isinstance(output, dict):
                        continue
                        
                    value_nanoerg = output.get('value', 0)
                    value_erg = value_nanoerg / 1000000000.0
                    
                    if abs(value_erg - expected_amount) < 0.0001:
                        logger.info(f"⚠️ Found transaction with matching amount: {value_erg} ERG to {output.get('address', 'unknown')}")
        
        logger.info(f"❌ No confirmed demurrage found in block {height}")
        return False, 0.0

async def main():
    """Run checks on known demurrage blocks."""
    logger.info("===== Verifying Known Demurrage Blocks =====")
    
    results = []
    
    # Check each known demurrage block
    for height, expected_amount in KNOWN_DEMURRAGE.items():
        logger.info(f"\n----- Checking Block {height} (Expected: {expected_amount} ERG) -----")
        found, amount = await check_block_detailed(height)
        results.append((height, expected_amount, found, amount))
        
    # Summary
    logger.info("\n===== SUMMARY =====")
    successes = sum(1 for _, _, found, _ in results if found)
    logger.info(f"Successfully verified {successes} out of {len(results)} blocks")
    
    for height, expected, found, actual in results:
        status = "✅ MATCH" if found and abs(expected - actual) < 0.0001 else "❌ FAIL"
        logger.info(f"Block {height}: {status} (Expected: {expected} ERG, Found: {actual if found else 'None'} ERG)")
    
    logger.info("===== Verification completed =====")

if __name__ == "__main__":
    asyncio.run(main()) 