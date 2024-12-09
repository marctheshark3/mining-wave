# routes/sigscore.py
from fastapi import APIRouter, Depends, Query, HTTPException
from database import create_db_pool
from utils.logging import logger
from datetime import datetime, timedelta
from fastapi_cache.decorator import cache
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import json
from utils.calculate import calculate_mining_effort, calculate_time_to_find_block, calculate_pplns_participation

router = APIRouter(prefix="/sigscore")

class SigScoreException(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=500, detail=detail)
        logger.error(f"SigScore Error: {detail}")
        

class LoyalMiner(BaseModel):
    address: str
    days_active: int
    weekly_avg_hashrate: float
    current_balance: float
    last_payment: Optional[str]

@router.get("/miners/bonus", response_model=List[LoyalMiner])
async def get_weekly_loyal_miners(
    db=Depends(create_db_pool),
    limit: int = Query(default=100, ge=1, le=1000)
) -> List[Dict[str, Any]]:
    """
    Get miners who have been active for at least 4 out of the last 7 days,
    with at least 12 hours of activity per active day.
    """
    
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=7)
    
    query = """
    WITH hourly_activity AS (
        -- Get hourly averages for each miner
        SELECT 
            miner,
            date_trunc('hour', created) AS hour,
            DATE(created) AS day,
            AVG(hashrate) AS avg_hashrate
        FROM minerstats
        WHERE created >= $1 AND created <= $2
        GROUP BY miner, date_trunc('hour', created), DATE(created)
        HAVING AVG(hashrate) > 0
    ),
    daily_activity AS (
        -- Count active hours per day for each miner
        SELECT 
            miner,
            day,
            COUNT(DISTINCT hour) AS active_hours,
            AVG(avg_hashrate) AS daily_avg_hashrate
        FROM hourly_activity
        GROUP BY miner, day
    ),
    qualified_miners AS (
        -- Find miners active for 12+ hours on at least 4 days
        SELECT 
            miner,
            COUNT(DISTINCT day) AS days_active,
            AVG(daily_avg_hashrate) AS weekly_avg_hashrate
        FROM daily_activity
        WHERE active_hours >= 12
        GROUP BY miner
        HAVING COUNT(DISTINCT day) >= 4
    )
    SELECT 
        qm.miner,
        qm.days_active,
        qm.weekly_avg_hashrate,
        COALESCE(b.amount, 0) as current_balance,
        MAX(p.created) as last_payment_date
    FROM qualified_miners qm
    LEFT JOIN balances b ON qm.miner = b.address
    LEFT JOIN payments p ON qm.miner = p.address
    GROUP BY qm.miner, qm.days_active, qm.weekly_avg_hashrate, b.amount
    ORDER BY qm.weekly_avg_hashrate DESC
    LIMIT $3
    """
    
    try:
        async with db.acquire() as conn:
            rows = await conn.fetch(query, start_time, end_time, limit)
            
            if not rows:
                # Return empty list instead of raising 404
                logger.info("No loyal miners found for the given criteria")
                return []
        
        loyal_miners = [
            LoyalMiner(
                address=row['miner'],
                days_active=row['days_active'],
                weekly_avg_hashrate=float(row['weekly_avg_hashrate']),
                current_balance=float(row['current_balance']),
                last_payment=row['last_payment_date'].isoformat() if row['last_payment_date'] else None
            )
            for row in rows
        ]
        
        logger.info(f"Retrieved {len(loyal_miners)} miners active for 4+ days in the past week")
        return loyal_miners
        
    except Exception as e:
        logger.error(f"Error retrieving weekly loyal miners: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/history")
@cache(expire=300)  # Cache for 5 minutes
async def get_pool_history(db=Depends(create_db_pool)):
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
    
    async with db.acquire() as conn:
        rows = await conn.fetch(query, start_time, end_time)

    pool_history = [
        {
            "timestamp": row['hour'].isoformat(),
            "total_hashrate": float(row['total_hashrate'])
        } for row in rows
    ]

    logger.info(f"Retrieved pool history data for the last 5 days")
    return pool_history

@router.get("/miners")
async def get_all_miners(
    db=Depends(create_db_pool),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    query = """
        WITH latest_timestamp AS (
            SELECT MAX(created) as max_created
            FROM minerstats
        ),
        latest_stats AS (
            SELECT 
                miner,
                SUM(hashrate) as total_hashrate,
                SUM(sharespersecond) as total_sharespersecond
            FROM minerstats
            WHERE created = (SELECT max_created FROM latest_timestamp)
            GROUP BY miner
            HAVING SUM(hashrate) > 0
        ),
        latest_blocks AS (
            SELECT DISTINCT ON (miner) miner, created as last_block_found
            FROM blocks
            ORDER BY miner, created DESC
        )
        SELECT 
            ls.miner, 
            ls.total_hashrate, 
            ls.total_sharespersecond,
            (SELECT max_created FROM latest_timestamp) as last_stat_time,
            lb.last_block_found
        FROM latest_stats ls
        LEFT JOIN latest_blocks lb ON ls.miner = lb.miner
        ORDER BY ls.total_hashrate DESC NULLS LAST
        LIMIT $1 OFFSET $2
    """
    
    async with db.acquire() as conn:
        rows = await conn.fetch(query, limit, offset)
    
    miners = [{
        "address": row['miner'],
        "hashrate": float(row['total_hashrate']),
        "sharesPerSecond": float(row['total_sharespersecond']),
        "lastStatTime": row['last_stat_time'].isoformat(),
        "last_block_found": row['last_block_found'].isoformat() if row['last_block_found'] else None
    } for row in rows]
    
    logger.info(f"Retrieved {len(miners)} active miners for the latest timestamp")
    return miners

@router.get("/miners/top")
@cache(expire=60)  # Cache for 1 minute
async def get_top_miners(db=Depends(create_db_pool)):
    query = """
        SELECT miner, hashrate
        FROM (
            SELECT DISTINCT ON (miner) miner, hashrate
            FROM minerstats
            ORDER BY miner, created DESC
        ) as latest_stats
        ORDER BY hashrate DESC
        LIMIT 20
    """
    
    async with db.acquire() as conn:
        rows = await conn.fetch(query)
    
    top_miners = [{"address": row['miner'], "hashrate": float(row['hashrate'])} for row in rows]
    
    logger.info(f"Retrieved top 20 miners")
    return top_miners

@router.get("/miners/{address}")
@cache(expire=30)
async def get_miner_details(address: str, db=Depends(create_db_pool)):
    try:
        queries = {
            "pool_stats": """
                SELECT networkdifficulty, networkhashrate 
                FROM poolstats 
                ORDER BY created DESC 
                LIMIT 1
            """,
            "last_block": """
                SELECT created, blockheight 
                FROM blocks 
                WHERE miner = $1 
                ORDER BY created DESC 
                LIMIT 1
            """,
            "payment": """
                SELECT amount, created as last_payment_date, transactionconfirmationdata 
                FROM payments 
                WHERE address = $1 
                ORDER BY created DESC 
                LIMIT 1
            """,
            "total_paid": """
                SELECT COALESCE(SUM(amount), 0) as total_paid 
                FROM payments 
                WHERE address = $1
            """,
            "paid_today": """
                SELECT COALESCE(SUM(amount), 0) as paid_today 
                FROM payments 
                WHERE address = $1 
                AND DATE(created) = $2
            """,
            "workers": """
                WITH latest_worker_stats AS (
                    SELECT 
                        worker,
                        hashrate,
                        sharespersecond,
                        ROW_NUMBER() OVER (PARTITION BY worker ORDER BY created DESC) as rn
                    FROM minerstats
                    WHERE miner = $1
                )
                SELECT 
                    worker, 
                    hashrate, 
                    sharespersecond,
                    SUM(hashrate) OVER () as total_hashrate,
                    SUM(sharespersecond) OVER () as total_sharespersecond
                FROM latest_worker_stats
                WHERE rn = 1
                ORDER BY hashrate DESC
            """
        }

        results = {}
        async with db.acquire() as conn:
            # Get pool stats first
            pool_stats = await conn.fetchrow(queries["pool_stats"])
            
            # Get other data
            for key, query in queries.items():
                if key == "pool_stats":
                    continue
                if key == "paid_today":
                    results[key] = await conn.fetch(query, address, datetime.utcnow().date())
                else:
                    results[key] = await conn.fetch(query, address)

        if not results["workers"]:
            raise HTTPException(status_code=404, detail=f"Miner with address {address} not found")

        # Calculate effort and time to find block
        current_effort = calculate_mining_effort(
            pool_stats['networkdifficulty'],
            pool_stats['networkhashrate'],
            results["workers"][0]['total_hashrate'],
            results["last_block"][0]['created'].isoformat() if results["last_block"] else None
        )

        time_to_find = calculate_time_to_find_block(
            pool_stats['networkdifficulty'],
            pool_stats['networkhashrate'],
            results["workers"][0]['total_hashrate']
        )

        # Format workers as direct objects instead of JSON strings
        workers = [{
            "worker": row['worker'],
            "hashrate": float(row['hashrate']),
            "shares": float(row['sharespersecond'])
        } for row in results["workers"]]

        return {
            "address": address,
            "current_hashrate": float(results["workers"][0]['total_hashrate']),
            "shares_per_second": float(results["workers"][0]['total_sharespersecond']),
            "effort": current_effort,
            "time_to_find": time_to_find,
            "last_block_found": {
                "timestamp": results["last_block"][0]['created'].isoformat() if results["last_block"] else None,
                "block_height": results["last_block"][0]['blockheight'] if results["last_block"] else None
            },
            "payments": {
                "paid_today": float(results["paid_today"][0]['paid_today']),
                "total_paid": float(results["total_paid"][0]['total_paid']),
                "last_payment": {
                    "amount": float(results["payment"][0]['amount']) if results["payment"] else 0,
                    "date": results["payment"][0]['last_payment_date'].isoformat() if results["payment"] else None,
                    "tx_id": results["payment"][0]['transactionconfirmationdata'] if results["payment"] else None
                }
            },
            "workers": workers
        }

    except Exception as e:
        logger.error(f"Error retrieving miner details: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/miners/{address}/workers")
@cache(expire=60)
async def get_miner_worker_history(
    address: str,
    db=Depends(create_db_pool),
    days: int = Query(5, ge=1, le=30)
):
    try:
        query = """
            WITH worker_stats AS (
                SELECT 
                    worker,
                    date_trunc('hour', created) as hour,
                    AVG(hashrate) as hashrate,
                    AVG(sharespersecond) as shares
                FROM minerstats
                WHERE miner = $1
                AND created >= NOW() - make_interval(days => $2)
                GROUP BY worker, date_trunc('hour', created)
            )
            SELECT
                worker,
                hour as timestamp,
                hashrate,
                shares,
                LAG(hashrate) OVER (PARTITION BY worker ORDER BY hour) as prev_hashrate
            FROM worker_stats
            ORDER BY hour, worker
        """
        
        async with db.acquire() as conn:
            rows = await conn.fetch(query, address, days)
        
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

class MinerSettings(BaseModel):
    miner_address: str
    minimum_payout_threshold: float
    swapping: bool
    created_at: str

@router.get("/miner_setting", response_model=List[MinerSettings])
async def get_all_miner_settings(
    db=Depends(create_db_pool),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    query = """
        SELECT miner_address, minimum_payout_threshold, swapping, created_at
        FROM miner_payouts
        ORDER BY created_at DESC
        LIMIT $1 OFFSET $2
    """
    
    async with db.acquire() as conn:
        rows = await conn.fetch(query, limit, offset)
    
    settings = [
        MinerSettings(
            miner_address=row['miner_address'],
            minimum_payout_threshold=float(row['minimum_payout_threshold']),
            swapping=row['swapping'],
            created_at=row['created_at'].isoformat()
        )
        for row in rows
    ]
    
    return settings

@router.get("/miner_setting/{miner_address}", response_model=MinerSettings)
async def get_miner_setting(miner_address: str, db=Depends(create_db_pool)):
    query = "SELECT * FROM miner_payouts WHERE miner_address = $1"
    
    async with db.acquire() as conn:
        row = await conn.fetchrow(query, miner_address)
    
    if row is None:
        raise HTTPException(status_code=404, detail="Miner settings not found")
    
    return MinerSettings(
        miner_address=row['miner_address'],
        minimum_payout_threshold=float(row['minimum_payout_threshold']),
        swapping=row['swapping'],
        created_at=row['created_at'].isoformat()
    )