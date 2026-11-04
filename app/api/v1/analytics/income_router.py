from datetime import datetime, timezone, timedelta
from typing import List

from fastapi import APIRouter, Depends, status

from app.dependencies import get_current_user
from app.models.user import User
from app.models.user_income import UserIncome
from app.schemas.common import ResponseModel
from app.api.v1.analytics.schema import (
    CategoryBreakdownItem,
    IncomeStatisticsResponse,
    MonthlyTrendItem,
    RecentIncomeItem,
)

# IST offset: UTC+5:30
IST = timezone(timedelta(hours=5, minutes=30))

router = APIRouter(prefix="/analytics/income", tags=["Analytics - Income"])


def _chat_ids(user: User) -> List[str]:
    """Income is stored by chat_id, which is the user's phone or telegram id."""
    return [cid for cid in (user.phone, user.telegram_id) if cid]


def _ist(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000, tz=IST)


@router.get(
    "/statistics",
    status_code=status.HTTP_200_OK,
    response_model=ResponseModel[IncomeStatisticsResponse],
)
async def income_statistics(current_user: User = Depends(get_current_user)):
    """Income totals for the same windows as spending statistics (IST, by earning date)."""
    chat_ids = _chat_ids(current_user)
    empty = IncomeStatisticsResponse(
        daily_earned=0, last_7_days_earned=0, last_14_days_earned=0,
        last_month_earned=0, last_2_months_earned=0,
    )
    if not chat_ids:
        return ResponseModel(success=True, message="No linked phone or telegram to fetch data", data=empty)

    today_start = datetime.now(IST).replace(hour=0, minute=0, second=0, microsecond=0)
    current_month_start = today_start.replace(day=1)
    prev_month_start = (current_month_start - timedelta(days=1)).replace(day=1)

    today_ms = int(today_start.timestamp() * 1000)
    days_7_ms = int((today_start - timedelta(days=6)).timestamp() * 1000)
    days_14_ms = int((today_start - timedelta(days=13)).timestamp() * 1000)
    month_ms = int(current_month_start.timestamp() * 1000)
    two_months_ms = int(prev_month_start.timestamp() * 1000)

    docs = await UserIncome.find(
        {"chat_id": {"$in": chat_ids}, "earned_at_ms": {"$gte": min(two_months_ms, days_14_ms)}}
    ).to_list()

    stats = empty.model_copy()
    for doc in docs:
        ms, amount = doc.earned_at_ms, doc.amount
        if ms >= two_months_ms:
            stats.last_2_months_earned += amount
        if ms >= month_ms:
            stats.last_month_earned += amount
        if ms >= days_14_ms:
            stats.last_14_days_earned += amount
        if ms >= days_7_ms:
            stats.last_7_days_earned += amount
        if ms >= today_ms:
            stats.daily_earned += amount

    return ResponseModel(success=True, message="Income statistics retrieved successfully", data=stats)


@router.get(
    "/monthly-trend",
    status_code=status.HTTP_200_OK,
    response_model=ResponseModel[List[MonthlyTrendItem]],
)
async def income_monthly_trend(current_user: User = Depends(get_current_user)):
    """Total income per month (IST, by earning date), ascending."""
    chat_ids = _chat_ids(current_user)
    if not chat_ids:
        return ResponseModel(success=True, message="No linked phone or telegram to fetch data", data=[])

    docs = await UserIncome.find({"chat_id": {"$in": chat_ids}}).to_list()
    totals: dict[str, float] = {}
    for doc in docs:
        month = _ist(doc.earned_at_ms).strftime("%Y-%m")
        totals[month] = totals.get(month, 0) + doc.amount

    return ResponseModel(
        success=True,
        message="Income monthly trend retrieved successfully",
        data=[MonthlyTrendItem(month=m, amount=a) for m, a in sorted(totals.items())],
    )


@router.get(
    "/category-breakdown",
    status_code=status.HTTP_200_OK,
    response_model=ResponseModel[List[CategoryBreakdownItem]],
)
async def income_category_breakdown(current_user: User = Depends(get_current_user)):
    """Income per category for the last 30 days, sorted descending."""
    chat_ids = _chat_ids(current_user)
    if not chat_ids:
        return ResponseModel(success=True, message="No linked phone or telegram to fetch data", data=[])

    since_ms = int((datetime.now(timezone.utc) - timedelta(days=30)).timestamp() * 1000)
    docs = await UserIncome.find(
        {"chat_id": {"$in": chat_ids}, "earned_at_ms": {"$gte": since_ms}}
    ).to_list()

    totals: dict[str, float] = {}
    for doc in docs:
        totals[doc.category] = totals.get(doc.category, 0) + doc.amount

    return ResponseModel(
        success=True,
        message="Income category breakdown retrieved successfully",
        data=[
            CategoryBreakdownItem(name=c, amount=a)
            for c, a in sorted(totals.items(), key=lambda x: x[1], reverse=True)
        ],
    )


@router.get(
    "/recent",
    status_code=status.HTTP_200_OK,
    response_model=ResponseModel[List[RecentIncomeItem]],
)
async def recent_income(current_user: User = Depends(get_current_user)):
    """Last 100 income entries, newest earning date first."""
    chat_ids = _chat_ids(current_user)
    if not chat_ids:
        return ResponseModel(success=True, message="No linked phone or telegram to fetch data", data=[])

    docs = await UserIncome.find(
        {"chat_id": {"$in": chat_ids}}
    ).sort([("earned_at_ms", -1), ("created_at_ms", -1)]).limit(100).to_list()

    return ResponseModel(
        success=True,
        message="Recent income retrieved successfully",
        data=[
            RecentIncomeItem(
                id=f"{doc.id}",
                amount=doc.amount,
                category=doc.category,
                source=doc.source,
                date=_ist(doc.earned_at_ms).strftime("%Y-%m-%d"),
                channel=doc.channel,
                date_from_message=doc.date_from_message,
            )
            for doc in docs
        ],
    )
