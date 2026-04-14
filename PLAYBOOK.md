# Competition Day Playbook — Superbros TT

## Team: 2 people
- **Person A (Orchestrator)**: Reads requirements, plans translation strategy, directs agents, reviews output
- **Person B (Executor)**: Runs parallel Claude instances, handles integration, monitors test results

Both run Claude Code. Both can have multiple terminal tabs.

---

## Pre-Game Setup (do before 15:15)

```bash
# Clone the repo (or ensure it's up to date)
cd /path/to/hackathon-tt-py-superbros

# Run setup
scripts/setup.sh

# Open 4 terminal tabs
# Tab 1: Main working directory (orchestrator)
# Tab 2-4: Ready for worktrees
```

Ensure both people have:
- [ ] Claude Code running and authenticated
- [ ] `uv sync` completed in `tt/`
- [ ] `make evaluate_tt_ghostfolio` runs and shows baseline (~48 passing tests)
- [ ] Read COMPETITION_RULES.md

---

## Phase 1: Understand the Problem (15:15 - 15:45) — BOTH PEOPLE

**STOP. Read and understand before coding.**

1. Read COMPETITION_RULES.md together
2. Read the TypeScript source being translated:
   ```bash
   # Person A: explore the main calculator
   claude "@explorer Analyze projects/ghostfolio/apps/api/src/app/portfolio/calculator/"
   
   # Person B: explore the reference Python output
   claude "@explorer Analyze translations/ghostfolio_pytx_example/app/"
   ```
3. Run baseline: `make evaluate_tt_ghostfolio` — note which tests pass/fail
4. Understand the gap: ~48 pass from scaffold, ~87 need real translation
5. Categorize failing tests by what they need:
   - Performance calculations
   - Chart history
   - Holdings/investments
   - Dividends/fees
   - Report evaluation

### Key questions to answer:
- What TypeScript constructs are used most? (classes, generics, enums, interfaces?)
- What's the most impactful thing to translate first?
- What's the translation pipeline structure?

---

## Phase 2: Plan & Assign (15:45 - 16:00)

Decide strategy based on the TypeScript analysis:

### Translation Pipeline Architecture

The translator needs to handle:
1. **Class/inheritance translation** → Python classes
2. **Method signatures** → Python methods with self
3. **Type annotations** → Python type hints
4. **Expressions** → Python operators, optional chaining, etc.
5. **Imports** → Python import mapping
6. **Enums/interfaces** → Python enums/protocols

### Splitting Work

| Person A | Person B |
|----------|----------|
| Core class/method translation | Type system translation (enums, interfaces) |
| Expression handling | Import mapping & module structure |
| Calculator-specific logic | Scaffold support modules |

**Rule: Each person owns their translation aspect end-to-end.**

---

## Phase 3: Build (16:00 - 17:15) — HEADS DOWN

### Iteration loop (every 15-20 minutes)

```bash
# 1. Make translator changes in tt/tt/
# 2. Translate
uv run --project tt tt translate
# 3. Test
make spinup-and-test-ghostfolio_pytx
# 4. Note new test count
# 5. Check rules
make detect_rule_breaches
# 6. Commit if progress
git add -A && git commit -m "tt: [what improved]"
```

### Parallel Workflow

```bash
# Person A (Tab 1):
scripts/new-task.sh class-translation "Improve class/method translation"
cd .worktrees/class-translation && claude

# Person B (Tab 2):
scripts/new-task.sh type-translation "Handle TypeScript types/enums/interfaces"
cd .worktrees/type-translation && claude

# Merge when ready:
scripts/merge.sh class-translation
scripts/merge.sh type-translation
```

### Key Rules During Build Phase
- Run `make evaluate_tt_ghostfolio` after EVERY merge — track test count
- Run `make detect_rule_breaches` before every commit
- Commit frequently with descriptive messages (judges check git log)
- If stuck for >10 minutes, move to next translation pattern, come back later

---

## Phase 4: Integrate & Verify (17:15 - 17:30)

```bash
# Merge all worktrees
scripts/merge.sh [name]

# Full evaluation
make evaluate_tt_ghostfolio

# Rule check
make detect_rule_breaches

# Track: how many tests pass now?
```

---

## Phase 5: Polish & Optimize (17:30 - 18:15)

Priority order:
1. **Fix regressions** — any tests that stopped passing
2. **Target easy wins** — tests closest to passing
3. **Code quality** — run `make scoring_codequality`, improve pyscn score
4. **SOLUTION.md** — explain approach, architecture, decisions
5. **Clean up** — type hints, docstrings, remove dead code in `tt/tt/`

```bash
# Run polisher agent
claude "@polisher Polish the translator for final submission"

# Check quality score
make scoring_codequality
```

---

## Phase 6: Final Submission (18:15 - 18:30)

```bash
# Run full pre-submission check
scripts/submit.sh

# Publish results
make publish_results

# Ensure SOLUTION.md is complete
# Ensure main branch has your final commit
```

Checklist:
- [ ] `make detect_rule_breaches` passes
- [ ] `make evaluate_tt_ghostfolio` shows best test count
- [ ] SOLUTION.md explains approach clearly
- [ ] All work committed to main
- [ ] Results published: `make publish_results`

---

## Emergency Protocols

### "Tests are regressing"
→ `git diff` to see what changed. Revert the problematic translator change.
→ Translation is tricky — a fix for one test can break others.

### "Rule breach detected"
→ Fix IMMEDIATELY. Rule violations can disqualify.
→ Common issues: LLM calls, project-specific logic in tt/ core, wrapper modification.

### "We're running out of time"
→ Stop adding translation patterns. Focus on: rules clean > SOLUTION.md > quality polish.
→ A rule-compliant 60-test solution beats a disqualified 100-test solution.

### "Generated code is garbage"
→ Step back. Read the TypeScript more carefully.
→ Consider: is regex enough, or do you need AST-based translation?
→ The example tt uses regex — you may need something more sophisticated.

---

## Quick Reference

```bash
# Evaluate everything
make evaluate_tt_ghostfolio

# Just translate
uv run --project tt tt translate

# Just test
make spinup-and-test-ghostfolio_pytx

# Rule check
make detect_rule_breaches

# Quality score
make scoring_codequality

# Publish
make publish_results

# Status
scripts/status.sh

# Submit check
scripts/submit.sh
```
