# routes/miningcore/utils.py
from typing import Dict, Any, Optional, Tuple
from utils.logging import logger
from decimal import Decimal

# Constants
DEMURRAGE_WALLET = "9fE5o7913CKKe6wvNgM11vULjTuKiopPcvCaj7t2zcJWXM2gcLu"

def format_block_data(row: Dict[str, Any], effort: float, demurrage_info: Optional[Tuple[Decimal, Dict[str, int]]] = None) -> Dict[str, Any]:
    """Format block data for API response"""
    demurrage_erg = demurrage_info[0] if demurrage_info else Decimal(0)
    demurrage_tokens = demurrage_info[1] if demurrage_info else {}
    return {
        "created": row['created'].isoformat(),
        "blockheight": row['blockheight'],
        "effort": effort,
        "reward": float(row['reward']) if row['reward'] else 0,
        "confirmationprogress": float(row['confirmationprogress']) if row['confirmationprogress'] else 0,
        "demurrageErg": float(demurrage_erg), # Keep the API consistent with float for now
        "demurrageTokens": demurrage_tokens,
        "miner": row.get('miner')
    }

def format_payment_data(row: Dict[str, Any]) -> Dict[str, Any]:
    """Format payment data for API response"""
    return {
        "created": row['created'].isoformat(),
        "amount": float(row['amount']),
        "tx_id": row['transactionconfirmationdata']
    }

def format_share_data(row: Dict[str, Any]) -> Dict[str, Any]:
    """Format share data for API response"""
    return {
        "miner": row['miner'],
        "shares": float(row['shares']),
        "last_share": row['last_share'].isoformat() if row['last_share'] else None
    }

def get_address_column(table_name: str) -> str:
    """Get the appropriate address column name for a given table"""
    from .queries import ADDRESS_COLUMNS
    return ADDRESS_COLUMNS.get(table_name, "address")

def handle_db_error(operation: str, error: Exception) -> None:
    """Handle database errors consistently"""
    error_msg = f"Error during {operation}: {str(error)}"
    logger.error(error_msg)
    return error_msg