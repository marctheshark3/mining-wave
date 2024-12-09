# database.py
import asyncpg
import asyncio
from config import settings
from utils.logging import logger
from typing import Optional

class DatabasePool:
    _instance: Optional[asyncpg.Pool] = None
    _lock = asyncio.Lock()

    @classmethod
    async def get_pool(cls):
        if not cls._instance:
            async with cls._lock:
                if not cls._instance:
                    # Try to clean up any existing connections first
                    await cls.cleanup_connections()
                    cls._instance = await cls._create_pool()
        return cls._instance

    @classmethod
    async def cleanup_connections(cls):
        """Kill existing connections to the database"""
        try:
            # Create a temporary connection to run the cleanup
            conn = await asyncpg.connect(
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                database=settings.DB_NAME
            )
            
            # Kill all existing connections to our database except our current one
            await conn.execute("""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = current_database()
                AND pid <> pg_backend_pid();
            """)
            
            await conn.close()
            logger.info("Successfully cleaned up existing database connections")
        except Exception as e:
            logger.error(f"Error during connection cleanup: {str(e)}")

    @classmethod
    async def _create_pool(cls):
        for attempt in range(3):
            try:
                return await asyncpg.create_pool(
                    host=settings.DB_HOST,
                    port=settings.DB_PORT,
                    user=settings.DB_USER,
                    password=settings.DB_PASSWORD,
                    database=settings.DB_NAME,
                    min_size=2,
                    max_size=5,
                    command_timeout=30
                )
            except Exception as e:
                logger.error(f"Database connection attempt {attempt + 1} failed: {str(e)}")
                if attempt == 2:
                    raise
                await asyncio.sleep(1)

    @classmethod
    async def close(cls):
        """Close the pool and reset the instance"""
        if cls._instance:
            await cls._instance.close()
            cls._instance = None
            logger.info("Database pool closed and reset")

async def create_db_pool():
    return await DatabasePool.get_pool()