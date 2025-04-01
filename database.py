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
            # Calculate per-worker pool sizes
            worker_count = 4  # Matches the number of workers in docker-compose
            per_worker_min = max(1, settings.POOL_MIN_SIZE // worker_count)
            per_worker_max = max(3, settings.POOL_MAX_SIZE // worker_count)
            
            async def init_connection(conn):
                logger.info("New database connection initialized")
                return conn
            
            pool = await asyncpg.create_pool(
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                database=settings.DB_NAME,
                min_size=per_worker_min,  # Adjusted for per-worker
                max_size=per_worker_max,  # Adjusted for per-worker
                max_queries=50000,
                max_inactive_connection_lifetime=600.0,  # 10 minutes
                timeout=30.0,
                command_timeout=60.0,
                setup=cls._setup_connection,
                init=init_connection
            )
            
            # Log initial pool creation
            logger.info(
                "Created database pool",
                extra={
                    "min_size": per_worker_min,
                    "max_size": per_worker_max,
                    "worker_count": worker_count,
                    "total_min": per_worker_min * worker_count,
                    "total_max": per_worker_max * worker_count
                }
            )
            
            return pool
        except Exception as e:
            logger.error(f"Failed to create connection pool: {str(e)}")
            raise

    @staticmethod
    async def _setup_connection(conn: asyncpg.Connection):
        """Configure each connection in the pool"""
        await conn.execute('SET statement_timeout = 30000')  # 30 seconds
        await conn.execute('SET idle_in_transaction_session_timeout = 60000')  # 1 minute
        await conn.execute("SET application_name TO 'mining-wave-worker'")

    @classmethod
    @asynccontextmanager
    async def acquire(cls):
        """Smart connection acquisition with retry logic and monitoring"""
        current_time = time.time()
        conn_id = None
        
        try:
            pool = await cls.get_pool()
            
            # Check pool capacity before acquiring
            stats = await cls.get_pool_stats()
            if stats['pool_available'] == 0 and stats['pool_size'] >= stats['pool_max_size']:
                logger.warning("Pool at capacity, attempting cleanup before acquisition")
                await cls.cleanup_connections()
            
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
        """Smart cleanup of stale connections with worker awareness"""
        try:
            conn = await asyncpg.connect(
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                database=settings.DB_NAME
            )
            
            # Get detailed connection statistics
            stats = await conn.fetch("""
                SELECT 
                    application_name,
                    state,
                    COUNT(*) as conn_count,
                    MAX(EXTRACT(EPOCH FROM (NOW() - state_change))) as max_idle_time
                FROM pg_stat_activity
                WHERE datname = current_database()
                AND pid <> pg_backend_pid()
                GROUP BY application_name, state
            """)
            
            total_connections = sum(row['conn_count'] for row in stats)
            
            # Only cleanup if we're approaching capacity
            if total_connections > (settings.MAX_CONNECTIONS * 0.8):  # 80% threshold
                # Kill idle connections older than 10 minutes
                await conn.execute("""
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE datname = current_database()
                    AND pid <> pg_backend_pid()
                    AND state = 'idle'
                    AND state_change < NOW() - INTERVAL '10 minutes'
                    -- Preserve at least one connection per worker
                    AND application_name IN (
                        SELECT application_name 
                        FROM pg_stat_activity 
                        GROUP BY application_name 
                        HAVING COUNT(*) > 1
                    );
                """)
                
                # Log detailed cleanup info
                logger.info(
                    "Connection cleanup stats",
                    extra={
                        "total_connections": total_connections,
                        "max_connections": settings.MAX_CONNECTIONS,
                        "connection_stats": [
                            {
                                "app": row['application_name'],
                                "state": row['state'],
                                "count": row['conn_count'],
                                "max_idle_time": row['max_idle_time']
                            }
                            for row in stats
                        ]
                    }
                )
            
            await conn.close()
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