# routes/general.py
from fastapi import APIRouter, Depends
from fastapi_limiter.depends import RateLimiter
from database import DatabasePool
import asyncpg

router = APIRouter()

async def get_connection():
    """Get database connection from pool"""
    pool = await DatabasePool.get_pool()
    async with pool.acquire() as connection:
        yield connection

@router.get("/", dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def root():
    return {"message": "Welcome to the Mining Core API"}

@router.get("/tables")
async def list_tables(conn: asyncpg.Connection = Depends(get_connection)):
    """List all available database tables"""
    query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
    """
    tables = await conn.fetch(query)
    return [table['table_name'] for table in tables]

@router.get("/test_db_connection")
async def test_db_connection(conn: asyncpg.Connection = Depends(get_connection)):
    """Test database connectivity"""
    try:
        await conn.fetchval("SELECT 1")
        return {"status": "connected"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}