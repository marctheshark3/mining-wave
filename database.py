# database.py
import asyncpg
import asyncio
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any
from config import settings
from utils.logging import logger
import time
import backoff

class DatabasePool:
    _instance: Optional[asyncpg.Pool] = None
    _lock = asyncio.Lock()
    _last_connection_time: Dict[str, float] = {}
    _connection_attempts = 0
    MAX_RETRIES = 3
    COOLDOWN_PERIOD = 5  # seconds
    
    @classmethod
    async def get_pool(cls):
        if not cls._instance:
            async with cls._lock:
                if not cls._instance:
                    await cls.cleanup_connections()
                    cls._instance = await cls._create_pool()
        return cls._instance

    @classmethod
    @backoff.on_exception(
        backoff.expo,
        (asyncpg.TooManyConnectionsError, asyncpg.CannotConnectNowError),
        max_tries=3,
        max_time=30
    )
    async def _create_pool(cls) -> asyncpg.Pool:
        """Create a new connection pool with advanced configuration"""
        try:
            return await asyncpg.create_pool(
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                database=settings.DB_NAME,
                min_size=settings.POOL_MIN_SIZE,
                max_size=settings.POOL_MAX_SIZE,
                max_queries=50000,   # Maximum queries per connection
                max_inactive_connection_lifetime=300.0,  # 5 minutes
                timeout=30.0,        # Connection timeout
                command_timeout=60.0, # Command execution timeout
                setup=cls._setup_connection
            )
        except Exception as e:
            logger.error(f"Failed to create connection pool: {str(e)}")
            raise

    @staticmethod
    async def _setup_connection(conn: asyncpg.Connection):
        """Configure each connection in the pool"""
        await conn.execute('SET statement_timeout = 30000')  # 30 seconds
        await conn.execute('SET idle_in_transaction_session_timeout = 60000')  # 1 minute

    @classmethod
    @asynccontextmanager
    async def acquire(cls):
        """Smart connection acquisition with retry logic and monitoring"""
        current_time = time.time()
        conn_id = None

        try:
            pool = await cls.get_pool()
            async with pool.acquire() as connection:
                conn_id = id(connection)
                cls._last_connection_time[conn_id] = current_time
                cls._connection_attempts += 1
                
                try:
                    yield connection
                finally:
                    if conn_id in cls._last_connection_time:
                        del cls._last_connection_time[conn_id]
        except asyncpg.TooManyConnectionsError:
            logger.warning("Too many connections, initiating connection cleanup")
            await cls.cleanup_connections()
            raise
        except Exception as e:
            logger.error(f"Database connection error: {str(e)}")
            await cls.handle_connection_error()
            raise

    @classmethod
    async def cleanup_connections(cls):
        """Aggressively cleanup stale connections"""
        try:
            conn = await asyncpg.connect(
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                database=settings.DB_NAME
            )
            
            # Kill idle connections older than 5 minutes
            await conn.execute("""
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = current_database()
                AND pid <> pg_backend_pid()
                AND state = 'idle'
                AND state_change < NOW() - INTERVAL '5 minutes';
            """)
            
            await conn.close()
            logger.info("Successfully cleaned up stale database connections")
        except Exception as e:
            logger.error(f"Error during connection cleanup: {str(e)}")

    @classmethod
    async def close(cls):
        """Gracefully close the connection pool"""
        if cls._instance:
            await cls.cleanup_connections()
            await cls._instance.close()
            cls._instance = None
            cls._last_connection_time.clear()
            cls._connection_attempts = 0
            logger.info("Database pool closed and reset")

    @classmethod
    async def handle_connection_error(cls):
        """Handle connection errors with exponential backoff"""
        cls._connection_attempts += 1
        wait_time = min(2 ** cls._connection_attempts, 30)  # Max 30 seconds
        logger.warning(f"Connection error, waiting {wait_time} seconds before retry")
        await asyncio.sleep(wait_time)

    @classmethod
    async def get_pool_stats(cls) -> Dict[str, Any]:
        """Get current pool statistics"""
        if not cls._instance:
            return {"status": "not_initialized"}
            
        return {
            "active_connections": len(cls._last_connection_time),
            "total_connection_attempts": cls._connection_attempts,
            "pool_min_size": settings.POOL_MIN_SIZE,
            "pool_max_size": settings.POOL_MAX_SIZE,
            "pool_size": len(cls._instance._holders) if cls._instance else 0,
            "pool_available": len([h for h in cls._instance._holders if not h._in_use]) if cls._instance else 0,
        }

# Global connection pool manager
db_pool = DatabasePool()