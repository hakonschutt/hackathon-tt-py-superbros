# Person B: Quality, Scaffold & Test Maximization

## Your Mission

Make the translated output actually work. You own the scaffold support modules, import mappings, runtime helpers, and code quality. While Person A builds the translator pipeline, you make sure the output integrates correctly, passes tests, and scores well on quality.

## Your Areas

| Area | What |
|------|------|
| Scaffold | `tt/tt/scaffold/ghostfolio_pytx/` — support modules the translated code imports |
| Import map | `tt/tt/scaffold/ghostfolio_pytx/tt_import_map.json` — TS→Python import mappings |
| Runtime helpers | `tt/tt/runtime/helpers.py` — small shims for translated code |
| Test analysis | Read failing tests, figure out what's missing, feed back to Person A or fix in scaffold |
| Code quality | `make scoring_codequality` — type hints, docstrings, clean output |
| SOLUTION.md | Explain the approach, update throughout |
| Rule compliance | `make detect_rule_breaches` — keep us legal |

## Priority Order

### Step 1: Understand the target (~15 min)

Study what the translated code needs to produce. Read:

```bash
# The wrapper interface (what our code must implement)
translations/ghostfolio_pytx_example/app/wrapper/portfolio/

# The reference implementation (what correct output looks like)
translations/ghostfolio_pytx_example/app/implementation/

# The test fixtures (what scenarios are tested)
projecttests/ghostfolio_api/conftest.py
```

Map out: which Python classes, methods, and return shapes does the translated calculator need?

**Write initial SOLUTION.md. Commit.**

### Step 2: Build scaffold support modules (~20 min)

The translated calculator code will need Python equivalents of TypeScript types/models. Build these in `tt/tt/scaffold/ghostfolio_pytx/` so they get copied into the output:

- **Models/types** that the calculator imports (e.g., `PortfolioOrder`, `SymbolMetrics`, `TransactionPoint`)
- **Enum definitions** used by the calculator (activity types, performance types)
- **Helper functions** that TS library calls map to (e.g., `differenceInDays`, date utils)
- **`__init__.py`** files for proper Python packages

These are NOT translations — they're the Python support layer that translated code imports.

**Commit after each module.**

### Step 3: Import mapping (~15 min)

Build `tt/tt/scaffold/ghostfolio_pytx/tt_import_map.json`:

```json
{
  "@ghostfolio/common/interfaces": "app.wrapper.portfolio.interfaces",
  "@ghostfolio/common/types": "app.implementation.types",
  "date-fns": "datetime",
  "big.js": "decimal",
  "lodash": null
}
```

This tells the translator how to convert TS import paths to Python import paths. Update as Person A discovers new imports that need mapping.

**Commit.**

### Step 4: Run tests, analyze failures (~ongoing)

```bash
make evaluate_tt_ghostfolio
```

For each failing test:
1. What endpoint does it hit?
2. What value is wrong or missing?
3. Is the problem in the **translator** (Person A) or the **scaffold** (you)?
   - Translator problem: the TS→Python conversion is wrong → tell Person A what construct to fix
   - Scaffold problem: the translated code can't find an import, missing type, missing helper → fix it yourself

This is your main loop for the middle phase of the competition.

### Step 5: Runtime helpers

`tt/tt/runtime/helpers.py` — small utilities the translated code may need:

```python
from datetime import datetime, date

def difference_in_days(date_a: date, date_b: date) -> int:
    """Equivalent of date-fns differenceInDays."""
    return (date_a - date_b).days

def clamp(value: float, min_val: float, max_val: float) -> float:
    return max(min_val, min(max_val, value))

EPSILON = 2.220446049250313e-16  # Number.EPSILON equivalent
```

### Step 6: Code quality (last 20 min)

Run `make scoring_codequality` and improve:

**In `tt/tt/` (the translator itself):**
- Type hints on ALL function signatures
- Docstrings on all public functions and classes
- `pathlib.Path` for file paths
- Proper error handling with specific exceptions
- Functions under ~30 lines

**In generated output:**
- Make the emitter produce clean Python (Person A's code, but you review output quality)
- Proper imports, no dead code, no syntax errors
- Suggest improvements to Person A's emitter

### Step 7: Final SOLUTION.md

Must explain:
- What the translator does and how it works
- The tree-sitter parsing approach
- Which TypeScript patterns are handled
- Key design decisions and trade-offs
- Known limitations
- How to run it

## Key Test Groups (know what you're measuring)

| Tests | Count | What they need |
|-------|-------|----------------|
| Already passing (scaffold) | ~48 | Nothing — don't regress these |
| Investment grouping (day/month/year) | ~20 | Correct activity aggregation |
| Performance calculations | ~15 | Calculator math (Person A's domain) |
| Holdings with market prices | ~15 | Calculator + current price lookup |
| Chart history | ~8 | Date generation + historical prices |
| Dividends | ~10 | DIVIDEND activity filtering |
| Details endpoint | ~14 | Aggregation of holdings + summary |
| Report/xRay | ~9 | Rule evaluation structure |

## Workflow

```bash
scripts/new-task.sh quality "Scaffold, imports, quality, test analysis"
cd .worktrees/quality && claude
```

Your loop: `make evaluate_tt_ghostfolio` → read failures → fix scaffold or relay to Person A → commit.

## Coordination with Person A

- Person A builds the translator, you make the output work
- When you discover a TS pattern the translator doesn't handle, file it to Person A with the exact pattern and expected Python output
- When Person A's translated code needs a Python module to import, you build it in scaffold
- Merge frequently — your scaffold fixes often unblock Person A's translator output
- You own the final merge, quality pass, and submission
