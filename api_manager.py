# api_manager.py
from fastapi import FastAPI, Request
from fastapi.middleware.base import BaseHTTPMiddleware
import time
import asyncio
from typing import Dict, Set
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[str] = set()
        self.request_times: Dict[str, float] = {}
        self.lock = asyncio.Lock()
        
        # Configuration
        self.max_concurrent_connections = 50
        self.request_timeout = 30.0  # seconds
        self.rate_limit_window = 60  # seconds
        self.max_requests_per_window = 100
        
    async def add_connection(self, client_id: str) -> bool:
        """Add a new connection if within limits."""
        async with self.lock:
            current_time = time.time()
            
            # Clean up old requests
            self._cleanup_old_requests(current_time)
            
            # Check if client is within rate limit
            client_requests = sum(1 for t in self.request_times.values() 
                                if t > current_time - self.rate_limit_window)
            
            if (len(self.active_connections) < self.max_concurrent_connections and 
                client_requests < self.max_requests_per_window):
                self.active_connections.add(client_id)
                self.request_times[client_id] = current_time
                return True
            return False
            
    async def remove_connection(self, client_id: str):
        """Remove a connection."""
        async with self.lock:
            self.active_connections.discard(client_id)
            
    def _cleanup_old_requests(self, current_time: float):
        """Clean up old request records."""
        cutoff_time = current_time - self.rate_limit_window
        self.request_times = {
            client_id: timestamp 
            for client_id, timestamp in self.request_times.items() 
            if timestamp > cutoff_time
        }

class ConnectionManagerMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: FastAPI, connection_manager: ConnectionManager):
        super().__init__(app)
        self.connection_manager = connection_manager
        
    async def dispatch(self, request: Request, call_next):
        client_id = f"{request.client.host}:{request.client.port}"
        
        # Try to add connection
        if not await self.connection_manager.add_connection(client_id):
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."}
            )
            
        try:
            # Set timeout for the request
            response = await asyncio.wait_for(
                call_next(request),
                timeout=self.connection_manager.request_timeout
            )
            return response
            
        except asyncio.TimeoutError:
            logger.warning(f"Request timeout for client {client_id}")
            return JSONResponse(
                status_code=504,
                content={"detail": "Request timeout"}
            )
            
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"}
            )
            
        finally:
            await self.connection_manager.remove_connection(client_id)