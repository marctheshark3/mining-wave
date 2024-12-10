# api.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from fastapi_cache import FastAPICache
from fastapi_limiter import FastAPILimiter
from redis import asyncio as aioredis
from utils.cache import setup_cache
import asyncio
import uvicorn
from typing import Dict, Any

from database import DatabasePool
from routes import miningcore, sigscore, general
from middleware import setup_middleware
from utils.logging import logger
from config import settings

async def monitor_connections():
    """Monitor database connections and cleanup when necessary"""
    while True:
        try:
            pool_stats = await DatabasePool.get_pool_stats()
            logger.info(f"Pool stats: {pool_stats}")
            
            pool_size = pool_stats.get("pool_size", 0)
            max_size = pool_stats.get("pool_max_size", 20)
            if pool_size > max_size * 0.8:
                logger.warning(f"High connection usage detected ({pool_size}/{max_size}), initiating cleanup")
                await DatabasePool.cleanup_connections()
            
            await asyncio.sleep(30)  # Check every 30 seconds
        except Exception as e:
            logger.error(f"Error in connection monitoring: {str(e)}")
            await asyncio.sleep(60)  # Wait longer on error

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for the FastAPI application"""
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        try:
            # Initialize database pool
            pool = await DatabasePool.get_pool()
            app.state.pool = pool
            
            # Initialize Redis cache with our custom configuration
            redis = await setup_cache(settings.REDIS_URL)
            
            # Initialize rate limiter
            await FastAPILimiter.init(redis)
            
            # Start monitoring task
            app.state.monitor_task = asyncio.create_task(monitor_connections())
            logger.info("Application startup completed successfully")
            
            yield
            
            # Cleanup
            logger.info("Starting application shutdown")
            app.state.monitor_task.cancel()
            await DatabasePool.close()
            if redis:
                await redis.close()
            logger.info("Application shutdown completed")
            break
            
        except Exception as e:
            retry_count += 1
            logger.error(f"Startup attempt {retry_count} failed: {str(e)}")
            if retry_count == max_retries:
                raise
            await asyncio.sleep(5)  # Wait before retrying

def create_application() -> FastAPI:
    """Create and configure the FastAPI application"""
    app = FastAPI(
        title="MiningWave API",
        description="FastAPI-based microservice for crypto mining pool metrics and management",
        version="1.0.0",
        lifespan=lifespan
    )
    
    # Setup CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Adjust for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(general.router)
    app.include_router(miningcore.router, prefix="/miningcore")
    app.include_router(sigscore.router, prefix="/sigscore")
    
    # Additional middleware
    setup_middleware(app)
    
    return app

# Create the application instance
app = create_application()

@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint for the API"""
    try:
        pool_stats = await DatabasePool.get_pool_stats()
        return {
            "status": "healthy",
            "database_pool": pool_stats,
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Health check failed: {str(e)}"
        )

@app.get("/")
async def root():
    """Root endpoint returning API information"""
    return {
        "app": "MiningWave API",
        "version": "1.0.0",
        "status": "operational"
    }

@app.get("/routes")
async def list_routes():
    """List all available routes in the API"""
    routes = []
    for route in app.routes:
        if hasattr(route, "methods") and hasattr(route, "path"):
            for method in route.methods:
                routes.append({
                    "path": route.path,
                    "method": method,
                    "name": route.name if hasattr(route, "name") else None
                })
    return sorted(routes, key=lambda x: x["path"])

if __name__ == "__main__":
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        workers=4,
        loop="uvloop",
        limit_concurrency=100,
        timeout_keep_alive=30,
        access_log=True
    )