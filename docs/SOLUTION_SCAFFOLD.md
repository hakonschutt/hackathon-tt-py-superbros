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
