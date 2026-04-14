"""Helper functions for the translated calculator."""
from __future__ import annotations

from datetime import date, timedelta

from .date_utils import parse_date, start_of_month, start_of_week, sub_years


def get_factor(activity_type: str) -> int:
    """Return the sign factor for an activity type.

    Equivalent of portfolio.helper.ts getFactor().
    Returns 1 for BUY, -1 for SELL, 0 otherwise.
    """
    if activity_type == "BUY":
        return 1
    if activity_type == "SELL":
        return -1
    return 0


def get_interval_from_date_range(
    date_range: str, portfolio_start: date | None = None
) -> dict:
    """Convert a date range string to start/end dates.

    Equivalent of calculation-helper.ts getIntervalFromDateRange().
    """
    today = date.today()

    if date_range == "1d":
        return {"startDate": today - timedelta(days=1), "endDate": today}
    if date_range == "1y":
        return {"startDate": sub_years(today, 1), "endDate": today}
    if date_range == "5y":
        return {"startDate": sub_years(today, 5), "endDate": today}
    if date_range == "ytd":
        return {"startDate": date(today.year, 1, 1), "endDate": today}
    if date_range == "mtd":
        return {"startDate": start_of_month(today), "endDate": today}
    if date_range == "wtd":
        return {"startDate": start_of_week(today), "endDate": today}
    if date_range == "max":
        start = portfolio_start if portfolio_start else today
        return {"startDate": start, "endDate": today}

    # Year string like "2021"
    if date_range.isdigit() and len(date_range) == 4:
        year = int(date_range)
        year_start = date(year, 1, 1)
        actual_start = year_start
        if portfolio_start and portfolio_start > year_start:
            actual_start = portfolio_start
        return {"startDate": actual_start, "endDate": date(year, 12, 31)}

    return {"startDate": today, "endDate": today}
