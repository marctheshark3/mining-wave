# api.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_limiter import FastAPILimiter
from redis import asyncio as aioredis
import asyncio
import uvicorn
from contextlib import asynccontextmanager

from config import settings
from database import create_db_pool
from routes import miningcore, sigscore, general
from middleware import setup_middleware
from utils.logging import setup_logger

logger = setup_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # Initialize Redis
        redis = await aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf8",
            decode_responses=True,
            max_connections=10
        )
        
        # Clean up and initialize database pool
        app.state.pool = await create_db_pool()
        
        # Initialize cache and rate limiter
        FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache:")
        await FastAPILimiter.init(redis)
        
        yield
        
        # Cleanup
        await DatabasePool.close()
        if redis:
            await redis.close()
            
    except Exception as e:
        logger.error(f"Startup error: {str(e)}")
        # Make sure we cleanup even if startup fails
        await DatabasePool.close()
        raise

app = FastAPI(lifespan=lifespan)
app.include_router(general.router)
app.include_router(miningcore.router)
app.include_router(sigscore.router)
setup_middleware(app)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)