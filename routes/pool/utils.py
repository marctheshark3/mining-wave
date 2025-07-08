import json
import os
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import aiofiles
import asyncio
from .models import PoolConfig, PoolInfo
from utils.logging import logger

class PoolConfigManager:
    """Manager class for pool configuration"""
    
    def __init__(self, config_path: str = "data/pool_config.json"):
        self.config_path = Path(config_path)
        self._config: Optional[PoolConfig] = None
        self._last_modified: Optional[float] = None
        self._lock = asyncio.Lock()
    
    async def _load_config_from_file(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Pool configuration file not found: {self.config_path}")
        
        try:
            async with aiofiles.open(self.config_path, mode='r', encoding='utf-8') as file:
                content = await file.read()
                return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in pool configuration file: {e}")
            raise ValueError(f"Invalid JSON format in pool configuration: {e}")
        except Exception as e:
            logger.error(f"Error reading pool configuration file: {e}")
            raise
    
    async def _needs_reload(self) -> bool:
        """Check if configuration needs to be reloaded"""
        try:
            current_modified = self.config_path.stat().st_mtime
            return (self._last_modified is None or 
                   current_modified > self._last_modified or 
                   self._config is None)
        except Exception:
            return True
    
    async def get_config(self) -> PoolConfig:
        """Get pool configuration, reloading if necessary"""
        async with self._lock:
            if await self._needs_reload():
                try:
                    logger.info("Loading pool configuration from file")
                    config_data = await self._load_config_from_file()
                    self._config = PoolConfig(**config_data)
                    self._last_modified = self.config_path.stat().st_mtime
                    logger.info(f"Pool configuration loaded successfully: {self._config.pool_info.name}")
                except Exception as e:
                    logger.error(f"Failed to load pool configuration: {e}")
                    if self._config is None:
                        # If we have no config at all, create a minimal default
                        self._config = self._create_default_config()
                    raise
            
            return self._config
    
    def _create_default_config(self) -> PoolConfig:
        """Create a default configuration as fallback"""
        logger.warning("Creating default pool configuration as fallback")
        return PoolConfig(
            pool_info=PoolInfo(
                name="Default Pool",
                location="UNKNOWN",
                contact_email="admin@example.com",
                coin={
                    "symbol": "ERG",
                    "name": "Ergo",
                    "algorithm": "Autolykos"
                },
                pool_url="https://example.com",
                api_url="https://api.example.com",
                software_type="unknown",
                fee_percentage=0.0,
                features=[],
                last_updated=datetime.now(),
                status="inactive"
            ),
            api_endpoints={
                "pool_stats": "/stats",
                "miners": "/miners",
                "blocks": "/blocks",
                "payments": "/payments"
            },
            metadata={
                "version": "1.0.0",
                "created_by": "MiningWave API",
                "description": "Default configuration"
            }
        )
    
    async def reload_config(self) -> None:
        """Force reload of configuration"""
        async with self._lock:
            self._last_modified = None
            await self.get_config()

# Global config manager instance
pool_config_manager = PoolConfigManager()

# Convenience functions
async def get_pool_config() -> PoolConfig:
    """Get the current pool configuration"""
    return await pool_config_manager.get_config()

async def get_pool_info() -> PoolInfo:
    """Get just the pool info section"""
    config = await get_pool_config()
    return config.pool_info

async def reload_pool_config() -> None:
    """Reload pool configuration from file"""
    await pool_config_manager.reload_config() 