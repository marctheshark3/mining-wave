#!/usr/bin/env python3
import sys
import os
import asyncio
import logging
import json
import time
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import our utils
from utils.blockchain import get_block_by_height, get_demurrage_for_block, DEMURRAGE_WALLET

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set blockchain module to WARNING level to reduce connection error logs
logging.getLogger("utils.blockchain").setLevel(logging.WARNING)

# File to store demurrage records
DEMURRAGE_RECORDS_FILE = os.path.join(os.path.dirname(__file__), '../data/demurrage_records.json')

# Ensure data directory exists at startup
os.makedirs(os.path.dirname(DEMURRAGE_RECORDS_FILE), exist_ok=True)

async def get_latest_block_height():
    """Get the current blockchain height."""
    try:
        # Use a placeholder URL for node status
        from utils.blockchain import NODE_API_BASE
        url = f"{NODE_API_BASE}/info"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'fullHeight' in data:
                        return data['fullHeight']
                    else:
                        logger.error("Full height not found in node info")
                else:
                    logger.error(f"Failed to get node info: HTTP {response.status}")
        
        # Fallback to explorer API
        from utils.blockchain import EXPLORER_API_BASE
        url = f"{EXPLORER_API_BASE}/blocks?limit=1"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'items' in data and len(data['items']) > 0:
                        return data['items'][0]['height']
                    else:
                        logger.error("No blocks found in explorer response")
                else:
                    logger.error(f"Failed to get explorer blocks: HTTP {response.status}")
        
        return None
    except Exception as e:
        logger.error(f"Error getting latest block height: {str(e)}")
        return None

def load_demurrage_records():
    """Load the demurrage records from file."""
    try:
        if os.path.exists(DEMURRAGE_RECORDS_FILE):
            with open(DEMURRAGE_RECORDS_FILE, 'r') as f:
                return json.load(f)
        else:
            # Create the directory if it doesn't exist
            os.makedirs(os.path.dirname(DEMURRAGE_RECORDS_FILE), exist_ok=True)
            # Return empty records structure
            return {"last_checked_height": 0, "demurrage_blocks": {}}
    except Exception as e:
        logger.error(f"Error loading demurrage records: {str(e)}")
        return {"last_checked_height": 0, "demurrage_blocks": {}}

def save_demurrage_records(records):
    """Save the demurrage records to file."""
    try:
        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(DEMURRAGE_RECORDS_FILE), exist_ok=True)
        
        with open(DEMURRAGE_RECORDS_FILE, 'w') as f:
            json.dump(records, f, indent=2)
        logger.info(f"Demurrage records saved to {DEMURRAGE_RECORDS_FILE}")
    except Exception as e:
        logger.error(f"Error saving demurrage records: {str(e)}")

async def check_block_range(start_height, end_height, records):
    """Check a range of blocks for demurrage payments."""
    new_demurrage_found = False
    
    for height in range(start_height, end_height + 1):
        # Check if we've already recorded this block
        if str(height) in records["demurrage_blocks"]:
            logger.debug(f"Block {height} already checked and recorded")
            continue
        
        logger.info(f"Checking block {height} for demurrage")
        found, amount = await get_demurrage_for_block(height, DEMURRAGE_WALLET)
        
        if found:
            # Record the demurrage block
            timestamp = datetime.now().isoformat()
            records["demurrage_blocks"][str(height)] = {
                "height": height,
                "amount": amount,
                "timestamp": timestamp,
                "wallet": DEMURRAGE_WALLET
            }
            logger.info(f"✅ Found demurrage in block {height}: {amount} ERG")
            new_demurrage_found = True
        else:
            logger.debug(f"❌ No demurrage found in block {height}")
        
        # Update the last checked height
        records["last_checked_height"] = max(records["last_checked_height"], height)
    
    # Return whether new demurrage was found
    return new_demurrage_found

async def monitor_blockchain(interval=60, check_blocks=10):
    """
    Monitor the blockchain for demurrage payments.
    
    Args:
        interval: How often to check for new blocks (in seconds)
        check_blocks: How many recent blocks to check at a time
    """
    logger.info(f"Starting demurrage monitor, checking every {interval} seconds")
    
    while True:
        try:
            # Load the current records
            records = load_demurrage_records()
            
            # Get the latest block height
            latest_height = await get_latest_block_height()
            if not latest_height:
                logger.error("Failed to get latest block height, retrying in 30 seconds...")
                await asyncio.sleep(30)
                continue
            
            # Calculate which blocks to check
            last_checked = records["last_checked_height"]
            start_height = last_checked + 1
            end_height = min(latest_height, start_height + check_blocks - 1)
            
            if start_height > latest_height:
                logger.info(f"No new blocks to check (last checked: {last_checked}, latest: {latest_height})")
            else:
                logger.info(f"Checking blocks {start_height} to {end_height} (latest: {latest_height})")
                
                # Check the blocks
                new_found = await check_block_range(start_height, end_height, records)
                
                # Save the updated records
                save_demurrage_records(records)
                
                if new_found:
                    logger.info("✅ New demurrage payments found and recorded!")
                else:
                    logger.info("No new demurrage payments found in this block range")
            
            # Wait for the next interval
            logger.info(f"Next check in {interval} seconds...")
            await asyncio.sleep(interval)
        
        except Exception as e:
            logger.error(f"Error in monitor loop: {str(e)}")
            logger.info("Retrying in 30 seconds...")
            await asyncio.sleep(30)

async def summarize_demurrage():
    """Summarize all known demurrage payments."""
    records = load_demurrage_records()
    
    if not records["demurrage_blocks"]:
        logger.info("No demurrage blocks recorded yet")
        return
    
    logger.info("\n===== DEMURRAGE SUMMARY =====")
    logger.info(f"Total demurrage blocks: {len(records['demurrage_blocks'])}")
    
    total_amount = 0.0
    blocks = []
    
    # Convert to list for sorting
    for height_str, data in records["demurrage_blocks"].items():
        height = int(height_str)
        amount = data["amount"]
        total_amount += amount
        timestamp = data.get("timestamp", "unknown")
        blocks.append((height, amount, timestamp))
    
    # Sort by height (newest first)
    blocks.sort(reverse=True)
    
    logger.info(f"Total demurrage received: {total_amount:.8f} ERG")
    logger.info("\nMost recent demurrage blocks:")
    
    # Display the 10 most recent blocks
    for i, (height, amount, timestamp) in enumerate(blocks[:10]):
        try:
            dt = datetime.fromisoformat(timestamp)
            timestamp_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            timestamp_str = timestamp
            
        logger.info(f"{i+1}. Block {height}: {amount:.8f} ERG (recorded: {timestamp_str})")
    
    logger.info("===== END OF SUMMARY =====\n")

async def main():
    """Main entry point."""
    if len(sys.argv) > 1 and sys.argv[1] == "summary":
        # Just print a summary and exit
        await summarize_demurrage()
    elif len(sys.argv) > 1 and sys.argv[1] == "backfill":
        # Backfill mode - check a range of historical blocks
        logger.info("Running in backfill mode")
        
        # Load records
        records = load_demurrage_records()
        
        # Default range if not specified
        start_height = int(sys.argv[2]) if len(sys.argv) > 2 else 1494000
        end_height = int(sys.argv[3]) if len(sys.argv) > 3 else 1496000
        
        logger.info(f"Checking blocks from {start_height} to {end_height}")
        new_found = await check_block_range(start_height, end_height, records)
        
        # Save records
        save_demurrage_records(records)
        
        # Summarize
        await summarize_demurrage()
        
        if new_found:
            logger.info("✅ Found and recorded new demurrage payments!")
        else:
            logger.info("No new demurrage payments found in the specified range")
    else:
        # Monitor mode - continuously check for new blocks
        logger.info("Running in monitor mode")
        
        # Start by showing a summary
        await summarize_demurrage()
        
        # Then start monitoring
        await monitor_blockchain()

if __name__ == "__main__":
    import aiohttp  # Import here to avoid issues with asyncio
    asyncio.run(main()) 