"""All-time totals aggregated directly from the data collections.

These deliberately do not use users.total_spent / users.total_earned, which are
running counters and can drift from the underlying data.
"""
from typing import List

from app.models.user_data import UserData
from app.models.user_income import UserIncome


async def all_time_spend(chat_ids: List[str]) -> float:
    """Sum of every expense item price for these chat_ids.

    Prices are stored as strings by the backend (Mongoose schema), so convert in the
    pipeline; anything unparseable counts as 0. Discounts are negative prices.
    """
    if not chat_ids:
        return 0.0
    pipeline = [
        {"$match": {"chat_id": {"$in": chat_ids}}},
        {"$unwind": "$items"},
        {
            "$group": {
                "_id": None,
                "total": {
                    "$sum": {
                        "$convert": {"input": "$items.price", "to": "double", "onError": 0, "onNull": 0}
                    }
                },
            }
        },
    ]
    result = await UserData.aggregate(pipeline).to_list()
    return float(result[0]["total"]) if result else 0.0


async def all_time_earned(chat_ids: List[str]) -> float:
    """Sum of every income entry amount for these chat_ids."""
    if not chat_ids:
        return 0.0
    pipeline = [
        {"$match": {"chat_id": {"$in": chat_ids}}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
    ]
    result = await UserIncome.aggregate(pipeline).to_list()
    return float(result[0]["total"]) if result else 0.0
