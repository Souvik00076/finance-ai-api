from pydantic import BaseModel
from typing import Optional, List


class CategoryBreakdown(BaseModel):
    """Spending breakdown by category."""
    category: str
    amount: float
    percentage: float
    transaction_count: int


class SpendingSummaryResponse(BaseModel):
    """Summary of spending over a period."""
    total_spent: float
    period: str  # e.g. "monthly", "weekly"
    start_date: str
    end_date: str
    categories: List[CategoryBreakdown] = []
    average_daily_spending: float = 0.0


class TrendDataPoint(BaseModel):
    """A single data point in a spending trend."""
    date: str
    amount: float


class SpendingTrendResponse(BaseModel):
    """Spending trend over time."""
    period: str
    data_points: List[TrendDataPoint] = []
    total: float = 0.0


class RecentExpenseItem(BaseModel):
    """Single transaction entry."""
    id: str
    amount: float
    category: str
    description: str
    date: str
    source: str


class StatisticsResponse(BaseModel):
    """Spending statistics across various time windows."""
    daily_spend: float
    last_7_days_spend: float
    last_14_days_spend: float
    last_month_spend: float
    last_2_months_spend: float
    all_time_spend: float = 0.0     # aggregated from user_datas


class MonthlyTrendItem(BaseModel):
    """Single month's total spending."""
    month: str
    amount: float


class CategoryBreakdownItem(BaseModel):
    """Single category's total spending."""
    name: str
    amount: float


class DailyTrendItem(BaseModel):
    """Single day's total spending."""
    date: str
    amount: float


# ───────────── Income ─────────────

class IncomeStatisticsResponse(BaseModel):
    """Income totals across various time windows (IST, by earning date)."""
    daily_earned: float
    last_7_days_earned: float
    last_14_days_earned: float
    last_month_earned: float       # current calendar month
    last_2_months_earned: float    # current + previous calendar month
    all_time_earned: float = 0.0   # aggregated from user_incomes


class RecentIncomeItem(BaseModel):
    """Single income entry."""
    id: str
    amount: float
    category: str
    source: str                    # who paid, e.g. "Acme Corp"
    date: str                      # earning date, YYYY-MM-DD (IST)
    channel: str                   # whatsapp | telegram
    date_from_message: bool        # False = date assumed from message time
