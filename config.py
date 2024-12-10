# config.py
from pydantic import BaseSettings
from dotenv import load_dotenv
import os
from typing import Optional

# Load .env file
load_dotenv()

class Settings(BaseSettings):
    # Database settings
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    DB_USER: str = os.getenv("DB_USER", "")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME: str = os.getenv("DB_NAME", "")
    
    # Redis settings
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost")
    
    # Pool settings
    POOL_MIN_SIZE: int = int(os.getenv("POOL_MIN_SIZE", "5"))
    POOL_MAX_SIZE: int = int(os.getenv("POOL_MAX_SIZE", "20"))
    DB_TIMEOUT: int = int(os.getenv("DB_TIMEOUT", "30"))
    STATEMENT_TIMEOUT: int = int(os.getenv("STATEMENT_TIMEOUT", "30000"))
    
    # API settings
    MAX_CONNECTIONS: int = int(os.getenv("MAX_CONNECTIONS", "100"))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        case_sensitive = True

    def get_database_url(self) -> str:
        pass

# Create settings instance
settings = Settings()