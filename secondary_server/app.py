from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Connect to the secondary database
DATABASE_URL = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{os.getenv('DATABASE_HOST')}:5432/{os.getenv('POSTGRES_DB')}"

# SQLAlchemy setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
metadata = MetaData(bind=engine)

# FastAPI instance
app = FastAPI()

# Dynamic route for all tables
@app.get("/tables/{table_name}")
def read_table(table_name: str):
    try:
        table = Table(table_name, metadata, autoload_with=engine)
        session = SessionLocal()
        query = session.query(table).all()
        session.close()
        return [dict(row) for row in query]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
