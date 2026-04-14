# Coordination Protocol

## The Split

| Person A: Translator | Person B: Quality |
|---------------------|-------------------|
| Builds `tt/tt/` pipeline | Builds scaffold support modules |
| tree-sitter parsing → Python emission | Import mappings, runtime helpers |
| Owns: parser, visitor, transformers, emitter | Owns: scaffold/, SOLUTION.md, quality |
| Measures: does `tt translate` produce valid Python? | Measures: do tests pass? is quality score high? |

## File Ownership

```
tt/tt/
├── translator.py              # Person A (Person B can edit pipeline config)
├── parser.py                  # Person A
├── visitor.py                 # Person A
├── emitter.py                 # Person A
├── transformers/              # Person A (all files)
├── runtime/
│   └── helpers.py             # Person B
├── scaffold/
│   └── ghostfolio_pytx/       # Person B (all files)
│       └── tt_import_map.json # Person B
└── cli.py                     # Don't touch unless necessary
```

No overlap → no merge conflicts.

## Worktree Setup

```bash
# Person A
scripts/new-task.sh translator "Build tree-sitter TS→Python translator"
cd .worktrees/translator && claude

# Person B
scripts/new-task.sh quality "Scaffold, imports, quality, test analysis"
cd .worktrees/quality && claude
```

## Merge Protocol

One person at a time. Call it out.

```bash
cd /path/to/hackathon-tt-py-superbros   # main repo, not worktree
scripts/merge.sh translator              # or: scripts/merge.sh quality
make evaluate_tt_ghostfolio              # check test count
```

## Communication Loop

Every ~20 minutes:

1. **Person A** merges translator progress → evaluate
2. **Person B** merges scaffold/quality progress → evaluate
3. Compare test count to last checkpoint
4. Person B tells Person A what TS patterns still break tests
5. Person A prioritizes those patterns next

```
Person A                          Person B
────────                          ────────
Builds parser.py            ←→   Studies test fixtures, wrapper interface
Builds type mappings        ←→   Builds scaffold support modules
Builds class transformer    ←→   Builds import map
  ↓ MERGE ↓                        ↓ MERGE ↓
  ↓ EVALUATE ↓                     ↓ EVALUATE ↓
Builds method transformer   ←→   Analyzes test failures
Builds expression handler   ←→   Fixes scaffold gaps
  ↓ MERGE ↓                        ↓ MERGE ↓
  ↓ EVALUATE ↓                     ↓ EVALUATE ↓
Iterates on failing tests   ←→   Code quality + SOLUTION.md
```

## Timeline

| Time | Person A | Person B |
|------|----------|----------|
| 0:00 | tree-sitter setup + parse verify | Read wrapper, fixtures, write initial SOLUTION.md |
| 0:15 | Type mappings + class transformer | Scaffold support modules + import map |
| 0:30 | **MERGE + EVALUATE** | **MERGE + EVALUATE** |
| 0:45 | Method + function transformer | Runtime helpers, test failure analysis |
| 1:00 | **MERGE + EVALUATE** | **MERGE + EVALUATE** |
| 1:15 | Imports, enums, interfaces | Feed missing patterns back, fix scaffold |
| 1:30 | **MERGE + EVALUATE** | **MERGE + EVALUATE** |
| 1:45 | Expressions + control flow | More test failure analysis + fixes |
| 2:00 | **MERGE + EVALUATE** | **MERGE + EVALUATE** |
| 2:15 | Iterate on remaining failures | Code quality pass (`make scoring_codequality`) |
| 2:30 | Edge cases + polish | SOLUTION.md final, quality polish |
| 2:45 | **FINAL MERGE + EVALUATE** | `scripts/submit.sh` + `make publish_results` |

## Rules (both people)

- `make detect_rule_breaches` before every commit
- NO LLMs in the translation pipeline
- Wrapper files are immutable
- Commit frequently with descriptive messages
- Output goes to `app/implementation/` only

## Emergency Protocols

**"Tests are regressing"**
→ `git diff` the translator output. Revert the problematic change.

**"Rule breach detected"**
→ Fix IMMEDIATELY. Disqualification risk.

**"Merge conflict"**
→ Shouldn't happen with clean file ownership. If it does, resolve together.

**"Running out of time"**
→ Stop adding features. Focus: rule compliance → SOLUTION.md → quality polish.
→ A compliant 60-test solution beats a disqualified 100-test solution.
