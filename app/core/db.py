import pymongo
from loguru import logger

from app.core.config import settings
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
import models as models

DB_SESSION = None


async def initiate_database():
    client = AsyncIOMotorClient(settings.DATABASE_URL)
    await init_beanie(
        database=client.get_default_database(settings.MONGODB_DB), document_models=models.__all__
    )

