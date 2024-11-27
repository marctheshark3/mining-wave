# routes/miningcore.py
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi_cache.decorator import cache
from database import create_db_pool
from utils.logging import logger
from typing import List, Dict, Any

router = APIRouter(prefix="/miningcore")

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