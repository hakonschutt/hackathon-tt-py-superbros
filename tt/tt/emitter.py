"""Python code emitter — assembles translated fragments into valid Python files.

Handles indentation, import deduplication, empty body insertion, and formatting.
"""
from __future__ import annotations

import re


def build_python_file(
    class_code: str,
    imports: list[str] | None = None,
    module_docstring: str | None = None,
) -> str:
    """Assemble a complete Python file from translated components.

    Args:
        class_code: The translated class/function code.
        imports: List of import statements.
        module_docstring: Optional module-level docstring.

    Returns:
        A complete, formatted Python source string.
    """
    parts: list[str] = []

    # Module docstring
    if module_docstring:
        parts.append(f'"""{module_docstring}"""')

    parts.append("from __future__ import annotations")
    parts.append("")

    # Imports
    if imports:
        seen: set[str] = set()
        for imp in sorted(imports):
            imp = imp.strip()
            if imp and imp not in seen:
                seen.add(imp)
                parts.append(imp)
        parts.append("")

    # Main code
    parts.append(class_code)

    result = "\n".join(parts)

    # Post-processing: fix common issues
    result = _fix_empty_bodies(result)
    result = _fix_indentation(result)
    result = _collapse_blank_lines(result)

    # Ensure trailing newline
    if not result.endswith("\n"):
        result += "\n"

    return result


def _fix_empty_bodies(code: str) -> str:
    """Insert 'pass' into empty function/class bodies."""
    lines = code.split("\n")
    result = []
    for i, line in enumerate(lines):
        result.append(line)
        stripped = line.rstrip()
        if stripped.endswith(":") and not stripped.startswith("#"):
            # Check if next non-blank line is at same or lower indent
            indent = len(line) - len(line.lstrip())
            next_content = None
            for j in range(i + 1, len(lines)):
                if lines[j].strip():
                    next_content = lines[j]
                    break
            if next_content is None:
                result.append(" " * (indent + 4) + "pass")
            else:
                next_indent = len(next_content) - len(next_content.lstrip())
                if next_indent <= indent:
                    result.append(" " * (indent + 4) + "pass")
    return "\n".join(result)


def _fix_indentation(code: str) -> str:
    """Ensure consistent 4-space indentation."""
    lines = code.split("\n")
    result = []
    for line in lines:
        if line.strip():
            # Replace tabs with 4 spaces
            line = line.replace("\t", "    ")
        result.append(line)
    return "\n".join(result)


def _collapse_blank_lines(code: str) -> str:
    """Collapse 3+ consecutive blank lines to 2."""
    return re.sub(r"\n{4,}", "\n\n\n", code)
