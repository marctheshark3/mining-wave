# routes/sigscore/__init__.py
from fastapi import APIRouter
from .routes import router

# Re-export router for use in main app
__all__ = ['router']