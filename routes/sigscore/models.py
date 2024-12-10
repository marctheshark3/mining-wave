# routes/sigscore/models.py
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class LoyalMiner(BaseModel):
    address: str
    days_active: int
    weekly_avg_hashrate: float
    current_balance: float
    last_payment: Optional[str]

class MinerSettings(BaseModel):
    miner_address: str
    minimum_payout_threshold: float
    swapping: bool
    created_at: str

class WorkerStats(BaseModel):
    worker: str
    hashrate: float
    shares: float

class MinerPayment(BaseModel):
    amount: float
    date: Optional[str]
    tx_id: Optional[str]

class MinerDetails(BaseModel):
    address: str
    balance: float
    current_hashrate: float
    shares_per_second: float
    effort: float
    time_to_find: float
    last_block_found: Dict[str, Any]
    payments: Dict[str, Any]
    workers: List[WorkerStats]