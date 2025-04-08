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
import psutil
import time
from fastapi.responses import RedirectResponse

from database import DatabasePool
from routes import miningcore, sigscore, general, demurrage
from middleware import setup_middleware
from utils.logging import logger, start_telegram_handler, stop_telegram_handler
from config import settings

async def monitor_system_health():
    """Monitor system resources and health metrics"""
    unhealthy_count = 0
    while True:
        try:
            # System metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Database metrics
            pool_stats = await DatabasePool.get_pool_stats()
            pool_size = pool_stats.get("pool_size", 0)
            max_size = pool_stats.get("pool_max_size", 20)
            available = pool_stats.get("pool_available", 0)
            
            # Log system metrics
            metrics = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": disk.percent,
                "pool_usage": f"{pool_size}/{max_size}",
                "pool_available": available
            }
            
            # Check for concerning conditions
            is_critical = False
            reasons = []
            
            if cpu_percent > 85:
                reasons.append(f"CPU usage critical: {cpu_percent}%")
                is_critical = True
            
            if memory.percent > 90:
                reasons.append(f"Memory usage critical: {memory.percent}%")
                is_critical = True
            
            if disk.percent > 95:
                reasons.append(f"Disk usage critical: {disk.percent}%")
                is_critical = True
            
            if pool_size >= max_size:
                reasons.append(f"Connection pool at capacity: {pool_size}/{max_size}")
                is_critical = True
            elif pool_size > max_size * 0.9:
                reasons.append(f"Connection pool near capacity: {pool_size}/{max_size}")
                
            if is_critical:
                logger.error(f"System resources critical: {metrics}\nReasons: {', '.join(reasons)}")
                unhealthy_count += 1
                
                if unhealthy_count >= settings.MAX_UNHEALTHY_COUNT:
                    logger.critical(
                        f"System consistently unhealthy!\nMetrics: {metrics}\n"
                        f"Reasons: {', '.join(reasons)}"
                    )
                    # Reset counter to avoid spam
                    unhealthy_count = 0
            else:
                # Only log metrics every 5 minutes if healthy
                if time.time() % 300 < 1:  # Log every ~5 minutes
                    logger.info(f"System healthy - Metrics: {metrics}")
                unhealthy_count = 0
            
            # Cleanup if needed
            if pool_size > max_size * 0.9:
                logger.warning(f"High pool usage detected ({pool_size}/{max_size}), initiating cleanup")
                await DatabasePool.cleanup_connections()
            
            await asyncio.sleep(settings.HEALTH_CHECK_INTERVAL)
            
        except Exception as e:
            logger.error(f"Error in health monitoring: {str(e)}")
            await asyncio.sleep(60)  # Wait longer on error

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for the FastAPI application"""
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        try:
            # Start Telegram handler if configured
            start_telegram_handler()
            
            # Initialize database pool
            pool = await DatabasePool.get_pool()
            app.state.pool = pool
            
            # Initialize Redis cache with our custom configuration
            redis = await setup_cache(settings.REDIS_URL)
            
            # Initialize rate limiter
            await FastAPILimiter.init(redis)
            
            # Start monitoring tasks
            app.state.monitor_tasks = [
                asyncio.create_task(monitor_system_health())
            ]
            
            logger.info("Application startup completed successfully")
            
            yield
            
            # Cleanup
            logger.info("Starting application shutdown")
            for task in app.state.monitor_tasks:
                task.cancel()
            await DatabasePool.close()
            if redis:
                await redis.close()
            
            # Stop Telegram handler
            stop_telegram_handler()
            
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
    origins = [
        "http://localhost:5173",    # Vite development server
        "http://localhost:3000",    # Alternative development port
        "http://localhost:8080",    # Another common development port
        "http://127.0.0.1:5173",    # Alternative localhost
        "http://127.0.0.1:3000",    # Alternative localhost
        "http://127.0.0.1:8080",    # Alternative localhost
    ]
    
    # In production, add the actual domain
    if not settings.DEBUG:
        # Add production domains here
        production_origins = settings.ALLOWED_ORIGINS.split(',') if settings.ALLOWED_ORIGINS else []
        origins.extend(production_origins)
    else:
        # In development, can allow all origins
        origins.append("*")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        max_age=86400,  # Cache preflight requests for 24 hours
    )
    
    # Include routers
    app.include_router(general.router)
    app.include_router(miningcore.router, prefix="/miningcore")
    app.include_router(sigscore.router, prefix="/sigscore")
    app.include_router(demurrage.router, prefix="/demurrage")
    
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

@app.get("/sigscore/demurrage/{path:path}", include_in_schema=False)
async def redirect_old_demurrage_path(path: str):
    """
    Redirect legacy /sigscore/demurrage/* requests to /demurrage/*
    This handles clients that haven't updated to the new API path structure.
    """
    logger.info(f"Redirecting legacy request from /sigscore/demurrage/{path} to /demurrage/{path}")
    return RedirectResponse(url=f"/demurrage/{path}", status_code=307)

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