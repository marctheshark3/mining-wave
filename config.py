# config.py
from pydantic import BaseSettings
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

class Settings(BaseSettings):
    DB_HOST: str = os.environ.get("DB_HOST", "")
    DB_PORT: str = os.environ.get("DB_PORT", "5432")
    DB_USER: str = os.environ.get("DB_USER")  # Changed from POSTGRES_USER
    DB_PASSWORD: str = os.environ.get("DB_PASSWORD")  # Changed from POSTGRES_PASSWORD
    DB_NAME: str = os.environ.get("DB_NAME")  # Changed from POSTGRES_DB
    REDIS_URL: str = os.environ.get("REDIS_URL", "redis://localhost")

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

    def get_database_url(self) -> str:
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

settings = Settings()