"""Minimal TypeScript-to-Python translator.

Reads TypeScript source files from the Ghostfolio project and applies
regex-based transformations to produce Python equivalents.  Complex
methods that cannot be reliably translated are left as stubs from the
example scaffold.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

log = logging.getLogger(__name__)


def translate_typescript_file(ts_content: str) -> str:
    """Apply regex-based TS-to-Python transformations to *ts_content*.

    Handles class declarations, method signatures, enum return
    statements, closing braces, and blank-line cleanup.
    """
    python_code = ts_content

    # Remove TypeScript imports (we'll add Python imports separately)
    python_code = re.sub(r"^import\s+.*?;?\s*$", "", python_code, flags=re.MULTILINE)

    # Translate class declarations: class Name extends Base { -> class Name(Base):
    python_code = re.sub(
        r"export\s+class\s+(\w+)\s+extends\s+(\w+)\s*\{",
        r"class \1(\2):",
        python_code,
    )

    # Translate method definitions: protected methodName() { -> def methodName(self):
    python_code = re.sub(
        r"(protected|private|public)?\s*(\w+)\s*\([^)]*\)\s*\{",
        lambda m: f"def {m.group(2)}(self):",
        python_code,
    )

    # Translate return statements with enum values
    python_code = re.sub(
        r"return\s+(\w+)\.(\w+);",
        r'return "\2"',
        python_code,
    )

    # Remove closing braces
    python_code = re.sub(r"^\s*\}\s*$", "", python_code, flags=re.MULTILINE)

    # Clean up multiple blank lines
    python_code = re.sub(r"\n\s*\n\s*\n+", "\n\n", python_code)

    return python_code.strip()


def _extract_perf_type_method(ts_content: str) -> str | None:
    """Extract the ``getPerformanceCalculationType`` method body from *ts_content*.

    Returns the raw TypeScript method text, or ``None`` if it cannot be
    located.
    """
    match = re.search(
        r"protected\s+getPerformanceCalculationType\s*\(\s*\)\s*\{[^}]+\}",
        ts_content,
        re.DOTALL,
    )
    return match.group(0) if match else None


def _indent_block(text: str) -> str:
    """Indent every non-blank line of *text* by four spaces."""
    return "\n".join(
        "    " + line if line.strip() else line for line in text.split("\n")
    )


def translate_roai_calculator(
    ts_file: Path, output_file: Path, stub_file: Path
) -> None:
    """Translate the ROAI portfolio calculator from TypeScript to Python.

    Reads the TypeScript source, translates simple methods via regex, and
    merges the result into the stub implementation for methods that are
    too complex for automated translation.
    """
    ts_content = ts_file.read_text(encoding="utf-8")
    stub_content = stub_file.read_text(encoding="utf-8")

    ts_method = _extract_perf_type_method(ts_content)
    if ts_method:
        py_method = _indent_block(translate_typescript_file(ts_method))
        translated_section = (
            "    # --- Translated from TypeScript ---\n" + py_method + "\n"
            "    # --- End translated section ---\n"
        )

        lines = stub_content.split("\n")
        for i in range(len(lines) - 1, 0, -1):
            if lines[i].strip().startswith("def "):
                lines.insert(i, translated_section)
                break

        output_content = "\n".join(lines)
    else:
        output_content = stub_content

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(output_content, encoding="utf-8")


def run_translation(repo_root: Path, output_dir: Path) -> None:
    """Execute the full translation pipeline.

    Locates the TypeScript ROAI calculator source and the example stub,
    then delegates to :func:`translate_roai_calculator` for the actual
    translation.
    """
    ts_source = (
        repo_root
        / "projects"
        / "ghostfolio"
        / "apps"
        / "api"
        / "src"
        / "app"
        / "portfolio"
        / "calculator"
        / "roai"
        / "portfolio-calculator.ts"
    )

    stub_source = (
        repo_root
        / "translations"
        / "ghostfolio_pytx_example"
        / "app"
        / "implementation"
        / "portfolio"
        / "calculator"
        / "roai"
        / "portfolio_calculator.py"
    )

    output_file = (
        output_dir
        / "app"
        / "implementation"
        / "portfolio"
        / "calculator"
        / "roai"
        / "portfolio_calculator.py"
    )

    if not ts_source.exists():
        log.warning("TypeScript source not found: %s", ts_source)
        return

    if not stub_source.exists():
        log.warning("Stub file not found: %s", stub_source)
        return

    log.info("Translating %s...", ts_source.name)
    translate_roai_calculator(ts_source, output_file, stub_file=stub_source)
    log.info("  Translated -> %s", output_file)
