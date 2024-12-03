# main.py
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

# Setup middleware
setup_middleware(app)

@app.on_event("startup")
async def startup_event():
    # Initialize database pool
    app.state.pool = await create_db_pool()

    # Initialize Redis for caching
    redis = aioredis.from_url(settings.REDIS_URL, encoding="utf8", decode_responses=True)
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache:")

    # Initialize rate limiter
    await FastAPILimiter.init(redis)

@app.on_event("shutdown")
async def shutdown_event():
    await app.state.pool.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, workers=4)