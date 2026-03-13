"""MongoDB connection manager using Motor and Beanie ODM."""

import logging
from typing import List, Optional, Type

from beanie import Document, init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings

logger = logging.getLogger(__name__)


class MongoDB:
    """MongoDB connection manager.

    Handles connection lifecycle for Motor async client
    and Beanie ODM initialization.
    """

    def __init__(self) -> None:
        self.client: Optional[AsyncIOMotorClient] = None

    async def connect(
        self,
        document_models: Optional[List[Type[Document]]] = None,
    ) -> None:
        """Connect to MongoDB and initialize Beanie ODM.

        Args:
            document_models: List of Beanie Document classes to register.
        """
        logger.info(f"Connecting to MongoDB at {settings.MONGODB_URL}...")
        self.client = AsyncIOMotorClient(settings.MONGODB_URL)
        database = self.client[settings.MONGODB_DB_NAME]

        await init_beanie(
            database=database,
            document_models=document_models or [],
        )
        logger.info(
            f"Connected to MongoDB database: {settings.MONGODB_DB_NAME}"
        )

    async def close(self) -> None:
        """Close the MongoDB connection."""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed.")
