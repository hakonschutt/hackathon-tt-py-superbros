# Coordination Protocol

## The Rules

1. **Each person works in a worktree** — never edit `main` directly during the build phase
2. **Merge every 15-20 minutes** — small frequent merges beat one big merge at the end
3. **Run `make evaluate_tt_ghostfolio` after every merge** — track the number
4. **Run `make detect_rule_breaches` before every commit** — violations can disqualify

## Worktree Setup

```bash
# Person A
scripts/new-task.sh calc "Core calculator translation"
cd .worktrees/calc && claude

# Person B
scripts/new-task.sh endpoints "Endpoint aggregation and data formatting"
cd .worktrees/endpoints && claude
```

## Merge Protocol

Only one person merges at a time. Call it out verbally.

```bash
# 1. Go to main repo (not your worktree)
cd /path/to/hackathon-tt-py-superbros

# 2. Merge
scripts/merge.sh calc       # or: scripts/merge.sh endpoints

# 3. Evaluate
make evaluate_tt_ghostfolio

# 4. Note the score, tell the other person
```

If merge conflicts happen in `translator.py`:
- Stop and resolve together
- Or: restructure into separate modules so files don't overlap

## File Ownership (avoid conflicts)

```
tt/tt/
├── translator.py          # SHARED — keep changes in separate functions
├── calculator_core.py     # Person A — core math translation logic
├── endpoint_builders.py   # Person B — investment/dividend/details/report builders
├── type_mappings.py       # Person B — TS type/enum to Python mappings
├── scaffold/              # Person B — support modules
│   └── ghostfolio_pytx/   # Person B — scaffold overlays
└── cli.py                 # Don't touch unless necessary
```

The names above are suggestions. The point: **agree on who owns which files** so you don't both edit the same file in parallel worktrees. If you must share `translator.py`, structure it so Person A writes functions like `translate_calculator_methods()` and Person B writes `translate_endpoint_methods()`, both called from a shared entry point.

## Progress Tracking

Keep a running score. After each merge + evaluate:

```
Time    Tests Passing    Delta    Who Merged
-----   -------------    -----    ----------
15:30   48/135           -        baseline
15:50   52/135           +4       Person B (investments grouping)
16:10   58/135           +6       Person A (basic performance calc)
...
```

Write this in a shared terminal or on paper. It keeps urgency visible.

## Dependency Map

```
Person A: Calculator Core          Person B: Endpoints
─────────────────────────          ─────────────────────
Transaction loop ──────────────┐
Performance math ──────────┐   │
Market value lookups ──┐   │   │
                       │   │   │
                       ▼   ▼   ▼
                   ┌───────────────┐
                   │  get_holdings  │◄── Person B structures output
                   │  get_details   │◄── Person B structures output
                   └───────────────┘
                                       get_investments ◄── Person B (independent)
                                       get_dividends   ◄── Person B (independent)
                                       evaluate_report ◄── Person B (independent)
                                       chart dates     ◄── Shared (A math, B dates)
```

Person B's `get_investments()`, `get_dividends()`, and `evaluate_report()` are **fully independent** of Person A's work — they only need the raw activity data, not calculated performance. Start there.

Person B's `get_holdings()` and `get_details()` benefit from Person A's performance calculations but can return partial results (cost basis, quantity) without them.

## Timeline

| Time | Phase | Action |
|------|-------|--------|
| 0:00 | Start | Both read TypeScript source, set up worktrees |
| 0:15 | Build | Heads down. Person A: transaction loop. Person B: investment grouping |
| 0:30 | Merge 1 | First merge + evaluate. Note baseline improvement |
| 0:45 | Build | Continue. Person A: performance math. Person B: dividends |
| 1:00 | Merge 2 | Second merge + evaluate |
| 1:15 | Build | Person A: market values, chart. Person B: holdings, details |
| 1:30 | Merge 3 | Third merge + evaluate |
| 1:45 | Build | Both: target remaining failing tests, edge cases |
| 2:00 | Merge 4 | Fourth merge + evaluate |
| 2:15 | Polish | Person A: edge cases (short, fractional). Person B: report, quality |
| 2:30 | Final | Both: SOLUTION.md, `make scoring_codequality`, final commit |
| 2:45 | Submit | `scripts/submit.sh`, `make publish_results` |

## Emergency: "We're Colliding on the Same File"

Option 1: **Module split** — move your code into separate files, import from a shared entry point.

Option 2: **Serial merge** — one person merges, the other rebases on top:
```bash
# Person B, after Person A merged:
cd .worktrees/endpoints
git fetch origin
git rebase main
# resolve any conflicts
# continue working
```

Option 3: **Pair on it** — if it's one critical file, sit together for 5 minutes and merge manually.
