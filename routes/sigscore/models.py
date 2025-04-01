# routes/sigscore/models.py
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class LoyalMiner(BaseModel):
    address: str
    days_active: int
    weekly_avg_hashrate: float
    current_balance: float
    last_payment: Optional[str]

class BlockRequest(BaseModel):
    block_heights: List[int]

class MinerAverageParticipation(BaseModel):
    miner_address: str
    avg_shares: float
    avg_participation_percentage: float
    total_rewards: float
    block_count: int

class MultiBlockParticipation(BaseModel):
    block_heights: List[int]
    total_blocks: int
    miners: List[MinerAverageParticipation]
    start_timestamp: str
    end_timestamp: str

class MinerActivity(BaseModel):
    address: str
    days_active: int
    weekly_avg_hashrate: float
    current_balance: float
    last_payment: Optional[str]
    active_hours: int 

class MinerParticipation(BaseModel):
    miner_address: str
    shares: float
    participation_percentage: float
    reward: float

class BlockParticipation(BaseModel):
    block_height: int
    total_shares: float
    timestamp: str
    miners: List[MinerParticipation]

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