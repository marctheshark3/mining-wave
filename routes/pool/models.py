from pydantic import BaseModel, HttpUrl, EmailStr
from typing import List, Optional
from datetime import datetime

class CoinInfo(BaseModel):
    """Model for coin information"""
    symbol: str
    name: str
    algorithm: str

class ApiEndpoints(BaseModel):
    """Model for API endpoint configurations"""
    pool_stats: str
    miners: str
    blocks: str
    payments: str

class Metadata(BaseModel):
    """Model for configuration metadata"""
    version: str
    created_by: str
    description: str

class PoolInfo(BaseModel):
    """Model for complete pool information"""
    name: str
    location: str
    contact_email: EmailStr
    coin: CoinInfo
    pool_url: str
    api_url: str
    software_type: str
    fee_percentage: float
    features: List[str]
    last_updated: datetime
    status: str

class PoolConfig(BaseModel):
    """Model for the complete pool configuration"""
    pool_info: PoolInfo
    api_endpoints: ApiEndpoints
    metadata: Metadata

class PoolInfoResponse(BaseModel):
    """Response model for pool info API"""
    name: str
    location: str
    contact_email: str
    coin: CoinInfo
    pool_url: str
    api_url: str
    software_type: str
    fee_percentage: float
    status: str

class BasicInfoResponse(BaseModel):
    """Basic response model for simple string/number values"""
    value: str

class FeeResponse(BaseModel):
    """Response model for fee information"""
    fee_percentage: float
    currency: str = "ERG" 