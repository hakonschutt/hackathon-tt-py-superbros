#!/usr/bin/env bash
set -euo pipefail

# Pre-submission checklist — run before final submit
# Usage: scripts/submit.sh

REPO_ROOT="$(git -C "$(dirname "$0")/.." rev-parse --show-toplevel)"
cd "$REPO_ROOT"

echo "=== Pre-Submission Checklist ==="
echo ""

PASS=0
FAIL=0

check() {
    local label="$1"
    shift
    if "$@" >/dev/null 2>&1; then
        echo "  [PASS] $label"
        PASS=$((PASS + 1))
    else
        echo "  [FAIL] $label"
        FAIL=$((FAIL + 1))
    fi
}

# Git state
echo "## Git"
check "No uncommitted changes" test -z "$(git status --porcelain)"
check "On main branch" test "$(git branch --show-current)" = "main"
check "No unmerged worktrees" bash -c '[ ! -d .worktrees ] || [ -z "$(ls -A .worktrees 2>/dev/null)" ]'
echo ""

# Rule compliance
echo "## Rule Compliance"
check "No rule breaches" make detect_rule_breaches
echo ""

# SOLUTION.md
echo "## Documentation"
check "SOLUTION.md has content" bash -c '[ "$(wc -w < SOLUTION.md)" -gt 50 ]'
echo ""

# Translation + Tests
echo "## Translation & Tests"
echo "  Running full evaluation..."
EVAL_OUTPUT="$(make evaluate_tt_ghostfolio 2>&1 || true)"
echo "$EVAL_OUTPUT" | tail -20
echo ""

# Summary
echo "================================"
echo "  $PASS passed, $FAIL failed"
echo "================================"

if [ "$FAIL" -gt 0 ]; then
    echo ""
    echo "Fix failures before submitting!"
    echo "Remember: reset main to your final commit before 18:30."
    exit 1
else
    echo ""
    echo "All checks passed!"
    echo ""
    echo "Final steps:"
    echo "  1. Verify SOLUTION.md explains your approach"
    echo "  2. Run: make publish_results"
    echo "  3. Reset main to your final commit if needed"
fi
