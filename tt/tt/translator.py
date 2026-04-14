"""Tree-sitter based TypeScript-to-Python translation pipeline.

Orchestrates: parse TS → walk AST → transform nodes → emit Python.
This is the core of the tt translation tool.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from tt.parser import parse_file, parse_source, get_node_text
from tt.node_visitor import NodeVisitor
from tt.emitter import build_python_file
from tt.interface_gen import generate_interface_adapter

log = logging.getLogger(__name__)

# Standard imports for the translated calculator
CALCULATOR_IMPORTS = [
    "import copy",
    "import math",
    "from datetime import datetime, date, timedelta",
    "from decimal import Decimal, ROUND_HALF_UP, InvalidOperation",
    "from typing import Any",
    "",
    "from app.wrapper.portfolio.calculator.portfolio_calculator import PortfolioCalculator",
    "from app.implementation.helpers import *",
]


def translate_ts_file(ts_path: Path, import_map: dict | None = None) -> str:
    """Translate a single TypeScript file to Python source.

    Args:
        ts_path: Path to the TypeScript source file.
        import_map: Optional import mapping configuration.

    Returns:
        Translated Python source code as a string.
    """
    tree = parse_file(ts_path)
    visitor = NodeVisitor(import_map=import_map)
    translated = visitor.visit(tree.root_node)
    return translated


def translate_roai_calculator(
    roai_ts: Path,
    base_ts: Path,
    import_map: dict | None = None,
) -> str:
    """Translate the ROAI portfolio calculator from TypeScript to Python.

    Parses both the ROAI calculator and its base class, translates the
    relevant methods, and assembles them into a single Python class.

    Args:
        roai_ts: Path to the ROAI calculator TypeScript file.
        base_ts: Path to the base PortfolioCalculator TypeScript file.
        import_map: Optional import mapping configuration.

    Returns:
        Complete Python source code for the translated calculator.
    """
    log.info("Translating ROAI calculator: %s", roai_ts.name)

    # Parse and translate the ROAI calculator (the class with internal methods)
    roai_code = translate_ts_file(roai_ts, import_map)

    # Parse the base class to understand methods and generate interface adapters
    base_tree = parse_file(base_ts)
    interface_code = generate_interface_adapter(base_tree, roai_ts)

    # Combine: translated internal methods + generated interface adapters
    lines = roai_code.split("\n")
    insert_idx = len(lines)
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip():
            insert_idx = i + 1
            break

    lines.insert(insert_idx, interface_code)
    combined = "\n".join(lines)

    # Build the final Python file
    python_source = build_python_file(
        class_code=combined,
        imports=CALCULATOR_IMPORTS,
        module_docstring="ROAI Portfolio Calculator -- translated from TypeScript by tt.",
    )

    return python_source


def run_translation(repo_root: Path, output_dir: Path) -> None:
    """Run the full translation pipeline.

    Args:
        repo_root: Root of the repository.
        output_dir: Output directory for translated files.
    """
    # Source TypeScript files
    roai_ts = (
        repo_root / "projects" / "ghostfolio" / "apps" / "api" / "src"
        / "app" / "portfolio" / "calculator" / "roai" / "portfolio-calculator.ts"
    )
    base_ts = (
        repo_root / "projects" / "ghostfolio" / "apps" / "api" / "src"
        / "app" / "portfolio" / "calculator" / "portfolio-calculator.ts"
    )

    # Import map
    scaffold_dir = repo_root / "tt" / "tt" / "scaffold" / "ghostfolio_pytx"
    import_map_path = scaffold_dir / "tt_import_map.json"
    import_map = {}
    if import_map_path.exists():
        import_map = json.loads(import_map_path.read_text(encoding="utf-8"))

    # Output path
    output_file = (
        output_dir / "app" / "implementation" / "portfolio" / "calculator"
        / "roai" / "portfolio_calculator.py"
    )

    if not roai_ts.exists():
        log.warning("TypeScript source not found: %s", roai_ts)
        return

    # Translate
    python_source = translate_roai_calculator(roai_ts, base_ts, import_map)

    # Write output
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(python_source, encoding="utf-8")
    log.info("Translated -> %s", output_file)

    print(f"  Translated {roai_ts.name} -> {output_file}")
