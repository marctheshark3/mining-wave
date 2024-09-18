from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os
from dotenv import load_dotenv
from sqlalchemy.sql import text
import logging
from datetime import datetime, timedelta

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
    try:
        result = db.execute(text("SELECT 1")).fetchone()
        return {"status": "Database connection successful", "result": result[0]}
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database connection error: {str(e)}")

@app.get("/miningcore/{table_name}")
async def get_table_data(table_name: str, db: SessionLocal = Depends(get_db)):
    try:
        # Check if the table exists
        metadata = MetaData()
        metadata.reflect(bind=engine)
        if table_name not in metadata.tables:
            raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
        
        query = text(f"SELECT * FROM {table_name}")
        result = db.execute(query)
        
        columns = result.keys()
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
        
        logger.info(f"Retrieved {len(rows)} rows from table {table_name}")
        return rows
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching data from {table_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching data: {str(e)}")

@app.get("/miningcore/{table_name}/{address}")
async def get_filtered_table_data(
    table_name: str, 
    address: str, 
    db: SessionLocal = Depends(get_db),
    limit: int = Query(100, ge=1, le=1000)
):
    try:
        # Check if the table exists
        metadata = MetaData()
        metadata.reflect(bind=engine)
        if table_name not in metadata.tables:
            raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")

        # Determine the appropriate column for filtering based on the table
        address_column = get_address_column(table_name)
        
        # Use text() to create a safe SQL query with parameter binding
        query = text(f"SELECT * FROM {table_name} WHERE {address_column} = :address LIMIT :limit")
        result = db.execute(query, {"address": address, "limit": limit})
        
        columns = result.keys()
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
        
        logger.info(f"Retrieved {len(rows)} rows from table {table_name} for address {address}")
        return rows
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching data from {table_name} for address {address}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching data: {str(e)}")

def get_address_column(table_name: str) -> str:
    """
    Determine the appropriate column for address filtering based on the table name.
    """
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
    try:
        # Calculate the start time (5 days ago)
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=5)
        
        query = text("""
            WITH hourly_data AS (
                SELECT 
                    date_trunc('hour', created) AS hour,
                    miner,
                    AVG(hashrate) AS avg_hashrate
                FROM minerstats
                WHERE created >= :start_time AND created < :end_time
                GROUP BY date_trunc('hour', created), miner
            )
            SELECT 
                hour,
                SUM(avg_hashrate) AS total_hashrate
            FROM hourly_data
            GROUP BY hour
            ORDER BY hour
        """)
        
        result = db.execute(query, {
            "start_time": start_time,
            "end_time": end_time
        })

        # Process the results
        pool_history = [
            {
                "timestamp": row.hour.isoformat(),
                "total_hashrate": float(row.total_hashrate)
            } for row in result
        ]

        logger.info(f"Retrieved pool history data for the last 5 days")
        return pool_history
    except Exception as e:
        logger.error(f"Error fetching pool history data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching pool history data: {str(e)}")

@app.get("/sigscore/miners")
async def get_all_miners(
    db: SessionLocal = Depends(get_db),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    try:
        query = text("""
            WITH latest_stats AS (
                SELECT DISTINCT ON (miner) miner, hashrate, created
                FROM minerstats
                ORDER BY miner, created DESC
            ),
            latest_blocks AS (
                SELECT DISTINCT ON (miner) miner, created as last_block_found
                FROM blocks
                ORDER BY miner, created DESC
            )
            SELECT ls.miner, ls.hashrate, lb.last_block_found
            FROM latest_stats ls
            LEFT JOIN latest_blocks lb ON ls.miner = lb.miner
            ORDER BY ls.hashrate DESC NULLS LAST
            LIMIT :limit OFFSET :offset
        """)
        result = db.execute(query, {"limit": limit, "offset": offset})
        
        miners = [{
            "address": row.miner,
            "hashrate": row.hashrate,
            "last_block_found": row.last_block_found.isoformat() if row.last_block_found else None
        } for row in result]
        
        logger.info(f"Retrieved {len(miners)} miners with last block found timestamp")
        return miners
    except Exception as e:
        logger.error(f"Error fetching miners with last block found timestamp: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching miners: {str(e)}")
        
@app.get("/sigscore/miners/top")
async def get_top_miners(db: SessionLocal = Depends(get_db)):
    try:
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
        result = db.execute(query)
        
        top_miners = [{"address": row.miner, "hashrate": row.hashrate} for row in result]
        
        logger.info(f"Retrieved top 20 miners")
        return top_miners
    except Exception as e:
        logger.error(f"Error fetching top miners: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching top miners: {str(e)}")

@app.get("/sigscore/miners/{address}")
async def get_miner_details(address: str, db: SessionLocal = Depends(get_db)):
    try:
        # Get the latest stats for the miner
        latest_stats_query = text("""
            SELECT hashrate, sharespersecond
            FROM minerstats
            WHERE miner = :address
            ORDER BY created DESC
            LIMIT 1
        """)
        latest_stats_result = db.execute(latest_stats_query, {"address": address}).fetchone()
        if not latest_stats_result:
            raise HTTPException(status_code=404, detail=f"Miner with address {address} not found")
        
        # Get the last block found by this miner
        last_block_query = text("""
            SELECT created, blockheight
            FROM blocks
            WHERE miner = :address
            ORDER BY created DESC
            LIMIT 1
        """)
        last_block_result = db.execute(last_block_query, {"address": address}).fetchone()
        
        # Get balance information
        balance_query = text("""
            SELECT amount
            FROM balances
            WHERE address = :address
            ORDER BY updated DESC
            LIMIT 1
        """)
        balance_result = db.execute(balance_query, {"address": address}).fetchone()

        # Get payment information
        payment_query = text("""
            SELECT amount, created as last_payment_date, transactionconfirmationdata
            FROM payments
            WHERE address = :address
            ORDER BY created DESC
            LIMIT 1
        """)
        payment_result = db.execute(payment_query, {"address": address}).fetchone()

        # Get total paid amount
        total_paid_query = text("""
            SELECT COALESCE(SUM(amount), 0) as total_paid
            FROM payments
            WHERE address = :address
        """)
        total_paid_result = db.execute(total_paid_query, {"address": address}).fetchone()

        # Get amount paid today
        today = datetime.utcnow().date()
        paid_today_query = text("""
            SELECT COALESCE(SUM(amount), 0) as paid_today
            FROM payments
            WHERE address = :address
            AND DATE(created) = :today
        """)
        paid_today_result = db.execute(paid_today_query, {"address": address, "today": today}).fetchone()

        # Format the transaction link
        tx_link = None
        if payment_result and payment_result.transactionconfirmationdata:
            tx_link = f"https://ergexplorer.com/transactions#{payment_result.transactionconfirmationdata}"

        workers_query = text("""
            WITH latest_worker_stats AS (
                SELECT 
                    worker,
                    hashrate,
                    ROW_NUMBER() OVER (PARTITION BY worker ORDER BY created DESC) as rn
                FROM minerstats
                WHERE miner = :address
            )
            SELECT worker, hashrate
            FROM latest_worker_stats
            WHERE rn = 1
            ORDER BY hashrate DESC
        """)
        workers_result = db.execute(workers_query, {"address": address}).fetchall()

        # Compile all the information
        miner_stats = {
            "address": address,
            "current_hashrate": latest_stats_result.hashrate,
            "shares_per_second": latest_stats_result.sharespersecond,
            "last_block_found": {
                "timestamp": last_block_result.created.isoformat() if last_block_result else None,
                "block_height": last_block_result.blockheight if last_block_result else None
            },
            "balance": balance_result.amount if balance_result else 0,
            "last_payment": {
                "amount": payment_result.amount if payment_result else 0,
                "date": payment_result.last_payment_date.isoformat() if payment_result else None,
                "tx_link": tx_link
            },
            "total_paid": float(total_paid_result.total_paid),
            "paid_today": float(paid_today_result.paid_today),
            "workers": [{"worker": row.worker, "hashrate": float(row.hashrate)} for row in workers_result]
        }
        
        logger.info(f"Retrieved detailed miner information for address: {address}")
        return miner_stats
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching miner details for address {address}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching miner details: {str(e)}")


@app.get("/sigscore/miners/{address}/workers")
async def get_miner_workers(address: str, db: SessionLocal = Depends(get_db)):
    try:
        # Calculate the start time for the last 24 hours
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
        
        result = db.execute(query, {
            "address": address,
            "start_time": start_time,
            "end_time": end_time
        })

        # Process the results
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
    except Exception as e:
        logger.error(f"Error fetching 24-hour worker data for address {address}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching worker data: {str(e)}")
        
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)