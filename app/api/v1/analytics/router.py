from fastapi import status, Depends, Query
from fastapi import APIRouter
from typing import Optional, List
from datetime import datetime, timezone, timedelta

from app.dependencies import get_current_user
from app.models.user import User
from app.models.user_data import UserData
from app.schemas.common import ResponseModel
from app.api.v1.analytics.schema import (
    StatisticsResponse,
    RecentExpenseItem,
    MonthlyTrendItem,
    CategoryBreakdownItem,
    DailyTrendItem,
)

# IST offset: UTC+5:30
IST = timezone(timedelta(hours=5, minutes=30))

router = APIRouter(prefix='/analytics', tags=["Analytics"])


@router.get(
    "/statistics",
    status_code=status.HTTP_200_OK,
    response_model=ResponseModel[StatisticsResponse],
)
async def statistics(current_user: User = Depends(get_current_user)):
    """Get spending statistics across multiple time windows (IST-based)."""
    chat_ids = []
    if current_user.phone:
        chat_ids.append(current_user.phone)
    if current_user.telegram_id:
        chat_ids.append(current_user.telegram_id)

    if not chat_ids:
        return ResponseModel(
            success=True,
            message="No linked phone or telegram to fetch data",
            data=StatisticsResponse(
                daily_spend=0,
                last_7_days_spend=0,
                last_14_days_spend=0,
                last_month_spend=0,
                last_2_months_spend=0,
            ),
        )

    # Compute IST boundaries
    now_ist = datetime.now(IST)
    today_start = now_ist.replace(hour=0, minute=0, second=0, microsecond=0)

    # Current month start
    current_month_start = today_start.replace(day=1)
    # Previous month start
    prev_month = (current_month_start - timedelta(days=1)).replace(day=1)

    # Convert to ms timestamps
    today_start_ms = int(today_start.timestamp() * 1000)
    days_7_ago_ms = int((today_start - timedelta(days=6)).timestamp() * 1000)
    days_14_ago_ms = int((today_start - timedelta(days=13)).timestamp() * 1000)
    current_month_ms = int(current_month_start.timestamp() * 1000)
    two_months_ms = int(prev_month.timestamp() * 1000)

    # Fetch all docs from the widest window (2 months)
    docs = await UserData.find(
        {"chat_id": {"$in": chat_ids}, "created_at_ms": {"$gte": two_months_ms}}
    ).to_list()

    daily_spend = 0
    last_7 = 0
    last_14 = 0
    last_month = 0
    last_2_months = 0

    for doc in docs:
        doc_total = 0
        for item in doc.items:
            doc_total += item.price

        ms = doc.created_at_ms
        # last 2 months (current + previous month)
        last_2_months += doc_total
        # last month (current month)
        if ms >= current_month_ms:
            last_month += doc_total
        # last 14 days
        if ms >= days_14_ago_ms:
            last_14 += doc_total
        # last 7 days
        if ms >= days_7_ago_ms:
            last_7 += doc_total
        # today
        if ms >= today_start_ms:
            daily_spend += doc_total

    return ResponseModel(
        success=True,
        message="Statistics retrieved successfully",
        data=StatisticsResponse(
            daily_spend=daily_spend,
            last_7_days_spend=last_7,
            last_14_days_spend=last_14,
            last_month_spend=last_month,
            last_2_months_spend=last_2_months,
        ),
    )


@router.get(
    "/daily-trend",
    status_code=status.HTTP_200_OK,
    response_model=ResponseModel[List[DailyTrendItem]],
)
async def daily_trend(current_user: User = Depends(get_current_user)):
    """Get daily spending trend for the last 1 month.

    Pulls UserData docs where chat_id matches the user's phone or telegram_id,
    converts created_at_ms to IST date, aggregates total amount per day.
    """
    # Build list of possible chat_ids for this user
    chat_ids = []
    if current_user.phone:
        chat_ids.append(current_user.phone)
    if current_user.telegram_id:
        chat_ids.append(current_user.telegram_id)
    if not chat_ids:
        return ResponseModel(
            success=True,
            message="No linked phone or telegram to fetch data",
            data=[],
        )

    # Last 1 month boundary in ms
    now = datetime.now(timezone.utc)
    one_month_ago_ms = int((now - timedelta(days=30)).timestamp() * 1000)

    # Query user_data for last 30 days matching any of the user's chat_ids
    docs = await UserData.find(
        {"chat_id": {"$in": chat_ids}, "created_at_ms": {"$gte": one_month_ago_ms}}
    ).to_list()

    # Aggregate: convert ms -> IST date string, sum item prices per day
    daily_totals: dict[str, int] = {}
    for doc in docs:
        ist_dt = datetime.fromtimestamp(doc.created_at_ms / 1000, tz=IST)
        date_str = ist_dt.strftime("%Y-%m-%d")
        day_total = 0
        for item in doc.items:
            day_total += item.price
        daily_totals[date_str] = daily_totals.get(date_str, 0) + day_total

    # Sort by date ascending
    result = [
        DailyTrendItem(date=date, amount=amount)
        for date, amount in sorted(daily_totals.items())
    ]

    return ResponseModel(
        success=True,
        message="Daily trend retrieved successfully",
        data=result,
    )


@router.get(
    "/monthly-trend",
    status_code=status.HTTP_200_OK,
    response_model=ResponseModel[List[MonthlyTrendItem]],
)
async def monthly_trend(current_user: User = Depends(get_current_user)):
    """Get monthly spending trend. Aggregates all user data by month."""
    chat_ids = []
    if current_user.phone:
        chat_ids.append(current_user.phone)
    if current_user.telegram_id:
        chat_ids.append(current_user.telegram_id)

    if not chat_ids:
        return ResponseModel(
            success=True,
            message="No linked phone or telegram to fetch data",
            data=[],
        )

    docs = await UserData.find(
        {"chat_id": {"$in": chat_ids}}
    ).to_list()

    # Aggregate: convert ms -> IST month string, sum item prices per month
    monthly_totals: dict[str, int] = {}
    for doc in docs:
        ist_dt = datetime.fromtimestamp(doc.created_at_ms / 1000, tz=IST)
        month_str = ist_dt.strftime("%Y-%m")
        doc_total = 0
        for item in doc.items:
            doc_total += item.price
        monthly_totals[month_str] = monthly_totals.get(
            month_str, 0) + doc_total

    # Sort by month ascending
    result = [
        MonthlyTrendItem(month=month, amount=amount)
        for month, amount in sorted(monthly_totals.items())
    ]

    return ResponseModel(
        success=True,
        message="Monthly trend retrieved successfully",
        data=result,
    )


@router.get(
    "/category-breakdown",
    status_code=status.HTTP_200_OK,
    response_model=ResponseModel[List[CategoryBreakdownItem]],
)
async def category_breakdown(current_user: User = Depends(get_current_user)):
    """Get spending breakdown by category for the last 1 month.

    Each UserData doc has a categories list and items list.
    Sums total item prices per category, sorted descending by amount.
    """
    chat_ids = []
    if current_user.phone:
        chat_ids.append(current_user.phone)
    if current_user.telegram_id:
        chat_ids.append(current_user.telegram_id)

    if not chat_ids:
        return ResponseModel(
            success=True,
            message="No linked phone or telegram to fetch data",
            data=[],
        )

    now = datetime.now(timezone.utc)
    one_month_ago_ms = int((now - timedelta(days=30)).timestamp() * 1000)

    docs = await UserData.find(
        {"chat_id": {"$in": chat_ids}, "created_at_ms": {"$gte": one_month_ago_ms}}
    ).to_list()

    # Aggregate: sum item prices per category
    category_totals: dict[str, int] = {}
    for doc in docs:
        doc_total = 0
        for item in doc.items:
            doc_total += item.price
        # Distribute the doc total across its categories
        for cat in doc.categories:
            category_totals[cat] = category_totals.get(cat, 0) + doc_total

    # Sort descending by amount
    result = [
        CategoryBreakdownItem(name=cat, amount=amount)
        for cat, amount in sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
    ]

    return ResponseModel(
        success=True,
        message="Category breakdown retrieved successfully",
        data=result,
    )


@router.get(
    "/recent-expenses",
    status_code=status.HTTP_200_OK,
    response_model=ResponseModel[List[RecentExpenseItem]],
)
async def recent_expenses(current_user: User = Depends(get_current_user)):
    """Get the last 100 transactions for the current user."""
    chat_ids = []
    if current_user.phone:
        chat_ids.append(current_user.phone)
    if current_user.telegram_id:
        chat_ids.append(current_user.telegram_id)

    if not chat_ids:
        return ResponseModel(
            success=True,
            message="No linked phone or telegram to fetch data",
            data=[],
        )

    # Fetch last 100 docs sorted by created_at_ms descending
    docs = await UserData.find(
        {"chat_id": {"$in": chat_ids}}
    ).sort(-UserData.created_at_ms).limit(100).to_list()

    # Flatten: each item in each doc becomes a transaction entry
    result: List[RecentExpenseItem] = []
    for doc in docs:
        ist_dt = datetime.fromtimestamp(doc.created_at_ms / 1000, tz=IST)
        date_str = ist_dt.strftime("%Y-%m-%d")
        category = doc.categories[0] if doc.categories else "Uncategorized"
        for item in doc.items:
            result.append(RecentExpenseItem(
                id=str(doc.id),
                amount=item.price,
                category=category,
                description=item.name,
                date=date_str,
                source=doc.source,
            ))

    # Trim to 100 in case multiple items per doc pushed us over
    return ResponseModel(
        success=True,
        message="Recent expenses retrieved successfully",
        data=result[:100],
    )
