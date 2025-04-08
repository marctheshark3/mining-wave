import aiohttp
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import logging
import asyncio
import os

logger = logging.getLogger(__name__)

# Ergo blockchain explorer API base URL
EXPLORER_API_BASE = "https://api.ergoplatform.com/api/v1"
# Local node API endpoint - updated to use Docker host gateway
NODE_API_BASE = "http://host.docker.internal:9053"
# Demurrage wallet address for the mining pool
DEMURRAGE_WALLET = "9fE5o7913CKKe6wvNgM11vULjTuKiopPcvCaj7t2zcJWXM2gcLu"
# Maximum retries for API requests
MAX_RETRIES = 3
# Flag to track if local node is available
LOCAL_NODE_AVAILABLE = True

async def get_address_transactions(address: str, limit: int = 20, offset: int = 0) -> Dict[str, Any]:
    """
    Get transactions related to a specific address.
    
    Args:
        address: The Ergo blockchain address
        limit: Maximum number of transactions to fetch
        offset: Offset for pagination
        
    Returns:
        Dictionary containing transaction data
    """
    url = f"{EXPLORER_API_BASE}/addresses/{address}/transactions?limit={limit}&offset={offset}"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    logger.error(f"Error fetching address transactions: {response.status}")
                    return {"items": [], "total": 0}
                
                data = await response.json()
                return data
        except Exception as e:
            logger.error(f"Error in get_address_transactions: {str(e)}")
            return {"items": [], "total": 0}

async def get_address_balance(address: str) -> Dict[str, Any]:
    """
    Get the current balance for an address.
    
    Args:
        address: The Ergo blockchain address
        
    Returns:
        Dictionary containing balance information
    """
    url = f"{EXPLORER_API_BASE}/addresses/{address}/balance/confirmed"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    logger.error(f"Error fetching address balance: {response.status}")
                    return {"nanoErgs": 0}
                
                data = await response.json()
                return data
        except Exception as e:
            logger.error(f"Error in get_address_balance: {str(e)}")
            return {"nanoErgs": 0}

async def get_transaction_details(tx_id: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a transaction.
    
    Args:
        tx_id: Transaction ID
        
    Returns:
        Dictionary containing transaction information or None if not found
    """
    # Use multiple API endpoints to try to get the transaction, prioritizing local node
    endpoints = [
        f"{NODE_API_BASE}/transactions/{tx_id}",       # Local node - primary
        f"{EXPLORER_API_BASE}/transactions/{tx_id}"    # Explorer API - backup
    ]
    
    for endpoint in endpoints:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status != 404:  # Only log non-404 errors to reduce noise
                        logger.warning(f"Error fetching transaction {tx_id} from {endpoint}: {response.status}")
        except Exception as e:
            # Local node errors are more important to log
            if endpoint.startswith(NODE_API_BASE):
                logger.warning(f"Error with local node when fetching transaction {tx_id}: {str(e)}")
            else:
                logger.debug(f"Exception fetching transaction {tx_id} from {endpoint}: {str(e)}")
    
    # No need to log 404s for transactions as they're often expected
    return None

async def get_block_by_height(height):
    """Get block by height from API."""
    global LOCAL_NODE_AVAILABLE
    
    try:
        # Only try the local node if we haven't determined it's unavailable
        if LOCAL_NODE_AVAILABLE:
            try:
                # Try the local node API first
                local_url = f"{NODE_API_BASE}/blocks/at/{height}"
                async with aiohttp.ClientSession() as session:
                    async with session.get(local_url, timeout=2.0) as response:
                        if response.status == 200:
                            data = await response.json()
                            logger.debug(f"Received block data from local node: type={type(data)}")
                            
                            if isinstance(data, list) and len(data) > 0:
                                # List of block ids, need to get the full block
                                block_id = data[0]
                                if isinstance(block_id, str):
                                    logger.debug(f"Retrieved block id: {block_id}, getting full block details")
                                    
                                    # Get the full block using the block id
                                    block_url = f"{NODE_API_BASE}/blocks/{block_id}"
                                    async with session.get(block_url, timeout=2.0) as block_response:
                                        if block_response.status == 200:
                                            block_data = await block_response.json()
                                            # Add the block ID at the top level for convenience
                                            if isinstance(block_data, dict) and 'id' not in block_data and 'header' in block_data:
                                                if isinstance(block_data['header'], dict) and 'id' in block_data['header']:
                                                    block_data['id'] = block_data['header']['id']
                                            return block_data
                                        else:
                                            logger.debug(f"Failed to get full block details: HTTP {block_response.status}")
                                else:
                                    logger.debug(f"Block id is not a string: {block_id}")
                            elif isinstance(data, dict):
                                # Already have the full block
                                # Add the block ID at the top level for convenience
                                if 'id' not in data and 'header' in data:
                                    if isinstance(data['header'], dict) and 'id' in data['header']:
                                        data['id'] = data['header']['id']
                                return data
                            else:
                                logger.debug(f"Unexpected block data format: {type(data)}")
                        else:
                            logger.debug(f"Failed to get block from local node: HTTP {response.status}")
            except asyncio.TimeoutError:
                # If we timeout, mark the node as unavailable to avoid future attempts
                logger.warning("Local node connection timed out, will use Explorer API for subsequent requests")
                LOCAL_NODE_AVAILABLE = False
            except Exception as e:
                # If we get a connection error, mark the node as unavailable
                if "Cannot connect to host" in str(e):
                    logger.warning("Local node connection failed, will use Explorer API for subsequent requests")
                    LOCAL_NODE_AVAILABLE = False
                else:
                    logger.debug(f"Error with local node: {str(e)}")
        
        # Fall back to explorer API
        if not LOCAL_NODE_AVAILABLE:
            logger.debug(f"Using explorer API for block height {height}")
        else:
            logger.debug(f"Falling back to explorer API for block height {height}")
        
        # According to Explorer API documentation, the correct endpoint is:
        # GET /blocks?height={height}
        explorer_url = f"{EXPLORER_API_BASE}/blocks?height={height}"
        
        for i in range(MAX_RETRIES):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(explorer_url) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            # The response should be a dict with 'items' key containing an array of blocks
                            if isinstance(data, dict) and 'items' in data and len(data['items']) > 0:
                                logger.info(f"Successfully retrieved block {height} from Explorer API")
                                
                                # Log the structure of the returned block data
                                block = data['items'][0]
                                logger.info(f"Block keys: {list(block.keys())}")
                                
                                # Ensure we have an ID at the top level
                                if 'id' not in block and 'header' in block and isinstance(block['header'], dict) and 'id' in block['header']:
                                    block['id'] = block['header']['id']
                                    logger.info(f"Added top-level ID from header: {block['id']}")
                                
                                # Always log the ID we're going to use
                                if 'id' in block:
                                    logger.info(f"Block {height} ID: {block['id']}")
                                
                                return block  # Return the first matching block
                            else:
                                logger.debug(f"Explorer API response for block {height} had unexpected format: {type(data)}")
                                # Log the entire response for debugging if it's not too large
                                if len(str(data)) < 1000:
                                    logger.info(f"Response data: {data}")
                        else:
                            # Log the actual response content for debugging
                            try:
                                error_content = await response.text()
                                logger.debug(f"Explorer API request failed with status {response.status}: {error_content[:200]}")
                            except:
                                logger.debug(f"Explorer API request failed with status {response.status}")
                            
                            if i < MAX_RETRIES - 1:  # Don't sleep on the last attempt
                                await asyncio.sleep(2 ** i)  # Exponential backoff
            except Exception as e:
                logger.debug(f"Explorer API request attempt {i+1} failed: {str(e)}")
                if i < MAX_RETRIES - 1:  # Don't sleep on the last attempt
                    await asyncio.sleep(2 ** i)  # Exponential backoff
        
        # If the latest blocks aren't available on the Explorer yet, try to get the latest height
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{EXPLORER_API_BASE}/info") as response:
                    if response.status == 200:
                        info = await response.json()
                        latest_height = info.get('height')
                        if latest_height and latest_height < height:
                            logger.warning(f"The requested block {height} is beyond the Explorer's latest height ({latest_height})")
                            return None
        except Exception as e:
            logger.debug(f"Failed to get Explorer info: {str(e)}")
        
        logger.warning(f"Failed to get block at height {height} after {MAX_RETRIES} retries")
        return None
    except Exception as e:
        logger.error(f"Error getting block at height {height}: {str(e)}")
        return None

def nano_ergs_to_ergs(nano_ergs: int) -> float:
    """Convert nano ERGs to ERGs."""
    return nano_ergs / 1_000_000_000.0

def format_timestamp(timestamp: int) -> str:
    """Format a Unix timestamp to ISO format."""
    return datetime.utcfromtimestamp(timestamp / 1000).isoformat() + "Z"

async def get_demurrage_for_block(block_height, demurrage_wallet=DEMURRAGE_WALLET):
    """
    Check if a block contains a demurrage payment.
    
    Args:
        block_height: Height of the block to check
        demurrage_wallet: Wallet address to check for demurrage (defaults to pool's demurrage wallet)
    
    Returns:
        tuple: (found, amount) where found is a boolean indicating if demurrage was found,
               and amount is the amount of the demurrage in ERG.
    """
    try:
        # Check for saved known demurrage records
        records_file = os.path.join(os.path.dirname(__file__), '../data/demurrage_records.json')
        known_amount = None
        
        # Load known demurrage amounts from records file if it exists
        if os.path.exists(records_file):
            try:
                with open(records_file, 'r') as f:
                    records = json.load(f)
                    if "demurrage_blocks" in records and str(block_height) in records["demurrage_blocks"]:
                        known_data = records["demurrage_blocks"][str(block_height)]
                        known_amount = known_data.get("amount")
                        logger.info(f"Found known demurrage for block {block_height} in records: {known_amount} ERG")
            except Exception as e:
                logger.warning(f"Error loading demurrage records: {str(e)}")
        
        # Get the block
        block = await get_block_by_height(block_height)
        if not block:
            logger.warning(f"Block {block_height} not found")
            return False, 0.0
            
        # Get transactions for the block
        transactions = await get_block_transactions(block)
        if not transactions:
            logger.warning(f"No transactions found in block {block_height}")
            return False, 0.0
            
        # Check if any transaction has outputs to our demurrage wallet
        demurrage_amount = 0.0
        found_by_address = False
        
        # Step 1: Try to find by exact wallet address match
        for tx in transactions:
            if not isinstance(tx, dict) or 'outputs' not in tx:
                continue
                
            for output in tx['outputs']:
                if not isinstance(output, dict):
                    continue
                    
                # Check if this output goes to our demurrage wallet
                recipient = output.get('address')
                if recipient and recipient == demurrage_wallet:
                    # Calculate the value in ERG (value is in nanoERG)
                    value_nanoerg = output.get('value', 0)
                    value_erg = value_nanoerg / 1000000000.0
                    demurrage_amount += value_erg
                    found_by_address = True
                    logger.info(f"Found demurrage by address match in block {block_height}: {value_erg} ERG")
        
        # If we found by address, return that amount
        if found_by_address and demurrage_amount > 0:
            logger.info(f"Found demurrage in block {block_height} by address match: {demurrage_amount} ERG")
            return True, demurrage_amount
            
        # Step 2: If no address match but we have a known amount from records, look for that amount
        if known_amount:
            logger.info(f"Looking for known demurrage amount in block {block_height}: {known_amount} ERG")
            
            # Search for this exact amount in transactions
            for tx in transactions:
                if not isinstance(tx, dict) or 'outputs' not in tx:
                    continue
                    
                for output in tx['outputs']:
                    if not isinstance(output, dict):
                        continue
                        
                    value_nanoerg = output.get('value', 0)
                    value_erg = value_nanoerg / 1000000000.0
                    
                    # Match within a small margin of error
                    if abs(value_erg - known_amount) < 0.0001:
                        logger.info(f"Found demurrage payment in block {block_height} by amount match: {value_erg} ERG")
                        return True, value_erg
        
        # Step 3: If no exact match, try to detect by pattern
        # Demurrage payments typically end with .x25 or .x75
        for tx in transactions:
            if not isinstance(tx, dict) or 'outputs' not in tx:
                continue
                
            for output in tx['outputs']:
                if not isinstance(output, dict):
                    continue
                    
                value_nanoerg = output.get('value', 0)
                value_erg = value_nanoerg / 1000000000.0
                
                # Check if this could be a demurrage payment
                last_digits = int((value_erg * 10000) % 100)
                if last_digits == 25 or last_digits == 75:
                    recipient = output.get('address', 'unknown')
                    
                    # Only consider if the recipient is unknown (means it could be our wallet)
                    # or if it matches our wallet address
                    if recipient == 'unknown' or recipient == demurrage_wallet:
                        logger.info(f"Found potential demurrage in block {block_height} by pattern: {value_erg} ERG")
                        return True, value_erg
        
        # If no matches found
        logger.debug(f"No demurrage found in block {block_height}")
        return False, 0.0
    except Exception as e:
        logger.error(f"Error checking demurrage for block {block_height}: {str(e)}")
        return False, 0.0

async def get_block_transactions(block_data):
    """Get transactions for a block."""
    global LOCAL_NODE_AVAILABLE
    
    try:
        # First, extract the block ID
        block_id = None
        
        # Add detailed debugging of the block data structure
        if isinstance(block_data, dict):
            logger.info(f"Block data keys: {list(block_data.keys())}")
            if 'height' in block_data:
                logger.info(f"Processing block height: {block_data['height']}")
            
            if 'id' in block_data:
                block_id = block_data['id']
                logger.info(f"Found block ID directly in block data: {block_id}")
            elif 'header' in block_data and isinstance(block_data['header'], dict):
                logger.info(f"Header keys: {list(block_data['header'].keys())}")
                if 'id' in block_data['header']:
                    block_id = block_data['header']['id']
                    logger.info(f"Found block ID in header: {block_id}")
        else:
            logger.warning(f"Unexpected block data type: {type(block_data)}")
        
        if not block_id:
            logger.error("No block ID found in block data")
            # Add full block data dump for debugging if it's not too large
            if isinstance(block_data, dict) and len(str(block_data)) < 1000:
                logger.error(f"Block data dump: {block_data}")
            return None
            
        logger.info(f"Getting transactions for block ID: {block_id}")
        
        # Check if transactions are already included in block_data
        if 'blockTransactions' in block_data and 'transactions' in block_data['blockTransactions']:
            logger.debug("Transactions found in block data")
            return block_data['blockTransactions']['transactions']
            
        # Try local node API only if it's available
        if LOCAL_NODE_AVAILABLE:
            try:
                local_url = f"{NODE_API_BASE}/blocks/{block_id}/transactions"
                async with aiohttp.ClientSession() as session:
                    async with session.get(local_url, timeout=2.0) as response:
                        if response.status == 200:
                            data = await response.json()
                            # Handle different response formats
                            if isinstance(data, dict) and 'transactions' in data:
                                # Handle the format {"headerId": "...", "transactions": [...]}
                                logger.debug(f"Retrieved {len(data['transactions'])} transactions from local node")
                                return data['transactions']
                            elif isinstance(data, list):
                                logger.debug(f"Retrieved {len(data)} transactions from local node")
                                return data
                            else:
                                logger.debug(f"Local node returned unexpected data type: {type(data)}")
                        else:
                            logger.debug(f"Failed to get transactions from local node: HTTP {response.status}")
            except asyncio.TimeoutError:
                # If we timeout, mark the node as unavailable to avoid future attempts
                logger.warning("Local node connection timed out, will use Explorer API for subsequent requests")
                LOCAL_NODE_AVAILABLE = False
            except Exception as e:
                # If we get a connection error, mark the node as unavailable
                if "Cannot connect to host" in str(e):
                    logger.warning("Local node connection failed, will use Explorer API for subsequent requests")
                    LOCAL_NODE_AVAILABLE = False
                else:
                    logger.debug(f"Error with local node: {str(e)}")
        
        # Fall back to explorer API
        if not LOCAL_NODE_AVAILABLE:
            logger.debug(f"Using explorer API for block transactions")
        else:
            logger.debug(f"Falling back to explorer API for block transactions")
            
        # According to Explorer API documentation, the correct endpoint is:
        # GET /blocks/{blockId}/transactions
        explorer_url = f"{EXPLORER_API_BASE}/blocks/{block_id}/transactions"
        
        for i in range(MAX_RETRIES):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(explorer_url) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            # Handle different response formats
                            if isinstance(data, dict) and 'transactions' in data:
                                # Handle the format {"headerId": "...", "transactions": [...]}
                                logger.info(f"Retrieved {len(data['transactions'])} transactions from explorer")
                                return data['transactions']
                            # According to the API docs, this endpoint might return transactions directly
                            elif isinstance(data, list):
                                logger.info(f"Retrieved {len(data)} transactions from explorer")
                                return data
                            # Backward compatibility check
                            elif isinstance(data, dict) and 'items' in data:
                                logger.info(f"Retrieved {len(data['items'])} transactions from explorer (items format)")
                                return data['items']
                            else:
                                logger.warning(f"Explorer returned unexpected data type: {type(data)}")
                                return None
                        else:
                            # Log the actual response content for debugging
                            try:
                                error_content = await response.text()
                                logger.debug(f"Explorer API request failed with status {response.status}: {error_content[:200]}")
                            except:
                                logger.debug(f"Explorer API request failed with status {response.status}")
                            
                            if i < MAX_RETRIES - 1:
                                await asyncio.sleep(2 ** i)  # Exponential backoff
            except Exception as e:
                logger.debug(f"Explorer API request attempt {i+1} failed: {str(e)}")
                if i < MAX_RETRIES - 1:
                    await asyncio.sleep(2 ** i)  # Exponential backoff
        
        # If we couldn't get transactions with the block ID, try an alternative approach:
        # Check if we can get block transactions directly from the blockTransactions endpoint
        if isinstance(block_data, dict) and 'height' in block_data:
            height = block_data['height']
            logger.info(f"Attempting to get transactions directly for block at height {height}")
            
            try:
                # Try the blockTransactions endpoint with the block height
                alt_url = f"{EXPLORER_API_BASE}/blocks/at/{height}/transactions"
                async with aiohttp.ClientSession() as session:
                    async with session.get(alt_url) as response:
                        if response.status == 200:
                            data = await response.json()
                            if isinstance(data, list):
                                logger.info(f"Retrieved {len(data)} transactions from alternative endpoint")
                                return data
                            elif isinstance(data, dict) and 'items' in data:
                                logger.info(f"Retrieved {len(data['items'])} transactions from alternative endpoint (items format)")
                                return data['items']
                            elif isinstance(data, dict) and 'transactions' in data:
                                logger.info(f"Retrieved {len(data['transactions'])} transactions from alternative endpoint (transactions format)")
                                return data['transactions']
                            else:
                                logger.warning(f"Alternative endpoint returned unexpected data type: {type(data)}")
            except Exception as e:
                logger.debug(f"Alternative transaction lookup failed: {str(e)}")
        
        logger.warning(f"Failed to get transactions for block {block_id} after {MAX_RETRIES} retries")
        return None
    except Exception as e:
        logger.error(f"Error getting transactions for block: {str(e)}")
        return None 