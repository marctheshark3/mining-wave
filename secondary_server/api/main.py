from fastapi import FastAPI, Depends
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@secondary_db:5434/{os.getenv('POSTGRES_DB')}"

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
    metadata = MetaData()
    metadata.reflect(bind=engine)
    return {"tables": list(metadata.tables.keys())}

@app.get("/table/{table_name}")
async def get_table_data(table_name: str, db: SessionLocal = Depends(get_db)):
    metadata = MetaData()
    try:
        table = Table(table_name, metadata, autoload_with=engine)
        query = table.select()
        result = db.execute(query)
        return [dict(row) for row in result]
    except Exception as e:
        return {"error": f"Error fetching data from {table_name}: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)