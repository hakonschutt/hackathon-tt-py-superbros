#!/usr/bin/env bash
set -euo pipefail

# Merge a worktree branch back to main
# Usage: scripts/merge.sh <name> [--no-delete]
#
# Handles lockfile conflicts automatically:
# - Auto-resolves uv.lock conflicts by regenerating with `uv lock`

REPO_ROOT="$(git -C "$(dirname "$0")/.." rev-parse --show-toplevel)"
WORKTREE_DIR="$REPO_ROOT/.worktrees"

usage() {
    echo "Usage: $0 <name> [--no-delete]"
    echo ""
    echo "Merges task/<name> branch into main, runs checks, and cleans up."
    echo "Lockfile conflicts (uv.lock) are resolved automatically."
    echo ""
    echo "Options:"
    echo "  --no-delete   Keep the worktree after merging"
    exit 1
}

[[ $# -lt 1 ]] && usage

NAME="$1"
NO_DELETE=false
[[ "${2:-}" == "--no-delete" ]] && NO_DELETE=true

BRANCH="task/$NAME"
WT_PATH="$WORKTREE_DIR/$NAME"

# Ensure we're on main in the main repo
cd "$REPO_ROOT"

CURRENT_BRANCH="$(git branch --show-current)"
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "Error: Must be on 'main' branch to merge. Currently on '$CURRENT_BRANCH'."
    exit 1
fi

# Auto-stash uncommitted changes
STASHED=false
if [ -n "$(git status --porcelain)" ]; then
    echo "Stashing uncommitted changes on main..."
    git stash push -m "merge.sh: auto-stash before merging $BRANCH"
    STASHED=true
fi

# Check the worktree branch for uncommitted changes
if [ -d "$WT_PATH" ] && [ -n "$(git -C "$WT_PATH" status --porcelain)" ]; then
    echo "Error: Worktree '$NAME' has uncommitted changes."
    echo "Go commit them first: cd $WT_PATH"
    if [ "$STASHED" = true ]; then git stash pop; fi
    exit 1
fi

# Check branch exists
if ! git rev-parse --verify "$BRANCH" &>/dev/null; then
    echo "Error: Branch '$BRANCH' does not exist."
    if [ "$STASHED" = true ]; then git stash pop; fi
    exit 1
fi

echo "=== Merging $BRANCH into main ==="
echo ""

# Show what will be merged
COMMITS="$(git log main.."$BRANCH" --oneline)"
if [ -z "$COMMITS" ]; then
    echo "No commits to merge. Branch is up to date with main."
    if [ "$STASHED" = true ]; then git stash pop; fi
    exit 0
fi

echo "Commits to merge:"
echo "$COMMITS"
echo ""

# Attempt merge
if git merge "$BRANCH" --no-ff -m "Merge $BRANCH into main"; then
    echo "Merge completed cleanly."
else
    echo ""
    echo "Merge has conflicts. Attempting auto-resolution..."

    # Auto-resolve lockfile conflicts (always safe to regenerate)
    for lockfile in $(git diff --name-only --diff-filter=U | grep -E '(uv\.lock|\.lock)$' || true); do
        echo "  Auto-resolving $lockfile (will regenerate)"
        git checkout --ours "$lockfile"
        git add "$lockfile"
    done

    # Check if there are remaining conflicts
    REMAINING="$(git diff --name-only --diff-filter=U || true)"
    if [ -n "$REMAINING" ]; then
        echo ""
        echo "Remaining conflicts need manual resolution:"
        echo "$REMAINING"
        echo ""
        echo "Resolve them, then run:"
        echo "  git add -A && git commit"
    else
        git commit --no-edit
        echo "All conflicts auto-resolved."
    fi
fi

# Regenerate lockfiles after merge
echo ""
echo "Syncing dependencies..."
TOUCHED_DIRS="$(git diff HEAD~1 --name-only | grep 'pyproject.toml' | xargs -I{} dirname {} | sort -u || true)"
if [ -n "$TOUCHED_DIRS" ]; then
    for dir in $TOUCHED_DIRS; do
        if [ -f "$dir/pyproject.toml" ]; then
            echo "  uv lock in $dir/"
            (cd "$dir" && uv lock --quiet 2>/dev/null && uv sync --quiet 2>/dev/null) || true
        fi
    done
fi

# Restore stashed changes
if [ "$STASHED" = true ]; then
    git stash pop 2>/dev/null || true
fi

# Run rule breach check
echo ""
echo "Checking rule compliance..."
if make detect_rule_breaches 2>/dev/null; then
    echo "No rule breaches detected."
else
    echo "WARNING: Rule breaches detected. Review before pushing."
fi

# Clean up worktree
if [ "$NO_DELETE" = false ] && [ -d "$WT_PATH" ]; then
    echo ""
    echo "Removing worktree..."
    git worktree remove "$WT_PATH" --force
    echo "Worktree removed. Branch '$BRANCH' kept for reference."
fi

echo ""
echo "=== Merge complete ==="
echo ""
echo "Next: run 'make evaluate_tt_ghostfolio' to check test results."
