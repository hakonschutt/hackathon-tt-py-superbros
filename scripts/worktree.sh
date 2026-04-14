#!/usr/bin/env bash
set -euo pipefail

# Worktree management for hackathon parallel work
# Usage:
#   scripts/worktree.sh create <name>   — create worktree + branch for a task
#   scripts/worktree.sh list            — list all active worktrees
#   scripts/worktree.sh remove <name>   — remove a worktree (keeps branch)
#   scripts/worktree.sh go <name>       — print the path (use: cd $(scripts/worktree.sh go <name>))

REPO_ROOT="$(git -C "$(dirname "$0")/.." rev-parse --show-toplevel)"
WORKTREE_DIR="$REPO_ROOT/.worktrees"
INCLUDE_FILE="$REPO_ROOT/.worktreeinclude"

usage() {
    echo "Usage: $0 {create|list|remove|go} [name]"
    echo ""
    echo "Commands:"
    echo "  create <name>   Create a new worktree for a task"
    echo "  list            List all active worktrees"
    echo "  remove <name>   Remove a worktree (branch is kept)"
    echo "  go <name>       Print worktree path"
    echo ""
    echo "Examples:"
    echo "  $0 create improve-class-translation"
    echo "  cd \$($0 go improve-class-translation)"
    echo "  $0 remove improve-class-translation"
    exit 1
}

create_worktree() {
    local name="$1"
    local branch="task/$name"
    local wt_path="$WORKTREE_DIR/$name"

    if [ -d "$wt_path" ]; then
        echo "Error: Worktree '$name' already exists at $wt_path"
        exit 1
    fi

    mkdir -p "$WORKTREE_DIR"

    echo "Creating worktree '$name' on branch '$branch'..."
    git worktree add -b "$branch" "$wt_path" HEAD

    # Copy env files into worktree
    if [ -f "$REPO_ROOT/.env" ]; then
        cp "$REPO_ROOT/.env" "$wt_path/.env"
        echo "Copied .env"
    fi

    # Copy any files listed in .worktreeinclude
    if [ -f "$INCLUDE_FILE" ]; then
        while IFS= read -r pattern; do
            [[ -z "$pattern" || "$pattern" == \#* ]] && continue
            for f in $REPO_ROOT/$pattern; do
                if [ -f "$f" ]; then
                    local rel="${f#$REPO_ROOT/}"
                    mkdir -p "$wt_path/$(dirname "$rel")"
                    cp "$f" "$wt_path/$rel"
                    echo "Copied $rel"
                fi
            done
        done < "$INCLUDE_FILE"
    fi

    # Configure git hooks in worktree
    if [ -d "$REPO_ROOT/.githooks" ]; then
        git -C "$wt_path" config core.hooksPath .githooks
        echo "Configured git hooks"
    fi

    # Sync deps for the tt project
    echo "Installing dependencies..."
    (cd "$wt_path/tt" && uv sync --quiet 2>/dev/null) || true

    echo ""
    echo "Worktree ready at: $wt_path"
    echo "Branch: $branch"
    echo ""
    echo "Next steps:"
    echo "  cd $wt_path"
    echo "  claude  # start coding"
    echo ""
    echo "When done:"
    echo "  scripts/merge.sh $name"
}

list_worktrees() {
    echo "Active worktrees:"
    echo ""
    git worktree list
    echo ""

    if [ -d "$WORKTREE_DIR" ]; then
        echo "Task worktrees in $WORKTREE_DIR:"
        for d in "$WORKTREE_DIR"/*/; do
            if [ -d "$d" ]; then
                local name="$(basename "$d")"
                local branch="$(git -C "$d" branch --show-current 2>/dev/null || echo "unknown")"
                local commits="$(git -C "$d" log main..HEAD --oneline 2>/dev/null | wc -l | tr -d ' ')"
                echo "  $name (branch: $branch, $commits commits ahead)"
            fi
        done
    else
        echo "No task worktrees created yet."
    fi
}

remove_worktree() {
    local name="$1"
    local wt_path="$WORKTREE_DIR/$name"

    if [ ! -d "$wt_path" ]; then
        echo "Error: Worktree '$name' not found at $wt_path"
        exit 1
    fi

    # Check for uncommitted changes
    if [ -n "$(git -C "$wt_path" status --porcelain)" ]; then
        echo "Warning: Worktree '$name' has uncommitted changes!"
        echo ""
        git -C "$wt_path" status --short
        echo ""
        read -p "Remove anyway? (y/N) " confirm
        if [[ "$confirm" != [yY] ]]; then
            echo "Aborted."
            exit 1
        fi
    fi

    echo "Removing worktree '$name'..."
    git worktree remove "$wt_path" --force
    echo "Done. Branch 'task/$name' is still available."
}

go_worktree() {
    local name="$1"
    local wt_path="$WORKTREE_DIR/$name"

    if [ ! -d "$wt_path" ]; then
        echo "Error: Worktree '$name' not found" >&2
        exit 1
    fi

    echo "$wt_path"
}

# Main
[[ $# -lt 1 ]] && usage

case "$1" in
    create)
        [[ $# -lt 2 ]] && { echo "Error: name required"; usage; }
        create_worktree "$2"
        ;;
    list)
        list_worktrees
        ;;
    remove)
        [[ $# -lt 2 ]] && { echo "Error: name required"; usage; }
        remove_worktree "$2"
        ;;
    go)
        [[ $# -lt 2 ]] && { echo "Error: name required"; usage; }
        go_worktree "$2"
        ;;
    *)
        usage
        ;;
esac
