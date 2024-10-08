# routes/sigscore.py
from fastapi import APIRouter, Depends, Query, HTTPException
from database import create_db_pool
from utils.logging import logger
from datetime import datetime, timedelta
from fastapi_cache.decorator import cache
from typing import List, Dict, Any

router = APIRouter(prefix="/sigscore")

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
async def get_miner_details(address: str, db=Depends(create_db_pool)):
    queries = {
        "last_block": "SELECT created, blockheight FROM blocks WHERE miner = $1 ORDER BY created DESC LIMIT 1",
        "balance": "SELECT amount FROM balances WHERE address = $1 ORDER BY updated DESC LIMIT 1",
        "payment": "SELECT amount, created as last_payment_date, transactionconfirmationdata FROM payments WHERE address = $1 ORDER BY created DESC LIMIT 1",
        "total_paid": "SELECT COALESCE(SUM(amount), 0) as total_paid FROM payments WHERE address = $1",
        "paid_today": "SELECT COALESCE(SUM(amount), 0) as paid_today FROM payments WHERE address = $1 AND DATE(created) = $2",
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
        for key, query in queries.items():
            if key == "paid_today":
                rows = await conn.fetch(query, address, datetime.utcnow().date())
            else:
                rows = await conn.fetch(query, address)
            results[key] = rows

    if not results["workers"]:
        raise HTTPException(status_code=404, detail=f"Miner with address {address} not found")

    tx_link = None
    if results["payment"] and results["payment"][0]['transactionconfirmationdata']:
        tx_link = f"https://ergexplorer.com/transactions#{results['payment'][0]['transactionconfirmationdata']}"

    miner_stats = {
        "address": address,
        "current_hashrate": float(results["workers"][0]['total_hashrate']),
        "shares_per_second": float(results["workers"][0]['total_sharespersecond']),
        "last_block_found": {
            "timestamp": results["last_block"][0]['created'].isoformat() if results["last_block"] else None,
            "block_height": results["last_block"][0]['blockheight'] if results["last_block"] else None
        },
        "balance": results["balance"][0]['amount'] if results["balance"] else 0,
        "last_payment": {
            "amount": results["payment"][0]['amount'] if results["payment"] else 0,
            "date": results["payment"][0]['last_payment_date'].isoformat() if results["payment"] else None,
            "tx_link": tx_link
        },
        "total_paid": float(results["total_paid"][0]['total_paid']),
        "paid_today": float(results["paid_today"][0]['paid_today']),
        "workers": [{"worker": row['worker'], "hashrate": float(row['hashrate'])} for row in results["workers"]]
    }
    
    logger.info(f"Retrieved detailed miner information for address: {address}")
    return miner_stats