# middleware.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from utils.logging import logger
from datetime import datetime
import time

async def add_process_time_header(request: Request, call_next):
    """Middleware to track request processing time"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

class ActivityMiddleware:
    """Middleware to track API activity"""
    def __init__(self, app: FastAPI):
        self.app = app
        self.last_activity = datetime.now()
        
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            self.last_activity = datetime.now()
        return await self.app(scope, receive, send)

class LoggingMiddleware:
    """Middleware for request logging"""
    def __init__(self, app: FastAPI):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            start_time = time.time()
            
            # Create a modified send function to capture the response
            async def wrapped_send(message):
                if message["type"] == "http.response.start":
                    process_time = time.time() - start_time
                    status_code = message["status"]
                    logger.info(
                        f"Request: {scope['method']} {scope['path']} "
                        f"Status: {status_code} "
                        f"Duration: {process_time:.3f}s"
                    )
                await send(message)
            
            return await self.app(scope, receive, wrapped_send)
        return await self.app(scope, receive, send)

def setup_middleware(app: FastAPI):
    """Setup all middleware for the application"""
    # CORS middleware is already added in create_application()
    
    # Add custom middleware
    app.middleware("http")(add_process_time_header)
    app.add_middleware(ActivityMiddleware)
    app.add_middleware(LoggingMiddleware)
    
    logger.info("Middleware setup completed")