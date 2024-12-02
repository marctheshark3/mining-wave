# routes/sigscore.py
from fastapi import APIRouter, Depends, Query, HTTPException
from database import create_db_pool
from utils.logging import logger
from datetime import datetime, timedelta
from fastapi_cache.decorator import cache
from typing import List, Dict, Any

router = APIRouter(prefix="/sigscore")

class SigScoreException(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=500, detail=detail)
        logger.error(f"SigScore Error: {detail}")
        

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
            "current_stats": """
                WITH latest_stats AS (
                    SELECT 
                        miner,
                        SUM(hashrate) as total_hashrate,
                        SUM(sharespersecond) as total_shares,
                        json_agg(
                            json_build_object(
                                'worker', worker,
                                'hashrate', hashrate,
                                'shares', sharespersecond
                            )
                        ) as workers,
                        MAX(created) as last_stat
                    FROM minerstats
                    WHERE miner = $1
                    AND created >= NOW() - INTERVAL '1 hour'
                    GROUP BY miner
                )
                SELECT 
                    ls.*,
                    p.networkdifficulty,
                    p.networkhashrate
                FROM latest_stats ls
                CROSS JOIN LATERAL (
                    SELECT networkdifficulty, networkhashrate
                    FROM poolstats
                    ORDER BY created DESC
                    LIMIT 1
                ) p
            """,
            "blocks": """
                SELECT created, blockheight
                FROM blocks
                WHERE miner = $1
                ORDER BY created DESC
                LIMIT 1
            """,
            "payments": """
                SELECT 
                    SUM(amount) FILTER (WHERE created >= CURRENT_DATE) as paid_today,
                    SUM(amount) as total_paid,
                    json_build_object(
                        'amount', MAX(amount),
                        'date', MAX(created),
                        'tx_id', MAX(transactionconfirmationdata)
                    ) as last_payment
                FROM payments
                WHERE address = $1
            """
        }

        results = {}
        async with db.acquire() as conn:
            for key, query in queries.items():
                rows = await conn.fetch(query, address)
                results[key] = rows[0] if rows else None

        if not results["current_stats"]:
            raise SigScoreException(f"No data found for miner {address}")

        # Calculate effort and time to find block
        stats = results["current_stats"]
        effort = calculate_mining_effort(
            stats['networkdifficulty'],
            stats['networkhashrate'],
            stats['total_hashrate'],
            results["blocks"]["created"] if results["blocks"] else datetime.min
        )
        
        ttf = calculate_time_to_find_block(
            stats['networkdifficulty'],
            stats['networkhashrate'],
            stats['total_hashrate']
        )

        payments = results["payments"]
        
        return {
            "address": address,
            "current_hashrate": float(stats['total_hashrate']),
            "shares_per_second": float(stats['total_shares']),
            "effort": effort,
            "time_to_find": ttf,
            "last_block_found": {
                "timestamp": results["blocks"]["created"].isoformat() if results["blocks"] else None,
                "block_height": results["blocks"]["blockheight"] if results["blocks"] else None
            },
            "payments": {
                "paid_today": float(payments['paid_today']) if payments['paid_today'] else 0,
                "total_paid": float(payments['total_paid']) if payments['total_paid'] else 0,
                "last_payment": {
                    "amount": float(payments['last_payment']['amount']) if payments['last_payment']['amount'] else 0,
                    "date": payments['last_payment']['date'].isoformat() if payments['last_payment']['date'] else None,
                    "tx_id": payments['last_payment']['tx_id']
                }
            },
            "workers": stats['workers']
        }
            
    except SigScoreException:
        raise
    except Exception as e:
        raise SigScoreException(f"Error retrieving miner details: {str(e)}")

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