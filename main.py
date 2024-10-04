from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy import create_engine, MetaData, Table, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os
from dotenv import load_dotenv
from sqlalchemy.sql import text
import logging
from datetime import datetime, timedelta

from pydantic import BaseModel
from typing import List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

DB_HOST = os.getenv('DB_HOST', 'postgres_secondary')
DB_PORT = os.getenv('DB_PORT', '5432')
DATABASE_URL = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{DB_HOST}:{DB_PORT}/{os.getenv('POSTGRES_DB')}"

logger.info(f"Connecting to database: {DATABASE_URL}")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def execute_query(db, query, params=None):
    try:
        result = db.execute(query, params or {})
        return result
    except Exception as e:
        logger.error(f"Database query error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/")
async def root():
    return {"message": "Welcome to the Mining Core API"}

@app.get("/tables")
async def list_tables(db: SessionLocal = Depends(get_db)):
    try:
        metadata = MetaData()
        metadata.reflect(bind=engine)
        tables = list(metadata.tables.keys())
        logger.info(f"Retrieved tables: {tables}")
        return {"tables": tables}
    except Exception as e:
        logger.error(f"Error retrieving tables: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/test_db_connection")
async def test_db_connection(db: SessionLocal = Depends(get_db)):
    result = execute_query(db, text("SELECT 1"))
    return {"status": "Database connection successful", "result": result.fetchone()[0]}

@app.get("/miningcore/{table_name}")
async def get_table_data(table_name: str, db: SessionLocal = Depends(get_db)):
    metadata = MetaData()
    metadata.reflect(bind=engine)
    if table_name not in metadata.tables:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    
    query = text(f"SELECT * FROM {table_name}")
    result = execute_query(db, query)
    
    columns = result.keys()
    rows = [dict(zip(columns, row)) for row in result.fetchall()]
    
    logger.info(f"Retrieved {len(rows)} rows from table {table_name}")
    return rows

@app.get("/miningcore/{table_name}/{address}")
async def get_filtered_table_data(
    table_name: str, 
    address: str, 
    db: SessionLocal = Depends(get_db),
    limit: int = Query(100, ge=1, le=1000)
):
    metadata = MetaData()
    metadata.reflect(bind=engine)
    if table_name not in metadata.tables:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")

    address_column = get_address_column(table_name)
    
    query = text(f"SELECT * FROM {table_name} WHERE {address_column} = :address LIMIT :limit")
    result = execute_query(db, query, {"address": address, "limit": limit})
    
    columns = result.keys()
    rows = [dict(zip(columns, row)) for row in result.fetchall()]
    
    logger.info(f"Retrieved {len(rows)} rows from table {table_name} for address {address}")
    return rows

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

@app.get("/sigscore/history")
async def get_pool_history(db: SessionLocal = Depends(get_db)):
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=5)
    
    query = text("""
        WITH hourly_data AS (
            SELECT 
                date_trunc('hour', created) AS hour,
                worker,
                AVG(hashrate) AS avg_hashrate
            FROM minerstats
            WHERE created >= :start_time AND created < :end_time
            GROUP BY date_trunc('hour', created), worker
        )
        SELECT 
            hour,
            SUM(avg_hashrate) AS total_hashrate
        FROM hourly_data
        GROUP BY hour
        ORDER BY hour
    """)
    
    result = execute_query(db, query, {"start_time": start_time, "end_time": end_time})

    pool_history = [
        {
            "timestamp": row.hour.isoformat(),
            "total_hashrate": float(row.total_hashrate)
        } for row in result
    ]

    logger.info(f"Retrieved pool history data for the last 5 days")
    return pool_history

@app.get("/sigscore/miners")
async def get_all_miners(
    db: SessionLocal = Depends(get_db),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    query = text("""
        WITH latest_stats AS (
            SELECT 
                miner,
                SUM(hashrate) as total_hashrate,
                SUM(sharespersecond) as total_sharespersecond,
                MAX(created) as last_stat_time
            FROM (
                SELECT DISTINCT ON (miner, worker) miner, worker, hashrate, sharespersecond, created
                FROM minerstats
                ORDER BY miner, worker, created DESC
            ) as latest_worker_stats
            GROUP BY miner
            HAVING SUM(hashrate) > 0  -- Filter out miners with 0 hashrate
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
            ls.last_stat_time,
            lb.last_block_found
        FROM latest_stats ls
        LEFT JOIN latest_blocks lb ON ls.miner = lb.miner
        ORDER BY ls.total_hashrate DESC NULLS LAST
        LIMIT :limit OFFSET :offset
    """)
    result = execute_query(db, query, {"limit": limit, "offset": offset})
    
    miners = [{
        "address": row.miner,
        "hashrate": float(row.total_hashrate),
        "sharesPerSecond": float(row.total_sharespersecond),
        "lastStatTime": row.last_stat_time.isoformat(),
        "last_block_found": row.last_block_found.isoformat() if row.last_block_found else None
    } for row in result]
    
    logger.info(f"Retrieved {len(miners)} active miners with total hashrate, shares per second, and last block found timestamp")
    return miners

@app.get("/sigscore/miners/top")
async def get_top_miners(db: SessionLocal = Depends(get_db)):
    query = text("""
        SELECT miner, hashrate
        FROM (
            SELECT DISTINCT ON (miner) miner, hashrate
            FROM minerstats
            ORDER BY miner, created DESC
        ) as latest_stats
        ORDER BY hashrate DESC
        LIMIT 20
    """)
    result = execute_query(db, query)
    
    top_miners = [{"address": row.miner, "hashrate": row.hashrate} for row in result]
    
    logger.info(f"Retrieved top 20 miners")
    return top_miners

@app.get("/sigscore/miners/{address}")
async def get_miner_details(address: str, db: SessionLocal = Depends(get_db)):
    queries = {
        "last_block": text("""
            SELECT created, blockheight
            FROM blocks
            WHERE miner = :address
            ORDER BY created DESC
            LIMIT 1
        """),
        "balance": text("""
            SELECT amount
            FROM balances
            WHERE address = :address
            ORDER BY updated DESC
            LIMIT 1
        """),
        "payment": text("""
            SELECT amount, created as last_payment_date, transactionconfirmationdata
            FROM payments
            WHERE address = :address
            ORDER BY created DESC
            LIMIT 1
        """),
        "total_paid": text("""
            SELECT COALESCE(SUM(amount), 0) as total_paid
            FROM payments
            WHERE address = :address
        """),
        "paid_today": text("""
            SELECT COALESCE(SUM(amount), 0) as paid_today
            FROM payments
            WHERE address = :address
            AND DATE(created) = :today
        """),
        "workers": text("""
            WITH latest_worker_stats AS (
                SELECT 
                    worker,
                    hashrate,
                    sharespersecond,
                    ROW_NUMBER() OVER (PARTITION BY worker ORDER BY created DESC) as rn
                FROM minerstats
                WHERE miner = :address
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
        """)
    }

    results = {}
    for key, query in queries.items():
        params = {"address": address}
        if key == "paid_today":
            params["today"] = datetime.utcnow().date()
        results[key] = execute_query(db, query, params).fetchall()

    if not results["workers"]:
        raise HTTPException(status_code=404, detail=f"Miner with address {address} not found")

    tx_link = None
    if results["payment"] and results["payment"][0].transactionconfirmationdata:
        tx_link = f"https://ergexplorer.com/transactions#{results['payment'][0].transactionconfirmationdata}"

    miner_stats = {
        "address": address,
        "current_hashrate": float(results["workers"][0].total_hashrate),
        "shares_per_second": float(results["workers"][0].total_sharespersecond),
        "last_block_found": {
            "timestamp": results["last_block"][0].created.isoformat() if results["last_block"] else None,
            "block_height": results["last_block"][0].blockheight if results["last_block"] else None
        },
        "balance": results["balance"][0].amount if results["balance"] else 0,
        "last_payment": {
            "amount": results["payment"][0].amount if results["payment"] else 0,
            "date": results["payment"][0].last_payment_date.isoformat() if results["payment"] else None,
            "tx_link": tx_link
        },
        "total_paid": float(results["total_paid"][0].total_paid),
        "paid_today": float(results["paid_today"][0].paid_today),
        "workers": [{"worker": row.worker, "hashrate": float(row.hashrate)} for row in results["workers"]]
    }
    
    logger.info(f"Retrieved detailed miner information for address: {address}")
    return miner_stats

@app.get("/sigscore/miners/{address}/workers")
async def get_miner_workers(address: str, db: SessionLocal = Depends(get_db)):
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=24)
    
    query = text("""
        WITH hourly_data AS (
            SELECT 
                worker,
                date_trunc('hour', created) AS hour,
                AVG(hashrate) AS avg_hashrate,
                AVG(sharespersecond) AS avg_sharespersecond
            FROM minerstats
            WHERE miner = :address
                AND created >= :start_time
                AND created < :end_time
            GROUP BY worker, date_trunc('hour', created)
        )
        SELECT 
            worker,
            hour,
            avg_hashrate,
            avg_sharespersecond
        FROM hourly_data
        ORDER BY worker, hour
    """)
    
    result = execute_query(db, query, {
        "address": address,
        "start_time": start_time,
        "end_time": end_time
    })

    workers_data = {}
    for row in result:
        worker = row.worker
        hour = row.hour.isoformat()
        if worker not in workers_data:
            workers_data[worker] = []
        workers_data[worker].append({
            "created": hour,
            "hashrate": float(row.avg_hashrate),
            "sharesPerSecond": float(row.avg_sharespersecond)
        })

    logger.info(f"Retrieved 24-hour hourly data for workers of miner address: {address}")
    return workers_data


class MinerSettings(BaseModel):
    miner_address: str
    minimum_payout_threshold: float
    swapping: bool
    created_at: str

@app.get("/sigscore/miner_setting", response_model=List[MinerSettings])
async def get_all_miner_settings(
    db: SessionLocal = Depends(get_db),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    query = text("""
        SELECT miner_address, minimum_payout_threshold, swapping, created_at
        FROM miner_payouts
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
    """)
    result = execute_query(db, query, {"limit": limit, "offset": offset})
    
    settings = [
        {
            "miner_address": row.miner_address,
            "minimum_payout_threshold": float(row.minimum_payout_threshold),
            "swapping": row.swapping,
            "created_at": row.created_at.isoformat()
        }
        for row in result
    ]
    
    return settings
    
@app.get("/sigscore/miner_setting/{miner_address}", response_model=MinerSettings)
async def get_miner_setting(miner_address: str, db: SessionLocal = Depends(get_db)):
    query = text("SELECT * FROM miner_payouts WHERE miner_address = :miner_address")
    result = execute_query(db, query, {"miner_address": miner_address})
    settings = result.fetchone()
    if settings is None:
        raise HTTPException(status_code=404, detail="Miner settings not found")
    return {
        "miner_address": settings.miner_address,
        "minimum_payout_threshold": float(settings.minimum_payout_threshold),
        "swapping": settings.swapping,
        "created_at": settings.created_at.isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
