"""Runtime helpers for translated TypeScript code.

Provides utility functions that bridge common TypeScript patterns
to their Python equivalents. Used by the translated calculator.
"""
from __future__ import annotations

import copy
import math
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Any


DATE_FORMAT = "%Y-%m-%d"


_ACTIVITY_FACTORS = {"BUY": 1, "SELL": -1}


def get_factor(activity_type: str) -> int:
    """Map an activity type to its quantity sign factor."""
    return _ACTIVITY_FACTORS.get(activity_type, 0)


def parse_date(val) -> datetime:
    """Parse various date representations to datetime."""
    if isinstance(val, datetime):
        return val
    if isinstance(val, date):
        return datetime(val.year, val.month, val.day)
    if isinstance(val, str):
        try:
            return datetime.strptime(val[:10], DATE_FORMAT)
        except (ValueError, TypeError):
            return datetime.now()
    return datetime.now()


def format_date(dt, fmt=None) -> str:
    """Format a date to string (default: YYYY-MM-DD)."""
    if isinstance(dt, str):
        return dt[:10]
    if isinstance(dt, (datetime, date)):
        return dt.strftime(DATE_FORMAT)
    return str(dt)[:10]


def difference_in_days(a, b) -> int:
    """Difference in days between two dates."""
    da = parse_date(a)
    db = parse_date(b)
    return (da - db).days


def is_before(a, b) -> bool:
    """Check if date a is before date b."""
    return parse_date(a) < parse_date(b)


def is_after(a, b) -> bool:
    """Check if date a is after date b."""
    return parse_date(a) > parse_date(b)


def add_milliseconds(dt, ms) -> datetime:
    """Add milliseconds to a datetime."""
    return parse_date(dt) + timedelta(milliseconds=ms)


def sub_days(dt, days) -> datetime:
    """Subtract days from a datetime."""
    return parse_date(dt) - timedelta(days=days)


def start_of_day(dt) -> datetime:
    """Start of day."""
    d = parse_date(dt)
    return datetime(d.year, d.month, d.day)


def end_of_day(dt) -> datetime:
    """End of day."""
    d = parse_date(dt)
    return datetime(d.year, d.month, d.day, 23, 59, 59)


def start_of_year(dt) -> datetime:
    """Start of year."""
    d = parse_date(dt)
    return datetime(d.year, 1, 1)


def end_of_year(dt) -> datetime:
    """End of year."""
    d = parse_date(dt)
    return datetime(d.year, 12, 31, 23, 59, 59)


def each_day_of_interval(interval, step=None) -> list[datetime]:
    """Generate dates in an interval."""
    if isinstance(interval, dict):
        s = parse_date(interval.get("start"))
        e = parse_date(interval.get("end"))
    else:
        return []
    step_size = step.get("step", 1) if isinstance(step, dict) else (step or 1)
    result = []
    current = s
    while current <= e:
        result.append(current)
        current += timedelta(days=step_size)
    return result


def each_year_of_interval(interval) -> list[datetime]:
    """Generate start of each year in an interval."""
    if isinstance(interval, dict):
        s = parse_date(interval.get("start"))
        e = parse_date(interval.get("end"))
    else:
        return []
    result = []
    year = s.year
    while year <= e.year:
        result.append(datetime(year, 1, 1))
        year += 1
    return result


def is_within_interval(dt, interval) -> bool:
    """Check if date is within interval."""
    d = parse_date(dt)
    s = parse_date(interval.get("start"))
    e = parse_date(interval.get("end"))
    return s <= d <= e


def is_this_year(dt) -> bool:
    """Check if date is in the current year."""
    return parse_date(dt).year == datetime.now().year


def reset_hours(dt) -> datetime:
    """Reset time to midnight."""
    d = parse_date(dt)
    return datetime(d.year, d.month, d.day)


def min_date(dates) -> datetime:
    """Get minimum date from a list."""
    parsed = [parse_date(d) for d in dates if d]
    return min(parsed) if parsed else datetime.now()


def sort_by(arr, key_fn):
    """Sort array by key function (lodash sortBy)."""
    if callable(key_fn):
        return sorted(arr, key=key_fn)
    if isinstance(key_fn, str):
        return sorted(arr, key=lambda x: x.get(key_fn, "") if isinstance(x, dict) else getattr(x, key_fn, ""))
    return sorted(arr)


def uniq_by(arr, key_fn):
    """Unique elements by key (lodash uniqBy)."""
    seen = {}
    result = []
    for item in arr:
        if callable(key_fn):
            k = key_fn(item)
        elif isinstance(key_fn, str):
            k = item.get(key_fn, "") if isinstance(item, dict) else getattr(item, key_fn, "")
        else:
            k = item
        if k not in seen:
            seen[k] = True
            result.append(item)
    return result


def is_number(val) -> bool:
    """Check if value is a number."""
    return isinstance(val, (int, float, Decimal))


def get_interval_from_date_range(date_range: str, ref_date=None):
    """Get start/end dates for a date range string."""
    now = datetime.now()
    today = datetime(now.year, now.month, now.day)

    if date_range == "1d":
        return {"startDate": today - timedelta(days=1), "endDate": today}
    elif date_range == "wtd":
        weekday = today.weekday()
        s = today - timedelta(days=weekday)
        return {"startDate": s, "endDate": today}
    elif date_range == "mtd":
        s = datetime(today.year, today.month, 1)
        return {"startDate": s, "endDate": today}
    elif date_range == "ytd":
        s = datetime(today.year, 1, 1)
        return {"startDate": s, "endDate": today}
    elif date_range == "1y":
        return {"startDate": today - timedelta(days=365), "endDate": today}
    elif date_range == "5y":
        return {"startDate": today - timedelta(days=5 * 365), "endDate": today}
    elif date_range == "max":
        s = ref_date if ref_date else today - timedelta(days=50 * 365)
        return {"startDate": parse_date(s), "endDate": today}
    else:
        try:
            year = int(date_range)
            return {
                "startDate": datetime(year, 1, 1),
                "endDate": datetime(year, 12, 31),
            }
        except (ValueError, TypeError):
            return {"startDate": today - timedelta(days=365), "endDate": today}
