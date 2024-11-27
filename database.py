# database.py
import asyncpg
from config import settings

async def create_db_pool():
    try:
        pool = await asyncpg.create_pool(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME
        )
        print(f"Successfully connected to database at {settings.DB_HOST}")
        return pool
    except Exception as e:
        print(f"Error connecting to database: {str(e)}")
        raise