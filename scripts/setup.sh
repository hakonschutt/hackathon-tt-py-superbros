#!/usr/bin/env bash
set -euo pipefail

echo "=== Superbros TT Hackathon Setup ==="

REPO_ROOT="$(git -C "$(dirname "$0")/.." rev-parse --show-toplevel)"
cd "$REPO_ROOT"

# Install uv if not present
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    echo "uv installed: $(uv --version)"
else
    echo "uv already installed: $(uv --version)"
fi

# Install tt project dependencies
echo "Installing tt dependencies..."
(cd tt && uv sync)

# Install translated project dependencies (for testing)
if [ -d "translations/ghostfolio_pytx_example" ]; then
    echo "Installing example project dependencies..."
    (cd translations/ghostfolio_pytx_example && uv sync 2>/dev/null) || true
fi

# Configure git hooks
if [ -d ".githooks" ]; then
    git config core.hooksPath .githooks
    echo "Configured git hooks"
fi

# Verify the baseline works
echo ""
echo "Running baseline evaluation..."
echo "(This translates with the example tt and runs tests)"
if make evaluate_tt_ghostfolio 2>/dev/null; then
    echo "Baseline evaluation complete."
else
    echo "Note: baseline evaluation had issues — check output above."
fi

echo ""
echo "=== Setup complete! ==="
echo ""
echo "Next steps:"
echo "  1. Read COMPETITION_RULES.md and README.md"
echo "  2. Read PLAYBOOK.md for competition-day strategy"
echo "  3. Read AGENTS.md for project conventions"
echo "  4. Explore the TypeScript source: projects/ghostfolio/"
echo "  5. Run: make evaluate_tt_ghostfolio  (to see baseline test results)"
