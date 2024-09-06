from fastapi import FastAPI, Depends, HTTPException
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
DB_PORT = os.getenv('DB_PORT', '5432')  # This should be 5432 for internal Docker network communication
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


@app.get("/table/{table_name}")
async def get_table_data(table_name: str, db: SessionLocal = Depends(get_db)):
    try:
        # Use text() to create a safe SQL query
        query = text(f"SELECT * FROM {table_name}")
        result = db.execute(query)
        
        # Get column names
        columns = result.keys()
        
        # Fetch rows and convert to list of dicts
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
        
        logger.info(f"Retrieved {len(rows)} rows from table {table_name}")
        return rows
    except Exception as e:
        logger.error(f"Error fetching data from {table_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching data from {table_name}: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)