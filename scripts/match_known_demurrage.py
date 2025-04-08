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

# Known demurrage amounts by block height from blockchain explorer
KNOWN_DEMURRAGE = {
    1495702: 4.9863,
    1495300: 0.8888,
    1495201: 0.3963,
    1495133: 1.6798,
    1494969: 1.1863,
    1494873: 1.4038,
    1494175: 1.185
}

async def find_demurrage_in_block(height, expected_amount):
    """Find demurrage transaction in a block using amount matching."""
    logger.info(f"Checking block {height} for demurrage amount of {expected_amount} ERG")
    
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
    
    # Check each transaction for amounts matching the expected demurrage
    for tx_idx, tx in enumerate(transactions):
        if not isinstance(tx, dict) or 'outputs' not in tx:
            continue
            
        tx_id = tx.get('id', 'unknown')
        outputs = tx['outputs']
        
        for output_idx, output in enumerate(outputs):
            if not isinstance(output, dict):
                continue
            
            # Calculate the value in ERG (value is in nanoERG)
            value_nanoerg = output.get('value', 0)
            value_erg = value_nanoerg / 1000000000.0
            recipient = output.get('address', 'unknown')
            
            # Check if value is close to expected (within 0.0001 ERG)
            if abs(value_erg - expected_amount) < 0.0001 or abs(value_erg - round(expected_amount * 100) / 100) < 0.0001:
                logger.info(f"✅ FOUND MATCH: Transaction {tx_id}, output {output_idx+1}")
                logger.info(f"   Amount: {value_erg} ERG")
                logger.info(f"   Recipient: {recipient}")
                
                if recipient == DEMURRAGE_WALLET:
                    logger.info(f"   ✅ Recipient matches expected demurrage wallet")
                elif recipient == 'unknown':
                    logger.info(f"   ⚠️ Recipient unknown, but amount matches expected demurrage")
                
                # Return the actual amount found
                return True, value_erg
    
    logger.error(f"❌ No matching amount found in block {height}")
    return False, 0.0

async def main():
    """Run the demurrage matching checks."""
    logger.info("===== Matching Known Demurrage Amounts =====")
    
    results = []
    
    for height, expected_amount in KNOWN_DEMURRAGE.items():
        logger.info(f"\n----- Block {height} (Expected: {expected_amount} ERG) -----")
        found, actual_amount = await find_demurrage_in_block(height, expected_amount)
        results.append((height, expected_amount, found, actual_amount))
    
    # Summary
    logger.info("\n===== SUMMARY =====")
    successes = sum(1 for _, _, found, _ in results if found)
    logger.info(f"Successfully found matching amounts in {successes} out of {len(results)} blocks")
    
    for height, expected, found, actual in results:
        status = "✅ MATCH" if found else "❌ FAIL"
        amount_info = f"{actual} ERG" if found else "None"
        diff = f" (diff: {abs(actual - expected):.6f})" if found else ""
        logger.info(f"Block {height}: {status} - Expected: {expected} ERG, Found: {amount_info}{diff}")
    
    logger.info("===== Matching completed =====")

if __name__ == "__main__":
    asyncio.run(main()) 