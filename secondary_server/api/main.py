from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os
from dotenv import load_dotenv
from sqlalchemy.sql import text
import logging

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

@app.get("/sigscore/live")
async def get_miner_stats(db: SessionLocal = Depends(get_db)):
    try:
        query = text("""
            WITH latest_entries AS (
                SELECT 
                    miner,
                    hashrate,
                    sharespersecond,
                    created,
                    ROW_NUMBER() OVER (PARTITION BY miner ORDER BY created DESC) as row_num
                FROM minerstats
            )
            SELECT miner, hashrate, sharespersecond
            FROM latest_entries
            WHERE row_num = 1
        """)
        
        result = db.execute(query)
        
        columns = result.keys()
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
        
        logger.info(f"Retrieved miner stats for {len(rows)} miners")
        return rows
    except Exception as e:
        logger.error(f"Error fetching miner stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching miner stats: {str(e)}")

@app.get("/sigscore/minerstats/{address}")
async def get_sigscore_miner_stats(address: str, db: SessionLocal = Depends(get_db)):
    try:
        # Get current balance
        balance_query = text("""
            SELECT amount
            FROM balances
            WHERE address = :address
            ORDER BY updated DESC
            LIMIT 1
        """)
        balance_result = db.execute(balance_query, {"address": address}).fetchone()
        current_balance = balance_result[0] if balance_result else 0

        # Get latest payment data
        payment_query = text("""
            SELECT amount, created, transactionconfirmationdata
            FROM payments
            WHERE address = :address
            ORDER BY created DESC
            LIMIT 1
        """)
        payment_result = db.execute(payment_query, {"address": address}).fetchone()
        
        # Get total paid amount
        total_paid_query = text("""
            SELECT SUM(amount) as total_paid
            FROM payments
            WHERE address = :address
        """)
        total_paid_result = db.execute(total_paid_query, {"address": address}).fetchone()
        
        # Prepare the response
        response = {
            "address": address,
            "current_balance": current_balance,
            "last_paid_amount": payment_result[0] if payment_result else 0,
            "last_paid_date": payment_result[1].isoformat() if payment_result else None,
            "last_tx_data": payment_result[2] if payment_result else None,
            "total_paid": total_paid_result[0] if total_paid_result else 0
        }
        
        logger.info(f"Retrieved SigScore miner stats for address: {address}")
        return response
    except Exception as e:
        logger.error(f"Error fetching SigScore miner stats for address {address}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching SigScore miner stats: {str(e)}")

@app.get("/sigscore/live/{address}")
async def get_worker_performance(address: str, start_date: str = Query(...), end_date: str = Query(...), db: SessionLocal = Depends(get_db)):
    try:
        # Convert start_date and end_date to datetime objects
        start_datetime = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end_datetime = datetime.fromisoformat(end_date.replace('Z', '+00:00'))

        # Query to get hourly performance data for each worker
        query = text("""
            WITH hourly_data AS (
                SELECT 
                    miner,
                    worker,
                    date_trunc('hour', created) AS hour,
                    AVG(hashrate) AS avg_hashrate,
                    AVG(sharespersecond) AS avg_sharespersecond
                FROM minerstats
                WHERE miner = :address
                    AND created >= :start_date
                    AND created < :end_date
                GROUP BY miner, worker, date_trunc('hour', created)
            )
            SELECT 
                miner,
                worker,
                hour,
                avg_hashrate,
                avg_sharespersecond
            FROM hourly_data
            ORDER BY worker, hour
        """)

        result = db.execute(query, {
            "address": address,
            "start_date": start_datetime,
            "end_date": end_datetime
        })

        # Process the results
        performance_data = {}
        for row in result:
            worker = row.worker
            hour = row.hour.isoformat()
            if worker not in performance_data:
                performance_data[worker] = []
            performance_data[worker].append({
                "created": hour,
                "hashrate": float(row.avg_hashrate),
                "sharesPerSecond": float(row.avg_sharespersecond)
            })

        logger.info(f"Retrieved worker performance data for address: {address}")
        return performance_data
    except Exception as e:
        logger.error(f"Error fetching worker performance data for address {address}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching worker performance data: {str(e)}")
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)