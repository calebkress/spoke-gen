from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import get_settings

_settings = get_settings()
_client: Optional[AsyncIOMotorClient] = None

def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(_settings.mongodb_uri)
    return _client

def get_db():
    return get_client()[_settings.mongodb_db_name]

def get_spokes_collection():
    return get_db()["spokes"]