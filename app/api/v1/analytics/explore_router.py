"""Period-based analytics: arbitrary date ranges, day/month/year granularity.

Everything is aggregated in MongoDB and bucketed by India time (UTC+05:30).
Expenses are dated by the message time (created_at_ms); income by earned_at_ms.
"""
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import get_current_user
from app.models.user import User
from app.models.user_data import UserData
from app.models.user_income import UserIncome
from app.schemas.common import ResponseModel
from app.api.v1.analytics.schema import (
    BreakdownItem,
    PeriodsResponse,
    TopExpenseItem,
    TrendPoint,
    WeekdayItem,
)

IST = timezone(timedelta(hours=5, minutes=30))
TZ = "+05:30"
MAX_BUCKETS = {"day": 400, "month": 600, "year": 100}
FORMATS = {"day": "%Y-%m-%d", "month": "%Y-%m", "year": "%Y"}
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

Kind = Literal["expense", "income"]
Granularity = Literal["day", "month", "year"]

router = APIRouter(prefix="/analytics", tags=["Analytics - Explore"])


# ───────────────────────── helpers ─────────────────────────

def _chat_ids(user: User) -> List[str]:
    return [cid for cid in (user.phone, user.telegram_id) if cid]


def _ist_ms(d: date) -> int:
    """Epoch ms of 00:00 IST on that date."""
    return int(datetime(d.year, d.month, d.day, tzinfo=IST).timestamp() * 1000)


def _check_range(start: date, end: date) -> None:
    if start > end:
        raise HTTPException(status_code=422, detail="start must be on or before end")


def _base_pipeline(kind: Kind, chat_ids: List[str], start: date, end: date) -> List[Dict[str, Any]]:
    """$match on user + IST date range, and add `amount` and `ts` (the dating field)."""
    field = "created_at_ms" if kind == "expense" else "earned_at_ms"
    pipeline: List[Dict[str, Any]] = [
        {"$match": {
            "chat_id": {"$in": chat_ids},
            field: {"$gte": _ist_ms(start), "$lt": _ist_ms(end + timedelta(days=1))},
        }},
        {"$addFields": {"ts": f"${field}"}},
    ]
    if kind == "expense":
        # Item prices are stored as strings by the backend; unparseable → 0, discounts are negative.
        pipeline.append({"$addFields": {"amount": {"$sum": {"$map": {
            "input": {"$ifNull": ["$items", []]},
            "as": "i",
            "in": {"$convert": {"input": "$$i.price", "to": "double", "onError": 0, "onNull": 0}},
        }}}}})
    return pipeline


def _model(kind: Kind):
    return UserData if kind == "expense" else UserIncome


def _bucket_keys(start: date, end: date, granularity: Granularity) -> List[str]:
    keys: List[str] = []
    if granularity == "day":
        d = start
        while d <= end:
            keys.append(d.isoformat())
            d += timedelta(days=1)
    elif granularity == "month":
        y, m = start.year, start.month
        while (y, m) <= (end.year, end.month):
            keys.append(f"{y:04d}-{m:02d}")
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    else:
        keys = [f"{y:04d}" for y in range(start.year, end.year + 1)]
    return keys


# ───────────────────────── endpoints ─────────────────────────

@router.get("/periods", status_code=status.HTTP_200_OK, response_model=ResponseModel[PeriodsResponse])
async def periods(current_user: User = Depends(get_current_user)):
    """Months and years (IST) that have any expense or income, newest first."""
    chat_ids = _chat_ids(current_user)
    if not chat_ids:
        return ResponseModel(success=True, message="No linked phone or telegram", data=PeriodsResponse())

    months: set[str] = set()
    for model, field in ((UserData, "created_at_ms"), (UserIncome, "earned_at_ms")):
        rows = await model.aggregate([
            {"$match": {"chat_id": {"$in": chat_ids}}},
            {"$group": {"_id": {"$dateToString": {"format": "%Y-%m", "date": {"$toDate": f"${field}"}, "timezone": TZ}}}},
        ]).to_list()
        months.update(r["_id"] for r in rows if r.get("_id"))

    ordered = sorted(months, reverse=True)
    years = sorted({int(m[:4]) for m in ordered}, reverse=True)
    return ResponseModel(success=True, message="Periods retrieved successfully",
                         data=PeriodsResponse(months=ordered, years=years))


@router.get("/trend", status_code=status.HTTP_200_OK, response_model=ResponseModel[List[TrendPoint]])
async def trend(
    kind: Kind = Query(...),
    start: date = Query(..., description="YYYY-MM-DD, inclusive (IST)"),
    end: date = Query(..., description="YYYY-MM-DD, inclusive (IST)"),
    granularity: Granularity = Query("day"),
    current_user: User = Depends(get_current_user),
):
    """Totals per day/month/year in [start, end], zero-filled, ascending."""
    _check_range(start, end)
    keys = _bucket_keys(start, end, granularity)
    if len(keys) > MAX_BUCKETS[granularity]:
        raise HTTPException(status_code=422,
                            detail=f"Too many {granularity} buckets ({len(keys)}); use a coarser granularity")

    totals: Dict[str, float] = {}
    chat_ids = _chat_ids(current_user)
    if chat_ids:
        pipeline = _base_pipeline(kind, chat_ids, start, end) + [
            {"$group": {
                "_id": {"$dateToString": {"format": FORMATS[granularity], "date": {"$toDate": "$ts"}, "timezone": TZ}},
                "amount": {"$sum": "$amount"},
            }},
        ]
        rows = await _model(kind).aggregate(pipeline).to_list()
        totals = {r["_id"]: float(r["amount"]) for r in rows}

    return ResponseModel(success=True, message="Trend retrieved successfully",
                         data=[TrendPoint(period=k, amount=totals.get(k, 0.0)) for k in keys])


@router.get("/breakdown", status_code=status.HTTP_200_OK, response_model=ResponseModel[List[BreakdownItem]])
async def breakdown(
    kind: Kind = Query(...),
    start: date = Query(...),
    end: date = Query(...),
    current_user: User = Depends(get_current_user),
):
    """Totals per category in [start, end], descending.

    An expense message with several categories has its total split evenly between them,
    so the categories add up to the real amount spent.
    """
    _check_range(start, end)
    chat_ids = _chat_ids(current_user)
    if not chat_ids:
        return ResponseModel(success=True, message="No linked phone or telegram", data=[])

    pipeline = _base_pipeline(kind, chat_ids, start, end)
    if kind == "expense":
        pipeline += [
            {"$addFields": {"cats": {"$cond": [
                {"$gt": [{"$size": {"$ifNull": ["$categories", []]}}, 0]}, "$categories", ["other"]]}}},
            {"$addFields": {"share": {"$divide": ["$amount", {"$size": "$cats"}]}}},
            {"$unwind": "$cats"},
            {"$group": {"_id": "$cats", "amount": {"$sum": "$share"}}},
        ]
    else:
        pipeline += [{"$group": {"_id": {"$ifNull": ["$category", "other"]}, "amount": {"$sum": "$amount"}}}]
    pipeline.append({"$sort": {"amount": -1}})

    rows = await _model(kind).aggregate(pipeline).to_list()
    return ResponseModel(success=True, message="Breakdown retrieved successfully",
                         data=[BreakdownItem(name=r["_id"], amount=round(float(r["amount"]), 2)) for r in rows])


@router.get("/top-expenses", status_code=status.HTTP_200_OK, response_model=ResponseModel[List[TopExpenseItem]])
async def top_expenses(
    start: date = Query(...),
    end: date = Query(...),
    limit: int = Query(5, ge=1, le=50),
    current_user: User = Depends(get_current_user),
):
    """The largest single expense items in [start, end]."""
    _check_range(start, end)
    chat_ids = _chat_ids(current_user)
    if not chat_ids:
        return ResponseModel(success=True, message="No linked phone or telegram", data=[])

    pipeline = [
        {"$match": {
            "chat_id": {"$in": chat_ids},
            "created_at_ms": {"$gte": _ist_ms(start), "$lt": _ist_ms(end + timedelta(days=1))},
        }},
        {"$unwind": "$items"},
        {"$addFields": {"price": {"$convert": {"input": "$items.price", "to": "double", "onError": 0, "onNull": 0}}}},
        {"$match": {"price": {"$gt": 0}}},
        {"$sort": {"price": -1, "created_at_ms": -1}},
        {"$limit": limit},
        {"$project": {
            "name": "$items.name",
            "price": 1,
            "category": {"$ifNull": [{"$arrayElemAt": ["$categories", 0]}, "other"]},
            "date": {"$dateToString": {"format": "%Y-%m-%d", "date": {"$toDate": "$created_at_ms"}, "timezone": TZ}},
            "source": 1,
        }},
    ]
    rows = await UserData.aggregate(pipeline).to_list()
    return ResponseModel(success=True, message="Top expenses retrieved successfully", data=[
        TopExpenseItem(id=str(r["_id"]), name=r.get("name") or "Item", amount=float(r["price"]),
                       category=r["category"], date=r["date"], source=r.get("source") or "whatsapp")
        for r in rows
    ])


@router.get("/weekday-pattern", status_code=status.HTTP_200_OK, response_model=ResponseModel[List[WeekdayItem]])
async def weekday_pattern(
    kind: Kind = Query("expense"),
    start: date = Query(...),
    end: date = Query(...),
    current_user: User = Depends(get_current_user),
):
    """Total and average per weekday (Mon..Sun) in [start, end].

    The average divides by how many times that weekday occurs in the range,
    so days with no spending count as zero.
    """
    _check_range(start, end)
    occurrences = [0] * 7
    d = start
    while d <= end:
        occurrences[d.weekday()] += 1
        d += timedelta(days=1)

    totals = [0.0] * 7
    chat_ids = _chat_ids(current_user)
    if chat_ids:
        pipeline = _base_pipeline(kind, chat_ids, start, end) + [
            # $isoDayOfWeek: 1 = Monday … 7 = Sunday
            {"$group": {"_id": {"$isoDayOfWeek": {"date": {"$toDate": "$ts"}, "timezone": TZ}},
                        "amount": {"$sum": "$amount"}}},
        ]
        for r in await _model(kind).aggregate(pipeline).to_list():
            totals[int(r["_id"]) - 1] = float(r["amount"])

    return ResponseModel(success=True, message="Weekday pattern retrieved successfully", data=[
        WeekdayItem(day=WEEKDAYS[i], total=round(totals[i], 2),
                    average=round(totals[i] / occurrences[i], 2) if occurrences[i] else 0.0)
        for i in range(7)
    ])
