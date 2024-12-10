# routes/sigscore/routes.py
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi_cache.decorator import cache
from database import DatabasePool
from datetime import datetime, timedelta
from typing import List, Dict, Any
import asyncpg
from utils.logging import logger
from utils.calculate import calculate_mining_effort, calculate_time_to_find_block
from utils.cache import MINER_CACHE, POOL_CACHE, WORKER_CACHE, SETTINGS_CACHE

from .models import (
    LoyalMiner, MinerSettings, MinerDetails, WorkerStats
)
from .queries import (
    LOYAL_MINERS_QUERY, MINER_DETAILS_QUERIES, ALL_MINERS_QUERY,
    TOP_MINERS_QUERY, WORKER_HISTORY_QUERY
)
from .utils import safe_float, format_worker_data, format_miner_data, format_timestamp

router = APIRouter()

class SigScoreException(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=500, detail=detail)
        logger.error(f"SigScore Error: {detail}")

async def get_connection():
    """Get database connection from pool"""
    pool = await DatabasePool.get_pool()
    async with pool.acquire() as connection:
        yield connection

@router.get("/miners/bonus", response_model=List[LoyalMiner])
@cache(expire=300, key_builder=POOL_CACHE)
async def get_weekly_loyal_miners(
    conn: asyncpg.Connection = Depends(get_connection),
    limit: int = Query(default=100, ge=1, le=1000)
) -> List[Dict[str, Any]]:
    """Get miners who have been active for at least 4 out of the last 7 days"""
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=7)
    
    try:
        rows = await conn.fetch(LOYAL_MINERS_QUERY, start_time, end_time, limit)
        
        if not rows:
            logger.info("No loyal miners found for the given criteria")
            return []
        
        return [
            LoyalMiner(
                address=row['miner'],
                days_active=row['days_active'],
                weekly_avg_hashrate=float(row['weekly_avg_hashrate']),
                current_balance=float(row['current_balance']),
                last_payment=format_timestamp(row['last_payment_date'])
            )
            for row in rows
        ]
    except Exception as e:
        logger.error(f"Error retrieving weekly loyal miners: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/history")
@cache(expire=300, key_builder=POOL_CACHE)
async def get_pool_history(conn: asyncpg.Connection = Depends(get_connection)):
    """Get pool hashrate history for the last 5 days"""
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=5)
    
    query = """
        WITH hourly_data AS (
            SELECT 
                date_trunc('hour', created) AS hour,
                worker,
                AVG(hashrate) AS avg_hashrate
            FROM minerstats
            WHERE created >= $1 AND created < $2
            GROUP BY date_trunc('hour', created), worker
        )
        SELECT 
            hour,
            SUM(avg_hashrate) AS total_hashrate
        FROM hourly_data
        GROUP BY hour
        ORDER BY hour
    """
    
    try:
        rows = await conn.fetch(query, start_time, end_time)
        return [{
            "timestamp": row['hour'].isoformat(),
            "total_hashrate": float(row['total_hashrate'])
        } for row in rows]
    except Exception as e:
        logger.error(f"Error retrieving pool history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/miners")
@cache(expire=60, key_builder=POOL_CACHE)
async def get_all_miners(
    conn: asyncpg.Connection = Depends(get_connection),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """Get list of all active miners with their current stats"""
    try:
        rows = await conn.fetch(ALL_MINERS_QUERY, limit, offset)
        return [format_miner_data(row) for row in rows]
    except Exception as e:
        logger.error(f"Error retrieving miners: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/miners/top")
@cache(expire=60, key_builder=POOL_CACHE)
async def get_top_miners(conn: asyncpg.Connection = Depends(get_connection)):
    """Get top 20 miners by hashrate"""
    try:
        rows = await conn.fetch(TOP_MINERS_QUERY)
        return [{
            "address": row['miner'],
            "hashrate": float(row['hashrate'])
        } for row in rows]
    except Exception as e:
        logger.error(f"Error retrieving top miners: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/miners/{address}", response_model=MinerDetails)
@cache(expire=30, key_builder=MINER_CACHE)
async def get_miner_details(
    address: str,
    conn: asyncpg.Connection = Depends(get_connection)
):
    """Get detailed statistics for a specific miner"""
    try:
        pool_stats = await conn.fetchrow(MINER_DETAILS_QUERIES["pool_stats"])
        
        results = {}
        for key, query in MINER_DETAILS_QUERIES.items():
            if key == "pool_stats":
                continue
            if key == "paid_today":
                results[key] = await conn.fetch(query, address, datetime.utcnow().date())
            else:
                results[key] = await conn.fetch(query, address)

        if not results["workers"]:
            raise HTTPException(status_code=404, detail=f"Miner {address} not found")

        # Calculate effort and time to find block
        current_effort = calculate_mining_effort(
            safe_float(pool_stats['networkdifficulty']),
            safe_float(pool_stats['networkhashrate']),
            safe_float(results["workers"][0]['total_hashrate']),
            results["last_block"][0]['created'].isoformat() if results["last_block"] else None
        )

        time_to_find = calculate_time_to_find_block(
            safe_float(pool_stats['networkdifficulty']),
            safe_float(pool_stats['networkhashrate']),
            safe_float(results["workers"][0]['total_hashrate'])
        )

        workers = [format_worker_data(row) for row in results["workers"]]
        balance = safe_float(results["balance"][0]["balance"]) if results["balance"] else 0.0

        return MinerDetails(
            address=address,
            balance=balance,
            current_hashrate=safe_float(results["workers"][0]['total_hashrate']),
            shares_per_second=safe_float(results["workers"][0]['total_sharespersecond']),
            effort=safe_float(current_effort),
            time_to_find=safe_float(time_to_find),
            last_block_found={
                "timestamp": results["last_block"][0]['created'].isoformat() if results["last_block"] else None,
                "block_height": results["last_block"][0]['blockheight'] if results["last_block"] else None
            },
            payments={
                "paid_today": safe_float(results["paid_today"][0]['paid_today']),
                "total_paid": safe_float(results["total_paid"][0]['total_paid']),
                "last_payment": {
                    "amount": safe_float(results["payment"][0]['amount']) if results["payment"] else 0,
                    "date": results["payment"][0]['last_payment_date'].isoformat() if results["payment"] else None,
                    "tx_id": results["payment"][0]['transactionconfirmationdata'] if results["payment"] else None
                }
            },
            workers=workers
        )
    except Exception as e:
        logger.error(f"Error retrieving miner details: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/miners/{address}/workers")
@cache(expire=60, key_builder=WORKER_CACHE)
async def get_miner_worker_history(
    address: str,
    conn: asyncpg.Connection = Depends(get_connection),
    days: int = Query(5, ge=1, le=30)
):
    """Get worker history for a specific miner"""
    try:
        rows = await conn.fetch(WORKER_HISTORY_QUERY, address, days)
        
        worker_history = {}
        for row in rows:
            worker = row['worker']
            if worker not in worker_history:
                worker_history[worker] = []
            
            # Calculate percentage change from previous hour
            pct_change = None
            if row['prev_hashrate']:
                pct_change = ((row['hashrate'] - row['prev_hashrate']) / row['prev_hashrate']) * 100
            
            worker_history[worker].append({
                "timestamp": row['timestamp'].isoformat(),
                "hashrate": float(row['hashrate']),
                "shares": float(row['shares']),
                "hashrate_change": float(pct_change) if pct_change is not None else None
            })
        
        return worker_history
    except Exception as e:
        raise SigScoreException(f"Error retrieving worker history: {str(e)}")

@router.get("/miner_setting", response_model=List[MinerSettings])
@cache(expire=300, key_builder=SETTINGS_CACHE)
async def get_all_miner_settings(
    conn: asyncpg.Connection = Depends(get_connection),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """Get settings for all miners"""
    try:
        query = """
            SELECT miner_address, minimum_payout_threshold, swapping, created_at
            FROM miner_payouts
            ORDER BY created_at DESC
            LIMIT $1 OFFSET $2
        """
        
        rows = await conn.fetch(query, limit, offset)
        return [
            MinerSettings(
                miner_address=row['miner_address'],
                minimum_payout_threshold=float(row['minimum_payout_threshold']),
                swapping=row['swapping'],
                created_at=row['created_at'].isoformat()
            )
            for row in rows
        ]
    except Exception as e:
        logger.error(f"Error retrieving miner settings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/miner_setting/{miner_address}", response_model=MinerSettings)
@cache(expire=300, key_builder=SETTINGS_CACHE)
async def get_miner_setting(
    miner_address: str,
    conn: asyncpg.Connection = Depends(get_connection)
):
    """Get settings for a specific miner"""
    try:
        query = "SELECT * FROM miner_payouts WHERE miner_address = $1"
        row = await conn.fetchrow(query, miner_address)
        
        if row is None:
            raise HTTPException(status_code=404, detail="Miner settings not found")
        
        return MinerSettings(
            miner_address=row['miner_address'],
            minimum_payout_threshold=float(row['minimum_payout_threshold']),
            swapping=row['swapping'],
            created_at=row['created_at'].isoformat()
        )
    except Exception as e:
        logger.error(f"Error retrieving miner setting: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))