from datetime import datetime, timezone

from beanie import Document
from pydantic import Field


def _now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


class UserIncome(Document):
    """Income entry written by finance-ai-backend (Mongoose 'user_incomes' collection).

    One document per income entry in a message.
    """

    chat_id: str
    channel: str                      # whatsapp | telegram
    amount: float
    currency: str = "INR"
    source: str = "Unknown"           # who paid / where it came from
    category: str = "other"
    earned_at_ms: int                 # when the money was earned
    date_from_message: bool = False   # False = date assumed from message time
    created_at_ms: int = Field(default_factory=_now_ms)
    operation_id: str
    entry_index: int = 0

    class Settings:
        name = "user_incomes"
