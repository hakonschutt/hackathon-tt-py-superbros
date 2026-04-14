#!/usr/bin/env bash
set -euo pipefail

# Quick status overview of the entire hackathon workspace
# Usage: scripts/status.sh

REPO_ROOT="$(git -C "$(dirname "$0")/.." rev-parse --show-toplevel)"
WORKTREE_DIR="$REPO_ROOT/.worktrees"

echo "=== TT Hackathon Status ==="
echo ""

# Main branch status
echo "## Main branch"
MAIN_BRANCH="$(git -C "$REPO_ROOT" branch --show-current)"
MAIN_STATUS="$(git -C "$REPO_ROOT" status --porcelain)"
COMMIT_COUNT="$(git -C "$REPO_ROOT" log --oneline | wc -l | tr -d ' ')"

echo "  Branch: $MAIN_BRANCH"
echo "  Commits: $COMMIT_COUNT"
if [ -z "$MAIN_STATUS" ]; then
    echo "  Status: clean"
else
    echo "  Status: dirty ($(echo "$MAIN_STATUS" | wc -l | tr -d ' ') files changed)"
fi
echo ""

# Worktrees
echo "## Worktrees"
if [ -d "$WORKTREE_DIR" ] && [ "$(ls -A "$WORKTREE_DIR" 2>/dev/null)" ]; then
    for d in "$WORKTREE_DIR"/*/; do
        [ -d "$d" ] || continue
        name="$(basename "$d")"
        branch="$(git -C "$d" branch --show-current 2>/dev/null || echo "detached")"
        status="$(git -C "$d" status --porcelain 2>/dev/null)"
        commits="$(git -C "$d" log main..HEAD --oneline 2>/dev/null | wc -l | tr -d ' ')"

        if [ -z "$status" ]; then
            state="clean"
        else
            state="dirty ($(echo "$status" | wc -l | tr -d ' ') files)"
        fi

        echo "  $name"
        echo "    Branch: $branch | Commits ahead: $commits | $state"
    done
else
    echo "  (none)"
fi
echo ""

# Rule compliance
echo "## Rule compliance"
cd "$REPO_ROOT"
if make detect_rule_breaches --quiet 2>/dev/null; then
    echo "  Rules: ok"
else
    echo "  Rules: BREACHES DETECTED"
fi
echo ""

echo "## Quick test (run 'make evaluate_tt_ghostfolio' for full eval)"
echo "  Tip: track test count after each change to measure progress"
echo ""

echo "=== Done ==="
