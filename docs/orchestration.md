# Orchestration Patterns

How the main Claude session dispatches parallel work for the TT competition. The main session is the **orchestrator** — it reads requirements, picks a strategy, spawns subagents, reviews results, and merges.

## Pattern 1: Divide & Dispatch

**When:** Multiple independent translation aspects can be worked on in parallel.

```
┌─────────────┐
│ Orchestrator │  analyzes TS source, identifies translation aspects
└──────┬──────┘
       │
  ┌────┴────┐
  ▼         ▼
┌──────────┐  ┌──────────┐
│ Solver A │  │ Solver B │   parallel worktrees
│ (classes)│  │ (types)  │
└──────┬───┘  └──────┬───┘
       │             │
  ┌────┴─────────────┘
  ▼
┌──────────┐
│ Evaluate │  make evaluate_tt_ghostfolio after each merge
└──────────┘
```

**How to invoke:**

```
# In the main Claude session:
Agent(isolation: "worktree", prompt: "Improve class/method translation in tt/tt/... [full context]")
Agent(isolation: "worktree", prompt: "Handle TypeScript enums and interfaces... [full context]")
# Both run in parallel
# Then review each branch and merge the good ones
```

**Example — TT competition:**
- Agent A → Class hierarchy + method signature translation
- Agent B → Type annotation + enum conversion
- Agent C → Expression translation (optional chaining, ternary, etc.)
- Merge A, B, C into main sequentially, evaluating after each

**When to use this pattern:**
- Translation aspects are independent (classes vs types vs expressions)
- Each aspect can be tested independently
- Clear boundaries between changes

## Pattern 2: Dual-Solve & Pick

**When:** Unsure whether to use regex-based or AST-based translation for a specific aspect.

```
┌─────────────┐
│ Orchestrator │  identifies two viable approaches
└──────┬──────┘
       │
  ┌────┴────┐
  ▼         ▼
┌──────────┐  ┌──────────┐
│ Solver A │  │ Solver B │   same aspect, different approaches
│ (regex)  │  │ (AST)    │
└──────┬───┘  └──────┬───┘
       │             │
  ┌────┴─────────────┘
  ▼
┌───────────┐
│ Pick-Best │  evaluate_tt_ghostfolio on both, pick winner
└───────────┘
```

**When to use this pattern:**
- Architecture is unclear (regex vs AST, single-pass vs multi-pass)
- Problem is complex — getting it wrong wastes more time than trying twice
- You have time budget for it (not the last hour)

## Pattern 3: Staged Dispatch

**When:** Some translation aspects depend on others.

```
┌─────────────┐
│ Orchestrator │
└──────┬──────┘
       ▼
┌──────────────┐
│ Solver: Core │   basic class/method translation (foundation)
└──────┬───────┘
       │ merge to main
  ┌────┴────┐
  ▼         ▼
┌──────────┐  ┌──────────┐
│ Solver A │  │ Solver B │   features that build on core
│ (calc)   │  │ (report) │
└──────────┘  └──────────┘
```

**Example — TT competition:**
1. First: build the core class/method translation pipeline
2. Merge to main
3. Then in parallel: calculator-specific logic + report generation logic

## Pattern 4: Debug-Driven Development

**When:** You have a working baseline and want to incrementally fix failing tests.

```
┌─────────────┐
│ Orchestrator │  runs evaluation, categorizes failures
└──────┬──────┘
       │
  ┌────┴────┐
  ▼         ▼
┌──────────┐  ┌──────────┐
│ Debugger │  │ Debugger │   each investigates a test failure category
│ (perf)   │  │ (chart)  │
└──────┬───┘  └──────┬───┘
       │             │
  ┌────┴─────────────┘
  ▼
┌──────────┐
│ Evaluate │  merge fixes, run full eval, repeat
└──────────┘
```

This is likely the most common pattern in the middle phase of the competition: identify why specific tests fail, fix the translator, and iterate.

## Decision Framework

```
Which phase of the competition are you in?
├── Early (understanding) → Pattern 3 (Staged: build foundation first)
├── Middle (iterating)
│   ├── Multiple independent aspects → Pattern 1 (Divide & Dispatch)
│   ├── Approach unclear → Pattern 2 (Dual-Solve & Pick)
│   └── Fixing specific failures → Pattern 4 (Debug-Driven)
└── Late (polishing) → Single polisher agent, no parallelism needed
```

## Practical Tips

- **Brief the solver fully.** Include the complete requirements, relevant TS source code, and current translator state. The solver has no context from the main conversation.
- **Always evaluate after merge.** Run `make evaluate_tt_ghostfolio` and track the test count. If it went down, investigate.
- **One commit per solver.** Each solver commits its work. The orchestrator reviews and merges.
- **Don't over-parallelize.** 2-3 parallel agents is the sweet spot. Translator changes can conflict.
- **Merge early, merge often.** Don't wait for all agents to finish. Merge completed work immediately.
- **Track test count obsessively.** The number that matters: X tests passing out of Y total.
- **Rule compliance is non-negotiable.** Always run `make detect_rule_breaches` after every merge.
