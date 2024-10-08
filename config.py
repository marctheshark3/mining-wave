# config.py
from pydantic import BaseSettings
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

class Settings(BaseSettings):
    DB_HOST: str = os.getenv("DB_HOST", "")
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    POSTGRES_USER: str = os.getenv("DB_USER")
    POSTGRES_PASSWORD: str = os.getenv("DB_PASSWORD")
    POSTGRES_DB: str = os.getenv("DB_NAME")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost")

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

settings = Settings()

# You can add a print statement here for debugging purposes
# print(f"Loaded settings: {settings.dict()}")