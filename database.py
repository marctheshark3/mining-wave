# database.py
import asyncpg
from config import settings

async def create_db_pool():
    return await asyncpg.create_pool(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        database=settings.DB_NAME,
        min_size=2,        # Add this
        max_size=10,       # Add this
        command_timeout=60  # Add this
    )