# config.py
from pydantic import BaseSettings
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

class Settings(BaseSettings):

    DB_HOST: str = os.getenv("DB_HOST", "")
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    DB_USER: str = os.getenv("DB_USER")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD")
    DB_NAME: str = os.getenv("DB_NAME")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost")


    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

    def get_database_url(self) -> str:
        # return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        pass

settings = Settings()