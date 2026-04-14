#!/usr/bin/env bash
set -euo pipefail

# Quick-start a new task: creates worktree, prints commands to begin
# Usage: scripts/new-task.sh <name> [prompt]
#
# Examples:
#   scripts/new-task.sh class-translation
#   scripts/new-task.sh class-translation "Improve class and method translation in tt"

REPO_ROOT="$(git -C "$(dirname "$0")/.." rev-parse --show-toplevel)"

usage() {
    echo "Usage: $0 <name> [prompt]"
    echo ""
    echo "Creates a worktree and prints the commands to start working."
    echo ""
    echo "Examples:"
    echo "  $0 class-translation"
    echo "  $0 class-translation \"Improve class/method translation\""
    exit 1
}

[[ $# -lt 1 ]] && usage

NAME="$1"
PROMPT="${2:-}"

# Create the worktree
"$REPO_ROOT/scripts/worktree.sh" create "$NAME"

WT_PATH="$REPO_ROOT/.worktrees/$NAME"

echo ""
echo "=============================="
echo "Run these commands to start:"
echo "=============================="
echo ""
echo "  cd $WT_PATH"

if [ -n "$PROMPT" ]; then
    echo "  claude \"$PROMPT\""
else
    echo "  claude"
fi
echo ""
