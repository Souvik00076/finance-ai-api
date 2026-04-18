from typing import Optional, List
from datetime import datetime, timezone

from beanie import Document
from pydantic import BaseModel, Field


def _now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


class Item(BaseModel):
    """Embedded item subdocument (equivalent to itemSchema)."""
    name: str
    price: float
    currency: str


class UserData(Document):
    """User data document model for MongoDB (Beanie ODM).

    Equivalent of the Mongoose 'user_data' collection.
    """

    chat_id: Optional[str] = None
    source: str
    created_at_ms: int = Field(default_factory=_now_ms)
    categories: List[str] = Field(default_factory=list)
    items: List[Item] = Field(default_factory=list)

    class Settings:
        name = "user_datas"
