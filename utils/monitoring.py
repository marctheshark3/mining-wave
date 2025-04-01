# monitoring.py
import asyncio
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

logger = logging.getLogger(__name__)

class HealthMonitor:
    def __init__(self):
        self.last_activity = datetime.now()
        self.is_healthy = True
        
    async def monitor_task(self):
        while True:
            try:
                current_time = datetime.now()
                time_since_last_activity = (current_time - self.last_activity).total_seconds()
                
                # If no activity for more than 30 seconds, log a warning
                if time_since_last_activity > 30:
                    logger.warning(f"No activity detected for {time_since_last_activity} seconds")
                
                # If no activity for more than 60 seconds, mark as unhealthy
                self.is_healthy = time_since_last_activity <= 60
                
                await asyncio.sleep(10)  # Check every 10 seconds
            except Exception as e:
                logger.error(f"Error in health monitor: {str(e)}")
                await asyncio.sleep(10)
    
    def update_activity(self):
        self.last_activity = datetime.now()

# Middleware to track activity
class ActivityMiddleware:
    def __init__(self, app: FastAPI, health_monitor: HealthMonitor):
        self.app = app
        self.health_monitor = health_monitor
        
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            self.health_monitor.update_activity()
        return await self.app(scope, receive, send)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup
    health_monitor = HealthMonitor()
    app.state.health_monitor = health_monitor
    
    # Start monitoring task
    monitoring_task = asyncio.create_task(health_monitor.monitor_task())
    
    yield
    
    # Cleanup
    monitoring_task.cancel()
    try:
        await monitoring_task
    except asyncio.CancelledError:
        pass