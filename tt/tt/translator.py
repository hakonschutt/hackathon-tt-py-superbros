"""Tree-sitter based TypeScript-to-Python translation pipeline.

Orchestrates: parse TS → walk AST → transform nodes → emit Python.
This is the core of the tt translation tool.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from tt.parser import parse_file, parse_source, get_node_text
from tt.node_visitor import NodeVisitor
from tt.emitter import build_python_file

log = logging.getLogger(__name__)

# Standard imports that the translated calculator needs
CALCULATOR_IMPORTS = [
    "import copy",
    "import math",
    "from datetime import datetime, date, timedelta",
    "from decimal import Decimal, ROUND_HALF_UP, InvalidOperation",
    "from typing import Any",
    "",
    "from app.wrapper.portfolio.calculator.portfolio_calculator import PortfolioCalculator",
]

# Runtime helpers that every translated file gets
RUNTIME_HELPERS = '''
# ── Runtime helpers (generic TS→Python support) ──────────────────

DATE_FORMAT = "%Y-%m-%d"


def _get_factor(activity_type: str) -> int:
    """Translate activity type to quantity factor."""
    if activity_type == "BUY":
        return 1
    elif activity_type == "SELL":
        return -1
    return 0


def _parse_date(val) -> datetime:
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


def _format_date(dt, fmt=None) -> str:
    """Format a date to string (default: YYYY-MM-DD)."""
    if isinstance(dt, str):
        return dt[:10]
    if isinstance(dt, (datetime, date)):
        return dt.strftime(DATE_FORMAT)
    return str(dt)[:10]


def _difference_in_days(a, b) -> int:
    """Difference in days between two dates."""
    da = _parse_date(a)
    db = _parse_date(b)
    return (da - db).days


def _is_before(a, b) -> bool:
    """Check if date a is before date b."""
    return _parse_date(a) < _parse_date(b)


def _is_after(a, b) -> bool:
    """Check if date a is after date b."""
    return _parse_date(a) > _parse_date(b)


def _add_milliseconds(dt, ms) -> datetime:
    """Add milliseconds to a datetime."""
    return _parse_date(dt) + timedelta(milliseconds=ms)


def _sub_days(dt, days) -> datetime:
    """Subtract days from a datetime."""
    return _parse_date(dt) - timedelta(days=days)


def _start_of_day(dt) -> datetime:
    """Start of day."""
    d = _parse_date(dt)
    return datetime(d.year, d.month, d.day)


def _end_of_day(dt) -> datetime:
    """End of day."""
    d = _parse_date(dt)
    return datetime(d.year, d.month, d.day, 23, 59, 59)


def _start_of_year(dt) -> datetime:
    """Start of year."""
    d = _parse_date(dt)
    return datetime(d.year, 1, 1)


def _end_of_year(dt) -> datetime:
    """End of year."""
    d = _parse_date(dt)
    return datetime(d.year, 12, 31, 23, 59, 59)


def _each_day_of_interval(interval, step=None) -> list[datetime]:
    """Generate dates in an interval."""
    if isinstance(interval, dict):
        start = _parse_date(interval.get("start"))
        end = _parse_date(interval.get("end"))
    else:
        return []
    s = step.get("step", 1) if isinstance(step, dict) else (step or 1)
    result = []
    current = start
    while current <= end:
        result.append(current)
        current += timedelta(days=s)
    return result


def _each_year_of_interval(interval) -> list[datetime]:
    """Generate start of each year in an interval."""
    if isinstance(interval, dict):
        start = _parse_date(interval.get("start"))
        end = _parse_date(interval.get("end"))
    else:
        return []
    result = []
    year = start.year
    while year <= end.year:
        result.append(datetime(year, 1, 1))
        year += 1
    return result


def _is_within_interval(dt, interval) -> bool:
    """Check if date is within interval."""
    d = _parse_date(dt)
    start = _parse_date(interval.get("start"))
    end = _parse_date(interval.get("end"))
    return start <= d <= end


def _is_this_year(dt) -> bool:
    """Check if date is in the current year."""
    return _parse_date(dt).year == datetime.now().year


def _reset_hours(dt) -> datetime:
    """Reset time to midnight."""
    d = _parse_date(dt)
    return datetime(d.year, d.month, d.day)


def _min_date(dates) -> datetime:
    """Get minimum date from a list."""
    parsed = [_parse_date(d) for d in dates if d]
    return min(parsed) if parsed else datetime.now()


def _sort_by(arr, key_fn):
    """Sort array by key function (lodash sortBy)."""
    if callable(key_fn):
        return sorted(arr, key=key_fn)
    if isinstance(key_fn, str):
        return sorted(arr, key=lambda x: x.get(key_fn, "") if isinstance(x, dict) else getattr(x, key_fn, ""))
    return sorted(arr)


def _uniq_by(arr, key_fn):
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


def _is_number(val) -> bool:
    """Check if value is a number."""
    return isinstance(val, (int, float, Decimal))


def _get_interval_from_date_range(date_range: str, ref_date=None):
    """Get start/end dates for a date range string."""
    now = datetime.now()
    today = datetime(now.year, now.month, now.day)

    if date_range == "1d":
        return {"startDate": today - timedelta(days=1), "endDate": today}
    elif date_range == "wtd":
        weekday = today.weekday()
        start = today - timedelta(days=weekday)
        return {"startDate": start, "endDate": today}
    elif date_range == "mtd":
        start = datetime(today.year, today.month, 1)
        return {"startDate": start, "endDate": today}
    elif date_range == "ytd":
        start = datetime(today.year, 1, 1)
        return {"startDate": start, "endDate": today}
    elif date_range == "1y":
        return {"startDate": today - timedelta(days=365), "endDate": today}
    elif date_range == "5y":
        return {"startDate": today - timedelta(days=5 * 365), "endDate": today}
    elif date_range == "max":
        start = ref_date if ref_date else today - timedelta(days=50 * 365)
        return {"startDate": _parse_date(start), "endDate": today}
    else:
        # Year range like "2023"
        try:
            year = int(date_range)
            return {
                "startDate": datetime(year, 1, 1),
                "endDate": datetime(year, 12, 31),
            }
        except (ValueError, TypeError):
            return {"startDate": today - timedelta(days=365), "endDate": today}

'''


def translate_ts_file(ts_path: Path, import_map: dict | None = None) -> str:
    """Translate a single TypeScript file to Python source.

    Args:
        ts_path: Path to the TypeScript source file.
        import_map: Optional import mapping configuration.

    Returns:
        Translated Python source code as a string.
    """
    tree = parse_file(ts_path)
    visitor = NodeVisitor(import_map=import_map)
    translated = visitor.visit(tree.root_node)
    return translated


def translate_roai_calculator(
    roai_ts: Path,
    base_ts: Path,
    import_map: dict | None = None,
) -> str:
    """Translate the ROAI portfolio calculator from TypeScript to Python.

    Parses both the ROAI calculator and its base class, translates the
    relevant methods, and assembles them into a single Python class.

    Args:
        roai_ts: Path to the ROAI calculator TypeScript file.
        base_ts: Path to the base PortfolioCalculator TypeScript file.
        import_map: Optional import mapping configuration.

    Returns:
        Complete Python source code for the translated calculator.
    """
    log.info("Translating ROAI calculator: %s", roai_ts.name)

    # Parse and translate the ROAI calculator
    roai_code = translate_ts_file(roai_ts, import_map)

    # Parse and translate the base calculator (for helper methods)
    base_code = translate_ts_file(base_ts, import_map)

    # Build the final Python file with proper imports and runtime helpers
    python_source = build_python_file(
        class_code=RUNTIME_HELPERS + "\n\n" + roai_code,
        imports=CALCULATOR_IMPORTS,
        module_docstring="ROAI Portfolio Calculator — translated from TypeScript by tt.",
    )

    return python_source


def run_translation(repo_root: Path, output_dir: Path) -> None:
    """Run the full translation pipeline.

    Args:
        repo_root: Root of the repository.
        output_dir: Output directory for translated files.
    """
    # Source TypeScript files
    roai_ts = (
        repo_root / "projects" / "ghostfolio" / "apps" / "api" / "src"
        / "app" / "portfolio" / "calculator" / "roai" / "portfolio-calculator.ts"
    )
    base_ts = (
        repo_root / "projects" / "ghostfolio" / "apps" / "api" / "src"
        / "app" / "portfolio" / "calculator" / "portfolio-calculator.ts"
    )

    # Import map
    scaffold_dir = repo_root / "tt" / "tt" / "scaffold" / "ghostfolio_pytx"
    import_map_path = scaffold_dir / "tt_import_map.json"
    import_map = {}
    if import_map_path.exists():
        import_map = json.loads(import_map_path.read_text(encoding="utf-8"))

    # Output path
    output_file = (
        output_dir / "app" / "implementation" / "portfolio" / "calculator"
        / "roai" / "portfolio_calculator.py"
    )

    if not roai_ts.exists():
        log.warning("TypeScript source not found: %s", roai_ts)
        return

    # Translate
    python_source = translate_roai_calculator(roai_ts, base_ts, import_map)

    # Write output
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(python_source, encoding="utf-8")
    log.info("Translated → %s", output_file)

    print(f"  Translated {roai_ts.name} → {output_file}")
