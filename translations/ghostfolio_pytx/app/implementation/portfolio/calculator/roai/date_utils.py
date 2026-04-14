"""Date utility functions — Python equivalents of date-fns."""

from __future__ import annotations

from datetime import date, datetime, timedelta

# Re-usable type alias for all public signatures.
DateLike = str | date | datetime


def parse_date(value: DateLike) -> date:
    """Coerce *value* to a :class:`date`.

    Accepts :class:`datetime`, :class:`date`, or an ISO-8601 string
    (only the first ten characters are used).
    """
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def format_date(d: DateLike, fmt: str = "%Y-%m-%d") -> str:
    """Format *d* as a string using :func:`strftime`."""
    return parse_date(d).strftime(fmt)


def difference_in_days(date_a: DateLike, date_b: DateLike) -> int:
    """Return the signed number of days between *date_a* and *date_b*."""
    return (parse_date(date_a) - parse_date(date_b)).days


def is_before(date_a: DateLike, date_b: DateLike) -> bool:
    """Return ``True`` if *date_a* is strictly before *date_b*."""
    return parse_date(date_a) < parse_date(date_b)


def is_after(date_a: DateLike, date_b: DateLike) -> bool:
    """Return ``True`` if *date_a* is strictly after *date_b*."""
    return parse_date(date_a) > parse_date(date_b)


def is_this_year(d: DateLike) -> bool:
    """Return ``True`` if *d* falls in the current calendar year."""
    return parse_date(d).year == date.today().year


def start_of_year(d: DateLike) -> date:
    """Return January 1st of the year containing *d*."""
    return date(parse_date(d).year, 1, 1)


def end_of_year(d: DateLike) -> date:
    """Return December 31st of the year containing *d*."""
    return date(parse_date(d).year, 12, 31)


def start_of_month(d: DateLike) -> date:
    """Return the first day of the month containing *d*."""
    parsed = parse_date(d)
    return date(parsed.year, parsed.month, 1)


def start_of_week(d: DateLike, week_starts_on: int = 1) -> date:
    """Return the start of the ISO week containing *d*.

    *week_starts_on* follows the ``date-fns`` convention where 1 = Monday.
    """
    parsed = parse_date(d)
    offset = (parsed.weekday() - (week_starts_on - 1)) % 7
    return parsed - timedelta(days=offset)


def sub_days(d: DateLike, n: int) -> date:
    """Return the date *n* days before *d*."""
    return parse_date(d) - timedelta(days=n)


def sub_years(d: DateLike, n: int) -> date:
    """Return the date *n* years before *d*, clamping Feb 29 to Feb 28."""
    parsed = parse_date(d)
    try:
        return parsed.replace(year=parsed.year - n)
    except ValueError:
        return parsed.replace(year=parsed.year - n, day=28)


def each_day_of_interval(start: DateLike, end: DateLike, step: int = 1) -> list[date]:
    """Return every *step*-th date from *start* to *end* (inclusive)."""
    first = parse_date(start)
    last = parse_date(end)
    delta = timedelta(days=step)
    days: list[date] = []
    current = first
    while current <= last:
        days.append(current)
        current += delta
    return days


def each_year_of_interval(start: DateLike, end: DateLike) -> list[date]:
    """Return January 1st of each year spanning *start* to *end*."""
    s_year = parse_date(start).year
    e_year = parse_date(end).year
    return [date(y, 1, 1) for y in range(s_year, e_year + 1)]


def add_milliseconds(d: DateLike, ms: int) -> date:
    """Add milliseconds to a date (used for sort tiebreaking)."""
    return parse_date(d)  # date has no time component; effectively a no-op for dates


def start_of_day(d: DateLike) -> date:
    """Return the date with time set to midnight (date-only: identity)."""
    return parse_date(d)


def end_of_day(d: DateLike) -> date:
    """Return the date with time set to end of day (date-only: identity)."""
    return parse_date(d)


def is_within_interval(d: DateLike, start: DateLike, end: DateLike) -> bool:
    """Check if date is within the interval [start, end] inclusive."""
    parsed = parse_date(d)
    return parse_date(start) <= parsed <= parse_date(end)


def min_date(dates: list[date]) -> date | None:
    """Return the earliest date, or None if empty."""
    return min(dates) if dates else None


def max_date(dates: list[date]) -> date | None:
    """Return the latest date, or None if empty."""
    return max(dates) if dates else None
