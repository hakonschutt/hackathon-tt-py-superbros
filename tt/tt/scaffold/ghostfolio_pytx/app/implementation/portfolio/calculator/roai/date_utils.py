"""Date utility functions — Python equivalents of date-fns."""
from __future__ import annotations

from datetime import date, datetime, timedelta


def parse_date(date_str: str | date | datetime) -> date:
    """Parse an ISO date string to a date object."""
    if isinstance(date_str, datetime):
        return date_str.date()
    if isinstance(date_str, date):
        return date_str
    return date.fromisoformat(str(date_str)[:10])


def format_date(d: date | datetime, fmt: str = "%Y-%m-%d") -> str:
    """Format a date as a string."""
    if isinstance(d, datetime):
        d = d.date()
    return d.strftime(fmt)


def difference_in_days(date_a: date | str, date_b: date | str) -> int:
    """Return number of days between date_a and date_b (a - b)."""
    return (parse_date(date_a) - parse_date(date_b)).days


def is_before(date_a: date | str, date_b: date | str) -> bool:
    """Check if date_a is before date_b."""
    return parse_date(date_a) < parse_date(date_b)


def is_after(date_a: date | str, date_b: date | str) -> bool:
    """Check if date_a is after date_b."""
    return parse_date(date_a) > parse_date(date_b)


def is_this_year(d: date | str) -> bool:
    """Check if the date is in the current year."""
    return parse_date(d).year == date.today().year


def start_of_year(d: date | str) -> date:
    """Return January 1st of the given date's year."""
    return date(parse_date(d).year, 1, 1)


def end_of_year(d: date | str) -> date:
    """Return December 31st of the given date's year."""
    return date(parse_date(d).year, 12, 31)


def start_of_month(d: date | str) -> date:
    """Return the 1st of the given date's month."""
    parsed = parse_date(d)
    return date(parsed.year, parsed.month, 1)


def start_of_week(d: date | str, week_starts_on: int = 1) -> date:
    """Return the start of the week (default Monday=1)."""
    parsed = parse_date(d)
    days_since_start = (parsed.weekday() - (week_starts_on - 1)) % 7
    return parsed - timedelta(days=days_since_start)


def sub_days(d: date | str, n: int) -> date:
    """Subtract n days from a date."""
    return parse_date(d) - timedelta(days=n)


def sub_years(d: date | str, n: int) -> date:
    """Subtract n years from a date."""
    parsed = parse_date(d)
    try:
        return parsed.replace(year=parsed.year - n)
    except ValueError:
        return parsed.replace(year=parsed.year - n, day=28)


def each_day_of_interval(
    start: date | str, end: date | str, step: int = 1
) -> list[date]:
    """Generate dates from start to end (inclusive) with given step."""
    s = parse_date(start)
    e = parse_date(end)
    result: list[date] = []
    current = s
    while current <= e:
        result.append(current)
        current += timedelta(days=step)
    return result


def each_year_of_interval(start: date | str, end: date | str) -> list[date]:
    """Generate Jan 1st of each year from start's year to end's year."""
    s = parse_date(start)
    e = parse_date(end)
    return [date(y, 1, 1) for y in range(s.year, e.year + 1)]
