# Person B: Scaffold, Quality & Test Maximization Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Python scaffold support modules, import map, and runtime helpers so that Person A's translated calculator has everything it needs to run. Maximize test pass rate through scaffold fixes and test analysis. Own code quality and SOLUTION.md.

**Architecture:** Person B owns the **support layer** — files that the translated calculator imports at runtime. Person A owns the **translator pipeline** (parser.py, emitter.py, translator.py). We do NOT touch each other's files.

**Person B's files (we own these):**
- `tt/tt/scaffold/ghostfolio_pytx/` — all support modules
- `SOLUTION.md`
- Code quality improvements to existing `tt/tt/` files (type hints, docstrings only — not logic changes)

**Person A's files (DO NOT TOUCH):**
- `tt/tt/parser.py`
- `tt/tt/emitter.py`
- `tt/tt/translator.py`
- `tt/tt/visitor.py`
- `tt/tt/transformers/`

**Tech Stack:** Python 3.11+, decimal.Decimal, datetime, dataclasses

**Baseline:** 0/112 tests passing, 82.8% code quality, overall 12.4/100

**Rule Constraints (from rule checker source code analysis):**

| Rule Check | What it flags | Impact on our scaffold code |
|---|---|---|
| `detect_explicit_financial_logic` | Functions in scaffold with >3 arithmetic ops per function, nested for/while loops, specific variable names (inv_buys, qty_buys, gps, etc.) | Keep functions small, no nested loops, avoid flagged var names |
| `detect_scaffold_bloat` | Private helpers in scaffold `main.py` only | Does NOT apply to our support modules (only main.py) |
| `detect_code_block_copying` | 10+ line blocks from tt/ (including scaffold) appearing verbatim in translated output | Our scaffold modules are imported, not copied into the calculator file — safe as long as Person A's emitter doesn't reproduce our code verbatim |
| `detect_explicit_implementation` | Domain identifiers and "BUY"/"SELL" in tt/ core | Scaffold files are SKIPPED for signals 1-3 (confirmed in source: `skip_domain=is_scaffold`). Scaffold-specific checks only look for forbidden imports, domain function names, and domain dict keys |

**Key insight from rules:** The `detect_explicit_implementation` checker skips signals 1-3 (function length, domain identifiers, event strings) for scaffold files. It only runs scaffold-specific checks (signals 5-7: forbidden imports, domain function name keywords, domain dict keys). This means scaffold support modules CAN reference domain concepts like "BUY"/"SELL" as long as they don't hit the `detect_explicit_financial_logic` limits (>3 arithmetic ops, nested loops, specific var names).

---

## File Map

### Scaffold support files (in `tt/tt/scaffold/ghostfolio_pytx/`)

| File | Responsibility |
|------|---------------|
| `app/implementation/portfolio/calculator/roai/types.py` | Enums (PerformanceCalculationType), constants (DATE_FORMAT, INVESTMENT_ACTIVITY_TYPES) |
| `app/implementation/portfolio/calculator/roai/date_utils.py` | Python equivalents of date-fns functions used by the calculator |
| `app/implementation/portfolio/calculator/roai/helpers.py` | get_factor(), get_interval_from_date_range(), DATE_FORMAT |
| `app/implementation/portfolio/calculator/roai/__init__.py` | Package init |
| `app/implementation/portfolio/calculator/__init__.py` | Package init |
| `app/implementation/portfolio/__init__.py` | Package init |
| `app/implementation/__init__.py` | Package init |
| `tt_import_map.json` | TS→Python import path mappings (used by Person A's translator) |

### Other files we own

| File | What |
|------|------|
| `SOLUTION.md` | Explain approach, architecture, trade-offs |

---

## Task 1: Initial SOLUTION.md (Person B section only)

**Files:**
- Create: `docs/SOLUTION_SCAFFOLD.md` (Person B's draft — merged into SOLUTION.md at the end)

Person A may also be editing SOLUTION.md. To avoid merge conflicts, we write our section in a separate file and merge it into SOLUTION.md as the final step (Task 8).

- [ ] **Step 1: Write Person B's scaffold/quality section**

Create `docs/SOLUTION_SCAFFOLD.md`:

```markdown
# Scaffold & Support Layer (Person B)

## Scaffold Support Modules

The translated calculator imports Python support modules that provide runtime equivalents of TypeScript libraries. These live in `tt/tt/scaffold/ghostfolio_pytx/app/implementation/portfolio/calculator/roai/`:

### types.py
- `PerformanceCalculationType` — enum with MWR, ROAI, ROI, TWR values
- `INVESTMENT_ACTIVITY_TYPES` — tuple of activity types the calculator processes
- `DATE_FORMAT` — Python strftime format matching TS DATE_FORMAT constant

### date_utils.py
Python equivalents of every `date-fns` function used by the calculator:
- `parse_date`, `format_date` — ISO string ↔ date conversion
- `difference_in_days`, `is_before`, `is_after`, `is_this_year` — comparisons
- `start_of_year`, `end_of_year`, `start_of_month`, `start_of_week` — boundaries
- `sub_days`, `sub_years` — arithmetic
- `each_day_of_interval`, `each_year_of_interval` — range generation

### helpers.py
- `get_factor(activity_type)` — returns +1 for BUY, -1 for SELL (mirrors portfolio.helper.ts)
- `get_interval_from_date_range(range, start?)` — converts "1d", "1y", "max", "ytd" etc. to {startDate, endDate} (mirrors calculation-helper.ts)

### tt_import_map.json
Maps TypeScript import paths to Python module paths. The translator reads this to convert `import { X } from '@ghostfolio/...'` to `from app.implementation... import X`.

## Design Decisions

- **Decimal for Big.js** — Python decimal.Decimal provides arbitrary-precision math matching Big.js semantics. Final values are converted to float for JSON serialization.
- **Standalone date helpers** — Small focused functions rather than wrapping datetime. Each function mirrors exactly one date-fns export for easy 1:1 mapping.
- **No financial logic in scaffold** — Rule-enforced constraint. All calculation logic comes from the translated source. Scaffold only provides utilities.

## Code Quality

- Type hints on all function signatures
- Docstrings on all public functions
- pathlib.Path for file paths in tt/ code
- Functions kept under 30 lines
```

- [ ] **Step 2: Commit**

```bash
git add docs/SOLUTION_SCAFFOLD.md
git commit -m "docs: add Person B scaffold section draft for SOLUTION.md"
```

---

## Task 2: Scaffold package structure + types

**Files:**
- Create: `tt/tt/scaffold/ghostfolio_pytx/app/implementation/__init__.py`
- Create: `tt/tt/scaffold/ghostfolio_pytx/app/implementation/portfolio/__init__.py`
- Create: `tt/tt/scaffold/ghostfolio_pytx/app/implementation/portfolio/calculator/__init__.py`
- Create: `tt/tt/scaffold/ghostfolio_pytx/app/implementation/portfolio/calculator/roai/__init__.py`
- Create: `tt/tt/scaffold/ghostfolio_pytx/app/implementation/portfolio/calculator/roai/types.py`

- [ ] **Step 1: Create all `__init__.py` files**

Each one is empty (ensures the package structure exists for imports).

- [ ] **Step 2: Create types.py**

```python
"""Type definitions and enums for the translated calculator."""
from __future__ import annotations


class PerformanceCalculationType:
    """Enum for performance calculation methodology."""

    MWR = "MWR"
    ROAI = "ROAI"
    ROI = "ROI"
    TWR = "TWR"


INVESTMENT_ACTIVITY_TYPES = ("BUY", "DIVIDEND", "SELL")

DATE_FORMAT = "%Y-%m-%d"
```

- [ ] **Step 3: Run rule checks**

```bash
make detect_rule_breaches
```

Expected: all OK

- [ ] **Step 4: Commit**

```bash
git add tt/tt/scaffold/ghostfolio_pytx/
git commit -m "feat(scaffold): add package structure and type definitions"
```

---

## Task 3: Date utility functions

**Files:**
- Create: `tt/tt/scaffold/ghostfolio_pytx/app/implementation/portfolio/calculator/roai/date_utils.py`

- [ ] **Step 1: Create date_utils.py**

All functions are simple (no financial arithmetic, no nested loops). Each is a standalone equivalent of one date-fns export.

```python
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
```

- [ ] **Step 2: Run rule checks**

```bash
make detect_rule_breaches
```

Expected: all OK — no financial arithmetic, no nested loops.

- [ ] **Step 3: Commit**

```bash
git add tt/tt/scaffold/ghostfolio_pytx/app/implementation/portfolio/calculator/roai/date_utils.py
git commit -m "feat(scaffold): add date utility functions (date-fns equivalents)"
```

---

## Task 4: Helper functions

**Files:**
- Create: `tt/tt/scaffold/ghostfolio_pytx/app/implementation/portfolio/calculator/roai/helpers.py`

- [ ] **Step 1: Create helpers.py**

```python
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
```

- [ ] **Step 2: Run rule checks**

```bash
make detect_rule_breaches
```

Expected: all OK — get_factor has 0 arithmetic ops, get_interval_from_date_range has only date arithmetic (not flagged as financial).

- [ ] **Step 3: Commit**

```bash
git add tt/tt/scaffold/ghostfolio_pytx/app/implementation/portfolio/calculator/roai/helpers.py
git commit -m "feat(scaffold): add helper functions (get_factor, get_interval_from_date_range)"
```

---

## Task 5: Import map

**Files:**
- Create: `tt/tt/scaffold/ghostfolio_pytx/tt_import_map.json`

This tells Person A's translator how to map TS import paths to Python import paths.

- [ ] **Step 1: Create tt_import_map.json**

```json
{
  "@ghostfolio/api/app/portfolio/calculator/portfolio-calculator": "app.wrapper.portfolio.calculator.portfolio_calculator",
  "@ghostfolio/api/app/portfolio/interfaces/portfolio-order-item.interface": "app.wrapper.portfolio.interfaces.portfolio_order_item",
  "@ghostfolio/api/helper/portfolio.helper": "app.implementation.portfolio.calculator.roai.helpers",
  "@ghostfolio/common/calculation-helper": "app.implementation.portfolio.calculator.roai.helpers",
  "@ghostfolio/common/helper": "app.implementation.portfolio.calculator.roai.helpers",
  "@ghostfolio/common/interfaces": "app.wrapper.portfolio.interfaces",
  "@ghostfolio/common/types": "app.implementation.portfolio.calculator.roai.types",
  "@ghostfolio/common/types/performance-calculation-type.type": "app.implementation.portfolio.calculator.roai.types",
  "big.js": "decimal",
  "date-fns": "app.implementation.portfolio.calculator.roai.date_utils",
  "lodash": null
}
```

- [ ] **Step 2: Commit**

```bash
git add tt/tt/scaffold/ghostfolio_pytx/tt_import_map.json
git commit -m "feat(scaffold): add TypeScript-to-Python import mapping"
```

---

## Task 6: Run tests, analyze failures, iterate on scaffold

This is the **main loop** for Person B during the competition. After Person A's translator starts producing output, we run tests and fix scaffold issues.

- [ ] **Step 1: Run full evaluation**

```bash
make evaluate_tt_ghostfolio
```

Record which tests pass and fail.

- [ ] **Step 2: For each failing test, triage**

For each failure:
1. What endpoint does it hit? (performance, investments, holdings, details, dividends, report)
2. What value is wrong vs expected?
3. Is the problem in the **translator** (Person A) or the **scaffold** (us)?
   - **Import error** → missing scaffold module or wrong import map entry → fix ourselves
   - **Missing function** → scaffold helper needed → add to helpers.py or date_utils.py
   - **Wrong calculation** → Person A's translated code is wrong → communicate the exact TS pattern and expected Python to Person A
   - **Missing method** → translated calculator doesn't implement an abstract method → Person A issue
   - **Wrong response shape** → translated code returns wrong dict structure → could be either

- [ ] **Step 3: Fix scaffold issues found**

Common fixes:
- Add missing entries to `tt_import_map.json`
- Add missing date utility functions to `date_utils.py`
- Add missing helper functions to `helpers.py`
- Add missing type/enum definitions to `types.py`
- Fix incorrect import paths

- [ ] **Step 4: Re-run tests after each fix**

```bash
make evaluate_tt_ghostfolio
```

- [ ] **Step 5: Commit after each meaningful improvement**

```bash
git add tt/tt/scaffold/ghostfolio_pytx/
git commit -m "fix(scaffold): [describe what was fixed]"
```

**Repeat steps 2-5 until test count stabilizes or time runs out.**

---

## Task 7: Code quality pass

**Files:**
- Review/modify: all `tt/tt/` files (type hints and docstrings only — no logic changes to Person A's code)
- Review: translated output quality

- [ ] **Step 1: Run code quality scoring**

```bash
make scoring_codequality
```

Review the scores. Currently 82.8% — target 90%+. The score is weighted 80% translated code, 20% tt/ code.

- [ ] **Step 2: Improve tt/ code quality (our files only)**

For files we own (`tt/tt/scaffold/ghostfolio_pytx/`), ensure:
- Type hints on ALL function parameters and return values
- Docstrings on all public functions and classes
- Clean structure, no dead code

For `tt/tt/cli.py` and `tt/tt/__init__.py` (shared files), only add:
- Missing type hints
- Missing docstrings
- Do NOT change logic

- [ ] **Step 3: Run quality + rule checks**

```bash
make scoring_codequality
make detect_rule_breaches
```

- [ ] **Step 4: Commit**

```bash
git add tt/tt/
git commit -m "refactor: improve code quality — type hints, docstrings"
```

---

## Task 8: Final SOLUTION.md merge and submission

**Files:**
- Modify: `SOLUTION.md`
- Read: `docs/SOLUTION_SCAFFOLD.md`

- [ ] **Step 1: Final evaluation run**

```bash
make detect_rule_breaches
make evaluate_tt_ghostfolio
```

Record final score.

- [ ] **Step 2: Merge Person B section into SOLUTION.md**

Read current `SOLUTION.md` (Person A may have added translator details). Integrate `docs/SOLUTION_SCAFFOLD.md` content into the appropriate sections without overwriting Person A's work. Add:
- Final test pass count
- Known limitations
- How to run: `make evaluate_tt_ghostfolio`

- [ ] **Step 3: Commit**

```bash
git add SOLUTION.md
git commit -m "docs: merge scaffold section into SOLUTION.md, add final results"
```

---

## Communication Protocol with Person A

When you find a translator issue during Task 6, communicate to Person A with this format:

```
TRANSLATOR ISSUE: [short description]
Test: [test file::test name]
Expected: [what the test expects]
Got: [what actually happened — error message or wrong value]
TS pattern: [the TypeScript code that needs to be translated]
Expected Python: [what the Python output should look like]
```

When Person A needs a new scaffold module, they communicate:

```
SCAFFOLD REQUEST: [what they need]
Import path: [what the translated code will import]
Functions/classes needed: [list]
```

---

## Execution Priority & Dependencies

| Priority | Task | Est. Time | Depends on | Impact |
|----------|------|-----------|------------|--------|
| 1 | Task 1: SOLUTION.md (initial) | 5 min | Nothing | Required by rules |
| 2 | Task 2: Package structure + types | 5 min | Nothing | Foundation for Person A |
| 3 | Task 3: Date utilities | 10 min | Nothing | Foundation for Person A |
| 4 | Task 4: Helper functions | 10 min | Task 3 (imports date_utils) | Foundation for Person A |
| 5 | Task 5: Import map | 5 min | Nothing | Foundation for Person A |
| 6 | **Task 6: Test & fix loop** | **60+ min** | Person A producing output | **Biggest score impact** |
| 7 | Task 7: Code quality | 15 min | Tasks 2-5 done | 15% of score |
| 8 | Task 8: Final submission | 5 min | Everything | Required |

Tasks 1-5 can all be done immediately and in parallel — they unblock Person A.
Task 6 is iterative and ongoing — it's the main loop once Person A starts producing output.
Tasks 7-8 are final polish.
