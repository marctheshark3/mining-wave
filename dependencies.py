# dependencies.py
import os
import secrets
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
from config import settings

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def verify_api_key(key: str = Security(api_key_header)):
    """
    Verifies the API key provided in the X-API-Key header.
    Raises HTTPException 401 if the key is invalid or missing.
    """
    if not settings.API_KEY:
        # Allow access if API_KEY is not configured (useful for local dev/testing)
        # Consider adding a warning log here if desired
        return True
        
    if key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API Key in X-API-Key header",
            headers={"WWW-Authenticate": "API Key"},
        )
        
    # Use secrets.compare_digest to prevent timing attacks
    if not secrets.compare_digest(key, settings.API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
            headers={"WWW-Authenticate": "API Key"},
        )
    return True # Indicate success 