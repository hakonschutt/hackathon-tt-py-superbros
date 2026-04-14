"""CLI entry point for the ``tt`` TypeScript-to-Python translation tool.

Provides the ``tt translate`` sub-command which sets up the scaffold
directory and then runs the regex-based translator over the TypeScript
source files.
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path

log = logging.getLogger(__name__)

REPO_ROOT: Path = Path(__file__).parent.parent.parent.resolve()
TRANSLATION_DIR: Path = REPO_ROOT / "translations" / "ghostfolio_pytx"


def _setup_scaffold(output_dir: Path) -> bool:
    """Run the scaffold setup script.

    Returns ``True`` on success, ``False`` if the script is missing or
    the subprocess fails.
    """
    setup_script = REPO_ROOT / "helptools" / "setup_ghostfolio_scaffold_for_tt.py"
    if not setup_script.exists():
        log.error("Setup script not found: %s", setup_script)
        return False

    log.info("Setting up scaffold -> %s", output_dir)
    subprocess.run(
        [sys.executable, str(setup_script), "--output", str(output_dir)],
        check=True,
    )
    return True


def cmd_translate(args: argparse.Namespace) -> int:
    """Run the full translation pipeline: scaffold setup then TS-to-Python."""
    output_dir = Path(args.output) if args.output else TRANSLATION_DIR

    if not _setup_scaffold(output_dir):
        return 1

    log.info("Translating TypeScript to Python...")
    from tt.translator import run_translation

    run_translation(REPO_ROOT, output_dir)

    log.info("Done. Output at %s", output_dir)
    return 0


def main() -> int:
    """Parse CLI arguments and dispatch to the appropriate sub-command."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    parser = argparse.ArgumentParser(
        prog="tt",
        description="TypeScript-to-Python translation tool",
    )
    sub = parser.add_subparsers(dest="command")

    p_translate = sub.add_parser("translate", help="Translate TypeScript to Python")
    p_translate.add_argument("-o", "--output", help="Output directory")

    args = parser.parse_args()
    if args.command == "translate":
        return cmd_translate(args)

    parser.print_help()
    return 0
