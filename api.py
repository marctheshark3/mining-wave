# api.py
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_limiter import FastAPILimiter
from redis import asyncio as aioredis

from config import settings
from database import create_db_pool
from routes import miningcore, sigscore, general
from middleware import setup_middleware
from utils.logging import setup_logger

app = FastAPI()
logger = setup_logger()

# Add routes
app.include_router(general.router)
app.include_router(miningcore.router)
app.include_router(sigscore.router)

# Log settings at startup
logger.info(f"Loaded settings: {settings.dict()}")

# Setup middleware
setup_middleware(app)

@app.on_event("startup")
async def startup_event():
    try:
        # Initialize database pool
        logger.info("Initializing database pool...")
        app.state.pool = await create_db_pool()
        logger.info("Database pool initialized successfully")

        # Initialize Redis for caching
        logger.info("Initializing Redis connection...")
        redis = aioredis.from_url(
            settings.REDIS_URL, 
            encoding="utf8", 
            decode_responses=True
        )
        FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache:")
        logger.info(f"Redis cache initialized at {settings.REDIS_URL}")

        # Initialize rate limiter
        logger.info("Initializing rate limiter...")
        await FastAPILimiter.init(redis)
        logger.info("Rate limiter initialized successfully")

    except Exception as e:
        logger.error(f"Startup error: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    try:
        logger.info("Shutting down database pool...")
        await app.state.pool.close()
        logger.info("Database pool closed successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")
        raise

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, workers=4)
