# routes/pool/routes.py
from fastapi import APIRouter, HTTPException, Depends
from fastapi_limiter.depends import RateLimiter
from .models import PoolInfoResponse, BasicInfoResponse, FeeResponse
from .utils import get_pool_config, get_pool_info, reload_pool_config
from utils.logging import logger

# Create router without requiring API key authentication
router = APIRouter(
    prefix="/pool",
    tags=["pool"],
    responses={404: {"description": "Not found"}},
)

@router.get(
    "/info",
    response_model=PoolInfoResponse,
    summary="Get complete pool information",
    description="Returns comprehensive pool information including location, fees, software type, and API details",
    dependencies=[Depends(RateLimiter(times=30, seconds=60))]
)
async def get_pool_information():
    """Get complete pool information"""
    try:
        pool_info = await get_pool_info()
        return PoolInfoResponse(
            name=pool_info.name,
            location=pool_info.location,
            contact_email=pool_info.contact_email,
            coin=pool_info.coin,
            pool_url=pool_info.pool_url,
            api_url=pool_info.api_url,
            software_type=pool_info.software_type,
            fee_percentage=pool_info.fee_percentage,
            status=pool_info.status
        )
    except Exception as e:
        logger.error(f"Error retrieving pool information: {e}")
        raise HTTPException(status_code=500, detail="Unable to retrieve pool information")

@router.get(
    "/api-url",
    response_model=BasicInfoResponse,
    summary="Get pool API URL",
    description="Returns the pool's API URL that provides current hashrate and online miners",
    dependencies=[Depends(RateLimiter(times=60, seconds=60))]
)
async def get_pool_api_url():
    """Get the pool API URL"""
    try:
        pool_info = await get_pool_info()
        return BasicInfoResponse(value=pool_info.api_url)
    except Exception as e:
        logger.error(f"Error retrieving pool API URL: {e}")
        raise HTTPException(status_code=500, detail="Unable to retrieve pool API URL")

@router.get(
    "/software",
    response_model=BasicInfoResponse,
    summary="Get pool software type",
    description="Returns the software type used by the pool (mpos, yiimp, custom, etc.)",
    dependencies=[Depends(RateLimiter(times=60, seconds=60))]
)
async def get_pool_software():
    """Get the pool software type"""
    try:
        pool_info = await get_pool_info()
        return BasicInfoResponse(value=pool_info.software_type)
    except Exception as e:
        logger.error(f"Error retrieving pool software type: {e}")
        raise HTTPException(status_code=500, detail="Unable to retrieve pool software type")

@router.get(
    "/fee",
    response_model=FeeResponse,
    summary="Get pool fee percentage",
    description="Returns the pool's fee percentage",
    dependencies=[Depends(RateLimiter(times=60, seconds=60))]
)
async def get_pool_fee():
    """Get the pool fee percentage"""
    try:
        pool_info = await get_pool_info()
        return FeeResponse(
            fee_percentage=pool_info.fee_percentage,
            currency=pool_info.coin.symbol
        )
    except Exception as e:
        logger.error(f"Error retrieving pool fee: {e}")
        raise HTTPException(status_code=500, detail="Unable to retrieve pool fee")

@router.get(
    "/location",
    response_model=BasicInfoResponse,
    summary="Get pool location",
    description="Returns the geographical location of the pool",
    dependencies=[Depends(RateLimiter(times=60, seconds=60))]
)
async def get_pool_location():
    """Get the pool location"""
    try:
        pool_info = await get_pool_info()
        return BasicInfoResponse(value=pool_info.location)
    except Exception as e:
        logger.error(f"Error retrieving pool location: {e}")
        raise HTTPException(status_code=500, detail="Unable to retrieve pool location")

@router.get(
    "/url",
    response_model=BasicInfoResponse,
    summary="Get pool website URL",
    description="Returns the pool's main website URL",
    dependencies=[Depends(RateLimiter(times=60, seconds=60))]
)
async def get_pool_url():
    """Get the pool website URL"""
    try:
        pool_info = await get_pool_info()
        return BasicInfoResponse(value=pool_info.pool_url)
    except Exception as e:
        logger.error(f"Error retrieving pool URL: {e}")
        raise HTTPException(status_code=500, detail="Unable to retrieve pool URL")

@router.get(
    "/coin",
    summary="Get pool coin information",
    description="Returns information about the coin being mined",
    dependencies=[Depends(RateLimiter(times=60, seconds=60))]
)
async def get_pool_coin():
    """Get pool coin information"""
    try:
        pool_info = await get_pool_info()
        return pool_info.coin
    except Exception as e:
        logger.error(f"Error retrieving pool coin info: {e}")
        raise HTTPException(status_code=500, detail="Unable to retrieve pool coin information")

@router.post(
    "/reload",
    summary="Reload pool configuration",
    description="Forces a reload of the pool configuration from file (admin function)",
    dependencies=[Depends(RateLimiter(times=5, seconds=300))]
)
async def reload_configuration():
    """Reload pool configuration from file"""
    try:
        await reload_pool_config()
        logger.info("Pool configuration reloaded successfully")
        return {"message": "Pool configuration reloaded successfully"}
    except Exception as e:
        logger.error(f"Error reloading pool configuration: {e}")
        raise HTTPException(status_code=500, detail="Unable to reload pool configuration")

@router.get(
    "/status",
    summary="Get pool status",
    description="Returns the current operational status of the pool",
    dependencies=[Depends(RateLimiter(times=60, seconds=60))]
)
async def get_pool_status():
    """Get pool operational status"""
    try:
        pool_info = await get_pool_info()
        return {
            "status": pool_info.status,
            "name": pool_info.name,
            "location": pool_info.location,
            "last_updated": pool_info.last_updated
        }
    except Exception as e:
        logger.error(f"Error retrieving pool status: {e}")
        raise HTTPException(status_code=500, detail="Unable to retrieve pool status") 