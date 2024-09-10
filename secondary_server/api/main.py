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
    }
    return address_columns.get(table_name, "address")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)