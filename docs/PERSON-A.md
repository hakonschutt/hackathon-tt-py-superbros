# Person A: Calculator Core & Performance Math

## Your Mission

Make the translated `RoaiPortfolioCalculator` compute correct numbers. You own the core calculation pipeline — the loop that processes activities and produces performance metrics, chart data, and holdings values.

## Your Test Files (measure progress here)

| File | Tests | What they need |
|------|-------|----------------|
| `test_advanced.py` | 10 | Open position P&L, partial sell, chart entries, market prices |
| `test_deeper.py` | 7 | Closed position P&L with fees, dividend + market price, TWI |
| `test_novn_buy_and_sell.py` | 7 | Full buy/sell lifecycle, realized P&L, TWI percentage |
| `test_same_day_transactions.py` | 5 | Same-day BUY+SELL, EPSILON guard, finite percentage |
| `test_short_cover.py` | 6 | Short position open/cover, short profit |
| `test_msft_fractional.py` | 5 | Fractional shares, weighted avg cost, exact closure |

**~40 tests to capture.** Run just your tests with:

```bash
make spinup-and-test-ghostfolio_pytx PYTEST_ARGS="-k 'test_advanced or test_deeper or test_novn or test_same_day or test_short_cover or test_msft_fractional'"
```

Or run the full suite to see overall progress:

```bash
make evaluate_tt_ghostfolio
```

## What to Translate

The main TypeScript source is the ROAI calculator:

```
projects/ghostfolio/apps/api/src/app/portfolio/calculator/roai/portfolio-calculator.ts
```

With base class logic in:

```
projects/ghostfolio/apps/api/src/app/portfolio/calculator/portfolio-calculator.ts
```

### Priority order (each unlocks the next)

**1. Transaction processing loop** (unlocks everything)
- Translate the main loop that iterates activities and builds `TransactionPoint` entries
- Track: quantity, investment, average cost per symbol
- Handle BUY (add to position), SELL (reduce position, record realized P&L)

**2. Performance calculation** (unlocks test_novn, test_deeper, test_same_day)
- `netPerformance` = realized gains + unrealized gains - fees
- `grossPerformance` = same but without fees
- Time-Weighted Investment (TWI) as denominator for percentage
- `netPerformancePercentage` = netPerformance / TWI
- **EPSILON guard**: when buy and sell are same day, `differenceInDays = 0` — use `Number.EPSILON` equivalent to avoid division by zero

**3. Market value integration** (unlocks test_advanced holding/market tests)
- Use `self.current_rate_service.get_latest_price(symbol)` for current value
- `currentValueInBaseCurrency` = quantity * currentMarketPrice
- Unrealized P&L = currentValue - investment - fees

**4. Chart generation** (unlocks test_advanced chart tests, helps Person B's btcusd chart tests)
- Generate daily entries between first activity and today
- Each entry: `{ date, netPerformance, investmentValueWithCurrencyEffect }`
- Use `current_rate_service.get_nearest_price(symbol, date)` for historical values

**5. Edge cases** (unlocks test_short_cover, test_msft_fractional)
- Short positions: SELL before BUY = negative position, cover via BUY
- Fractional quantities: use Decimal or high-precision float
- Partial sells: average cost basis, combined realized + unrealized P&L

## Key Formulas from TypeScript

```
// Realized P&L on a SELL
realizedProfit = (sellPrice - avgCostBasis) * sellQuantity

// TWI (Time-Weighted Investment) — the denominator for percentage
// Each buy adds: quantity * unitPrice * (totalDays - daysFromStart) / totalDays
// This weights earlier investments more heavily
timeWeightedInvestment += quantity * unitPrice * timeWeight

// Net performance percentage
netPerformancePercentage = netPerformance / timeWeightedInvestment

// Same-day guard (differenceInDays = 0)
timeWeight = max(differenceInDays, Number.EPSILON) / totalDays
```

## Scaffold Integration Points

Your translated code writes to:
```
translations/ghostfolio_pytx/app/implementation/portfolio/calculator/roai/portfolio_calculator.py
```

The calculator class must:
- Extend `PortfolioCalculator` (the abstract base in `app/wrapper/`)
- Accept `activities` and `current_rate_service` in `__init__`
- Implement `get_performance()` returning chart + performance dict
- Implement `get_holdings()` returning per-symbol holdings

Person B handles `get_investments()`, `get_dividends()`, `get_details()`, `evaluate_report()` — but your calculation results feed into theirs, so getting the core loop right is the highest-leverage thing you can do.

## Workflow

```bash
# 1. Start your worktree
scripts/new-task.sh calc "Core calculator translation"
cd .worktrees/calc

# 2. Launch Claude Code
claude

# 3. Iterate
#    - Edit tt/tt/translator.py (or add modules in tt/tt/)
#    - uv run --project tt tt translate
#    - make spinup-and-test-ghostfolio_pytx
#    - Commit on progress

# 4. When ready to merge
#    - Commit all changes
#    - Go to main repo: cd /path/to/hackathon-tt-py-superbros
#    - scripts/merge.sh calc
#    - make evaluate_tt_ghostfolio
```

## Coordination with Person B

- You both modify `tt/tt/` — use separate files/modules where possible
- If you must both touch `translator.py`, keep changes in separate functions
- Merge frequently (every 15-20 min) to avoid painful conflicts
- Your core loop results feed Person B's endpoints — the sooner your math works, the sooner their aggregation tests pass too
