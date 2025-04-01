# routes/miningcore.py
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi_cache.decorator import cache
from database import create_db_pool
from utils.logging import logger
from typing import List, Dict, Any
from datetime import datetime, timedelta
from utils.calculate import (
    calculate_mining_effort,
    calculate_time_to_find_block,
    calculate_pplns_participation
)

router = APIRouter(prefix="/miningcore")

class MiningCoreException(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=500, detail=detail)
        logger.error(f"MiningCore Error: {detail}")
        
@router.get("/poolstats")
@cache(expire=60)
async def get_pool_stats(db=Depends(create_db_pool)):
    try:
        async with db.acquire() as conn:
            query = """
                WITH latest_stats AS (
                    SELECT *
                    FROM poolstats
                    ORDER BY created DESC
                    LIMIT 1
                ),
                pool_blocks AS (
                    SELECT COUNT(*) as block_count
                    FROM blocks
                    WHERE created >= NOW() - INTERVAL '24 hours'
                )
                SELECT 
                    ls.*,
                    pb.block_count as blocks_24h
                FROM latest_stats ls
                CROSS JOIN pool_blocks pb
            """
            result = await conn.fetch(query)
            if not result:
                return {"error": "No pool stats available"}
            
            return dict(result[0])
            
    except Exception as e:
        logger.error(f"Error retrieving pool stats: {str(e)}")
        return {"error": str(e)}

@router.get("/blocks/{address}")
@cache(expire=30)
async def get_miner_blocks(
    address: str,
    db=Depends(create_db_pool),
    limit: int = Query(100, ge=1, le=1000)
):
    try:
        async with db.acquire() as conn:
            query = """
                WITH pool_stats AS (
                    SELECT networkdifficulty, networkhashrate
                    FROM poolstats
                    ORDER BY created DESC
                    LIMIT 1
                ),
                miner_stats AS (
                    SELECT hashrate
                    FROM minerstats
                    WHERE miner = $1
                    ORDER BY created DESC
                    LIMIT 1
                )
                SELECT 
                    b.created,
                    b.blockheight,
                    b.effort as stored_effort,
                    b.reward,
                    b.confirmationprogress,
                    p.networkdifficulty,
                    p.networkhashrate,
                    ms.hashrate as current_hashrate
                FROM blocks b
                CROSS JOIN pool_stats p
                LEFT JOIN miner_stats ms ON true
                WHERE b.miner = $1
                ORDER BY b.created DESC
                LIMIT $2
            """
            rows = await conn.fetch(query, address, limit)
            
            blocks = []
            for row in rows:
                # If block has stored effort, use it, otherwise calculate
                if row['stored_effort'] is not None:
                    effort = float(row['stored_effort'])
                else:
                    effort = calculate_mining_effort(
                        row['networkdifficulty'],
                        row['networkhashrate'],
                        row['current_hashrate'] if row['current_hashrate'] else 0,
                        row['created'].isoformat()
                    )

                blocks.append({
                    "created": row['created'].isoformat(),
                    "blockheight": row['blockheight'],
                    "effort": effort,
                    "reward": float(row['reward']) if row['reward'] else 0,
                    "confirmationprogress": float(row['confirmationprogress']) if row['confirmationprogress'] else 0
                })
            
            return blocks
            
    except Exception as e:
        logger.error(f"Error retrieving blocks for miner {address}: {str(e)}")
        raise MiningCoreException(f"Error retrieving blocks for miner {address}: {str(e)}")

@router.get("/payments/{address}")
@cache(expire=60)
async def get_miner_payments(
    address: str,
    db=Depends(create_db_pool),
    limit: int = Query(100, ge=1, le=1000)
):
    try:
        async with db.acquire() as conn:
            query = """
                SELECT 
                    created,
                    amount,
                    transactionconfirmationdata
                FROM payments
                WHERE address = $1
                ORDER BY created DESC
                LIMIT $2
            """
            rows = await conn.fetch(query, address, limit)
            
            payments = [{
                "created": row['created'].isoformat(),
                "amount": float(row['amount']),
                "tx_id": row['transactionconfirmationdata']
            } for row in rows]
            
            return payments
            
    except Exception as e:
        logger.error(f"Error retrieving payments for miner {address}: {str(e)}")
        raise MiningCoreException(f"Error retrieving payments for miner {address}: {str(e)}")
        
@router.get("/shares")
@cache(expire=30)
async def get_current_shares(db=Depends(create_db_pool)):
    try:
        async with db.acquire() as conn:
            query = """
                WITH current_round AS (
                    SELECT MAX(created) as last_block
                    FROM blocks
                    WHERE confirmationprogress >= 1
                )
                SELECT 
                    m.miner,
                    COALESCE(SUM(m.sharespersecond), 0) as shares,
                    MAX(m.created) as last_share
                FROM minerstats m
                CROSS JOIN current_round cr
                WHERE m.created > cr.last_block
                GROUP BY m.miner
            """
            rows = await conn.fetch(query)
            
            return [{
                "miner": row['miner'],
                "shares": float(row['shares']),
                "last_share": row['last_share'].isoformat() if row['last_share'] else None
            } for row in rows]
            
    except Exception as e:
        logger.error(f"Error retrieving current shares: {str(e)}")
        return []


@router.get("/{table_name}")
@cache(expire=60)
async def get_table_data(table_name: str, db=Depends(create_db_pool)):
    try:
        async with db.acquire() as conn:
            result = await conn.fetch(f"SELECT * FROM {table_name}")
        return [dict(row) for row in result]
    except Exception as e:
        logger.error(f"Error retrieving data from {table_name}: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error")

@router.get("/{table_name}/{address}")
async def get_filtered_table_data(
    table_name: str, 
    address: str, 
    db=Depends(create_db_pool),
    limit: int = Query(100, ge=1, le=1000)
) -> List[Dict[str, Any]]:
    address_column = get_address_column(table_name)
    
    try:
        async with db.acquire() as conn:
            # Check if table exists
            table_exists = await conn.fetchval(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = $1)",
                table_name
            )
            if not table_exists:
                raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
            
            query = f"SELECT * FROM {table_name} WHERE {address_column} = $1 LIMIT $2"
            rows = await conn.fetch(query, address, limit)
        
        result = [dict(row) for row in rows]
        logger.info(f"Retrieved {len(result)} rows from table {table_name} for address {address}")
        return result
    except Exception as e:
        logger.error(f"Error retrieving filtered data from {table_name}: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error")

def get_address_column(table_name: str) -> str:
    address_columns = {
        "shares": "miner",
        "balances": "address",
        "balance_changes": "address",
        "payments": "address",
        "minerstats": "miner",
        "blocks": "miner",
    }
    return address_columns.get(table_name, "address")