# Person B: Endpoints, Aggregation & Quality

## Your Mission

Make the API endpoints return correct structured data — investments grouped by day/month/year, dividend lists, detailed holdings, and report evaluation. You also own the 15% code quality score and SOLUTION.md.

## Your Test Files (measure progress here)

| File | Tests | What they need |
|------|-------|----------------|
| `test_btcusd.py` | 9 | Chart dates, holdings values, investment grouping |
| `test_remaining_specs.py` | 39 | Investments by month/year, holdings, multi-symbol scenarios |
| `test_details.py` | 17 | Details endpoint: holdings, summary, market prices, P&L |
| `test_dividends.py` | 10 | Dividend list, amounts, grouping by month/year |
| `test_report.py` | 9 | xRay structure, categories, rules, statistics |
| `test_no_orders.py` | 4 | Empty portfolio edge cases |

**~88 tests to capture.** Many in `test_remaining_specs.py` test investment grouping which the scaffold already partially handles. Run just your tests:

```bash
make spinup-and-test-ghostfolio_pytx PYTEST_ARGS="-k 'test_btcusd or test_remaining or test_details or test_dividends or test_report or test_no_orders'"
```

## What to Build

You work on two layers:
1. **Scaffold support** (`tt/tt/scaffold/`) — the Python modules that the translated code imports
2. **Translator logic** for endpoint methods — `get_investments()`, `get_dividends()`, `get_details()`, `evaluate_report()`

### Priority order

**1. Investment grouping — `get_investments()`** (unlocks ~20 tests across btcusd, remaining_specs)

The endpoint accepts a `groupBy` query param: `day`, `month`, or `year`.

```python
# For each activity (BUY/SELL), track cumulative investment
# BUY:  investment += quantity * unitPrice
# SELL: investment -= quantity * avgCostBasis (proportional reduction)
#
# Group by requested period:
#   day:   return each activity date
#   month: aggregate to YYYY-MM-01
#   year:  aggregate to YYYY-01-01
#
# Return: [{"date": "2021-12-12", "investment": 44558.42}, ...]
```

Key TypeScript source for grouping logic:
```
projects/ghostfolio/apps/api/src/app/portfolio/calculator/portfolio-calculator.ts
```
Look for `getInvestments()` method.

**2. Dividends — `get_dividends()`** (unlocks 10 tests)

Filter activities to only `type == "DIVIDEND"`, compute amount = quantity * unitPrice, group by day/month/year same as investments.

```python
# Return: [{"date": "2021-11-16", "investment": 0.62}, ...]
# Note: the field is called "investment" in the API response even for dividends
```

**3. Holdings enrichment — `get_holdings()`** (unlocks ~15 tests)

Build per-symbol holdings with market data:

```python
holdings = {
    "BTCUSD": {
        "quantity": 1.0,
        "investment": 44558.42,      # cost basis
        "averagePrice": 44558.42,    # avg cost per share
        "marketPrice": 100.0,        # from current_rate_service
        "currency": "USD",
        "netPerformance": ...,       # currentValue - investment - fees
        "netPerformancePercentage": ...,
    }
}
```

Use `current_rate_service.get_latest_price(symbol)` for market prices.
Omit symbols where quantity == 0 (fully closed positions).

**4. Details endpoint — `get_details()`** (unlocks 17 tests)

Aggregates holdings + summary:

```python
{
    "accounts": {},
    "holdings": [
        {
            "symbol": "BTCUSD",
            "name": "BTCUSD",
            "quantity": 1.0,
            "investment": 44558.42,
            "marketPrice": 100.0,
            "netPerformance": ...,
            "netPerformancePercent": ...,
            "currency": "USD",
            "dataSource": "YAHOO"
        }
    ],
    "platforms": {},
    "summary": {
        "totalInvestment": 44558.42,
        "netPerformance": ...,
    },
    "hasError": False
}
```

**5. Report/xRay — `evaluate_report()`** (unlocks 9 tests)

Needs category-based rules engine. Check TypeScript:
```
projects/ghostfolio/apps/api/src/app/portfolio/calculator/portfolio-calculator.ts
```
Look for the report/evaluation section. Structure:

```python
{
    "xRay": {
        "categories": [
            {
                "key": "...",
                "name": "...",
                "rules": [{"name": "...", "isActive": True/False}]
            }
        ],
        "statistics": {
            "rulesActiveCount": N,
            "rulesFulfilledCount": M  # M <= N
        }
    }
}
```

**6. Code quality (the 15%)** — run `make scoring_codequality` and improve:
- Type hints on all functions in `tt/tt/`
- Docstrings on public functions
- Clean generated output (no dead code, proper imports)

## Key Test Fixtures You Need to Know

| Fixture | Activities | Used by |
|---------|-----------|---------|
| `btcusd_session` | BUY 1 BTCUSD @ 44558.42 | test_btcusd |
| `baln_buy_session` | BUY 2 BALN.SW @ 136.6 | test_remaining_specs |
| `baln_buy_and_buy` | BUY 2 + BUY 3 BALN.SW | test_remaining_specs |
| `baln_buy_and_sell` | BUY 2 + SELL 2 BALN.SW | test_remaining_specs |
| `baln_buy_and_sell_in_two` | BUY 2 + SELL 1 + SELL 1 BALN.SW | test_remaining_specs |
| `btceur_session` | BUY 1 BTCEUR @ 36270.69 | test_remaining_specs |
| `fee_session` | FEE only | test_remaining_specs |
| `googl_session` | BUY 1 GOOGL @ 103.07 | test_remaining_specs |
| `jnug_session` | BUY 10 + SELL 10 + BUY 5 + SELL 5 JNUG | test_remaining_specs |
| `msft_with_dividend` | BUY 1 MSFT + DIVIDEND 0.62 | test_dividends, test_details |
| `msft_multiple_dividends` | BUY + DIV + DIV | test_dividends |
| Empty (no activities) | None | test_no_orders, test_report |

## Scaffold Integration

Your work goes into the calculator methods. The scaffold wiring already:
- Routes HTTP requests to the calculator
- Passes `activities` and `current_rate_service` to the constructor
- Handles auth and user lifecycle

You implement the methods that return data. Person A's core loop gives you the computed values (performance, P&L); you structure and group the output.

## Workflow

```bash
# 1. Start your worktree
scripts/new-task.sh endpoints "Endpoint aggregation and data formatting"
cd .worktrees/endpoints

# 2. Launch Claude Code
claude

# 3. Iterate
#    - Edit tt/tt/translator.py or add modules in tt/tt/
#    - Add scaffold support in tt/tt/scaffold/ if needed
#    - uv run --project tt tt translate
#    - make spinup-and-test-ghostfolio_pytx
#    - Commit on progress

# 4. When ready to merge
#    - Commit all changes
#    - Go to main repo
#    - scripts/merge.sh endpoints
#    - make evaluate_tt_ghostfolio
```

## Coordination with Person A

- Person A builds the core calculation loop — your aggregation methods can call into the same data structures
- If Person A's math isn't ready yet, you can still build correct grouping/formatting with the simple cost-basis values the scaffold already computes
- Merge frequently to pick up each other's work
- You own SOLUTION.md — update it as both of you make progress
- You own the final quality polish — `make scoring_codequality` in the last 20 minutes
