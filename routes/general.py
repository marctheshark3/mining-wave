# routes/general.py
from fastapi import APIRouter, Depends
from fastapi_limiter.depends import RateLimiter

router = APIRouter()

@router.get("/", dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def root():
    return {"message": "Welcome to the Mining Core API"}