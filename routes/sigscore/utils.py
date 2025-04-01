# routes/sigscore/utils.py
from typing import Dict, Any, Optional
from datetime import datetime
from utils.logging import logger

def safe_float(value: Any, default: float = 0.0) -> float:
    """Convert a value to float safely, handling extreme values"""
    try:
        num = float(value)
        if abs(num) > 1e308 or (num != 0 and abs(num) < 1e-308):
            return default
        return num
    except (TypeError, ValueError):
        return default

def format_worker_data(row: Dict[str, Any]) -> Dict[str, Any]:
    """Format worker data for API response"""
    return {
        "worker": row['worker'],
        "hashrate": safe_float(row['hashrate']),
        "shares": safe_float(row['sharespersecond'])
    }

def format_miner_data(row: Dict[str, Any]) -> Dict[str, Any]:
    """Format miner data for API response"""
    return {
        "address": row['miner'],
        "hashrate": safe_float(row['total_hashrate']),
        "sharesPerSecond": safe_float(row['total_sharespersecond']),
        "lastStatTime": row['last_stat_time'].isoformat(),
        "last_block_found": row['last_block_found'].isoformat() if row['last_block_found'] else None
    }

def format_timestamp(dt: Optional[datetime]) -> Optional[str]:
    """Format datetime to ISO string if not None"""
    return dt.isoformat() if dt else None