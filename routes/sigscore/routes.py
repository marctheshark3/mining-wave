# routes/sigscore/routes.py
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi_cache.decorator import cache
from database import DatabasePool
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import asyncpg
from utils.logging import logger
from utils.calculate import calculate_mining_effort, calculate_time_to_find_block
from utils.cache import MINER_CACHE, POOL_CACHE, WORKER_CACHE, SETTINGS_CACHE

from .models import (
    LoyalMiner, MinerSettings, MinerDetails, WorkerStats, MinerActivity, MinerParticipation, BlockParticipation, MultiBlockParticipation, MinerAverageParticipation, BlockRequest
)
from .queries import (
    LOYAL_MINERS_QUERY, MINER_DETAILS_QUERIES, ALL_MINERS_QUERY,
    TOP_MINERS_QUERY, WORKER_HISTORY_QUERY, MINER_ACTIVITY_QUERY, MINER_BONUS_DIAGNOSTIC_QUERY, BLOCK_SHARES_QUERY, DEBUG_BLOCK_DATA, MULTI_BLOCK_SHARES_QUERY, GET_RECENT_BLOCKS
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

@router.post("/miners/average-participation", response_model=MultiBlockParticipation)
@router.get("/miners/average-participation", response_model=MultiBlockParticipation)
@cache(expire=300, key_builder=MINER_CACHE)
async def get_average_block_participation(
    block_request: Optional[BlockRequest] = None,
    blocks: str = Query(None, description="Comma-separated list of block heights"),
    conn: asyncpg.Connection = Depends(get_connection)
):
    """
    Calculate average participation across multiple blocks.
    
    Can be called via:
    - POST with JSON body: {"block_heights": [1418861, 1418909]}
    - GET with query param: ?blocks=1418861,1418909
    """
    try:
        # Handle both POST and GET methods
        if blocks:
            # Parse comma-separated string for GET request
            try:
                block_heights = [int(b.strip()) for b in blocks.split(',') if b.strip()]
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid block height format. Must be comma-separated numbers."
                )
        elif block_request:
            # Use block heights from POST body
            block_heights = block_request.block_heights
        else:
            raise HTTPException(
                status_code=400,
                detail="Must provide blocks either as query parameter or in request body"
            )
            
        # Validate input
        if not block_heights:
            raise HTTPException(
                status_code=400,
                detail="Must provide at least one block height"
            )
            
        if len(block_heights) > 100:
            raise HTTPException(
                status_code=400,
                detail="Maximum of 100 blocks can be analyzed at once"
            )
            
        # Fetch participation data across all blocks
        rows = await conn.fetch(
            MULTI_BLOCK_SHARES_QUERY, 
            block_heights
        )
        
        if not rows:
            raise HTTPException(
                status_code=404,
                detail="No participation data found for the specified blocks"
            )
            
        # Process results
        miners = [
            MinerAverageParticipation(
                miner_address=row['miner'],
                avg_shares=round(row['avg_shares'], 2),
                avg_participation_percentage=round(row['avg_participation'], 4),
                total_rewards=row['total_rewards'],
                block_count=row['block_count']
            )
            for row in rows
        ]
        
        return MultiBlockParticipation(
            block_heights=block_heights,
            total_blocks=len(block_heights),
            miners=miners,
            start_timestamp=min(row['start_time'] for row in rows).isoformat(),
            end_timestamp=max(row['end_time'] for row in rows).isoformat()
        )
        
    except Exception as e:
        error_msg = str(e) if str(e) else "Unknown error occurred"
        logger.error(f"Error calculating average participation: {error_msg}")
        logger.exception("Full exception details:")
        raise HTTPException(
            status_code=500,
            detail=f"Error calculating average participation: {error_msg}"
        )

@router.get("/miners/participation/{block_height}", response_model=BlockParticipation)
@cache(expire=300, key_builder=MINER_CACHE)
async def get_block_participation(
    block_height: str,
    days: int = Query(default=7, ge=1, le=30),
    conn: asyncpg.Connection = Depends(get_connection)
):
    """
    Get miner participation percentages for a specific block based on their share contributions.
    Uses actual share counts from block rewards to calculate percentages.
    """
    try:
        # Handle 'latest' or 'recent' to get last week's blocks
        if block_height.lower() in ['latest', 'recent']:
            recent_blocks = await conn.fetch(GET_RECENT_BLOCKS)
            if not recent_blocks:
                raise HTTPException(
                    status_code=404,
                    detail=f"No blocks found in the last {days} days"
                )
            # Use the most recent block
            block_height = recent_blocks[0]['block_height']
            logger.info(f"Using most recent block: {block_height}")
        else:
            try:
                block_height = int(block_height)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Block height must be a number or 'latest'"
                )

        # First try to fetch some debug data
        debug_rows = await conn.fetch(DEBUG_BLOCK_DATA, block_height)
        logger.info(f"Debug data for block {block_height}:")
        for row in debug_rows:
            logger.info(f"Usage: {row['usage']}, Amount: {row['amount']}, Address: {row['address']}")

        # Now fetch the actual data
        rows = await conn.fetch(BLOCK_SHARES_QUERY, block_height)
        
        if not rows:
            logger.warning(f"No participation data found for block {block_height}")
            raise HTTPException(
                status_code=404,
                detail=f"No data found for block {block_height}"
            )

        logger.info(f"Found {len(rows)} miners for block {block_height}")
        total_shares = rows[0]['total_shares']
        logger.info(f"Total shares: {total_shares}")
        
        # Calculate participation percentages
        miners = []
        for row in rows:
            try:
                participation = (row['shares'] / total_shares) * 100
                miners.append(MinerParticipation(
                    miner_address=row['miner'],
                    shares=row['shares'],
                    participation_percentage=round(participation, 4),
                    reward=row['reward']
                ))
            except Exception as e:
                logger.error(f"Error processing miner {row['miner']}: {str(e)}")
                logger.error(f"Row data: {row}")
        
        return BlockParticipation(
            block_height=block_height,
            total_shares=total_shares,
            timestamp=rows[0]['timestamp'].isoformat(),
            miners=miners
        )
        
    except Exception as e:
        error_msg = str(e) if str(e) else "Unknown database error occurred"
        logger.error(f"Error calculating block participation: {error_msg}")
        logger.exception("Full exception details:")
        raise HTTPException(
            status_code=500,
            detail=f"Error calculating participation: {error_msg}"
        )

@router.get("/miners/bonus", response_model=List[LoyalMiner])
@cache(expire=300, key_builder=POOL_CACHE)
async def get_weekly_loyal_miners(
    conn: asyncpg.Connection = Depends(get_connection),
    limit: int = Query(default=100, ge=1, le=1000)
) -> List[Dict[str, Any]]:
    """Get miners who have been active for at least 4 out of the last 7 days, with at least 8 hours of activity per active day"""
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

@router.get("/miners/{address}/bonus-eligibility")
async def check_miner_bonus_eligibility(
    address: str,
    conn: asyncpg.Connection = Depends(get_connection)
) -> Dict[str, Any]:
    """Check why a miner might or might not be eligible for the bonus"""
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=7)
    
    try:
        # Get the daily breakdown for the miner
        daily_stats = await conn.fetch(
            MINER_BONUS_DIAGNOSTIC_QUERY,
            start_time,
            end_time,
            address
        )
        
        if not daily_stats:
            return {
                "eligible": False,
                "reason": "No mining activity found in the last 7 days",
                "daily_breakdown": []
            }
            
        # Process the results
        daily_breakdown = [
            {
                "date": row['day'].isoformat(),
                "active_hours": row['active_hours'],
                "avg_hashrate": float(row['daily_avg_hashrate']),
                "meets_hours_requirement": row['active_hours'] >= 8
            }
            for row in daily_stats
        ]
        
        # Calculate eligibility
        total_days = len(daily_breakdown)
        qualifying_days = sum(1 for day in daily_breakdown if day['meets_hours_requirement'])
        
        result = {
            "address": address,
            "eligible": qualifying_days >= 4,
            "total_days_active": total_days,
            "qualifying_days": qualifying_days,
            "needs_days": qualifying_days >= 4,
            "daily_breakdown": daily_breakdown,
            "analysis": f"Miner was active for {total_days} days, with {qualifying_days} days meeting the 8-hour minimum requirement."
        }
        
        if not result["eligible"]:
            if qualifying_days < 4:
                result["reason"] = f"Only {qualifying_days} days met the minimum 8-hour requirement (needs 4)"
            else:
                result["reason"] = "Unknown reason - please check daily breakdown"
                
        return result
        
    except Exception as e:
        logger.error(f"Error checking bonus eligibility for miner {address}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/miners/activity", response_model=List[MinerActivity])
@cache(expire=300, key_builder=POOL_CACHE)
async def get_weekly_miner_activity(
    conn: asyncpg.Connection = Depends(get_connection),
    limit: int = Query(default=100, ge=1, le=1000)
) -> List[Dict[str, Any]]:
    """Get activity statistics for all miners over the last 7 days"""
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=7)
    
    try:
        rows = await conn.fetch(MINER_ACTIVITY_QUERY, start_time, end_time, limit)
        
        if not rows:
            logger.info("No miner activity found for the given time period")
            return []
        
        return [
            MinerActivity(
                address=row['miner'],
                days_active=row['days_active'],
                weekly_avg_hashrate=float(row['weekly_avg_hashrate']),
                current_balance=float(row['current_balance']),
                last_payment=format_timestamp(row['last_payment_date']),
                active_hours=row['total_active_hours']
            )
            for row in rows
        ]
    except Exception as e:
        logger.error(f"Error retrieving miner activity: {str(e)}")
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