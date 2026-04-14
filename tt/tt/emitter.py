"""Python code emitter — assembles translated fragments into valid Python files.

Handles indentation, import deduplication, empty body insertion,
and attribute-to-dict-access conversion for translated TS code.
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
    result = _convert_attribute_to_dict_access(result)
    result = _fix_empty_bodies(result)
    result = _fix_indentation(result)
    result = _collapse_blank_lines(result)

    # Ensure trailing newline
    if not result.endswith("\n"):
        result += "\n"

    return result


def _convert_attribute_to_dict_access(code: str) -> str:
    """Convert attribute access on dict-like objects to dict-style access.

    In translated code, TS object property access (obj.prop) becomes
    Python dict access. Assignment targets use obj["prop"] = val,
    while reads use obj.get("prop").
    """
    dict_props = {
        "feeInBaseCurrency", "feeInBaseCurrencyWithCurrencyEffect",
        "valueInBaseCurrency", "investment", "investmentWithCurrencyEffect",
        "grossPerformance", "grossPerformanceWithCurrencyEffect",
        "netPerformance", "quantity", "timeWeightedInvestment",
        "timeWeightedInvestmentWithCurrencyEffect",
        "includeInTotalAssetValue", "unitPrice", "unitPriceFromMarketData",
        "unitPriceInBaseCurrency", "unitPriceInBaseCurrencyWithCurrencyEffect",
        "SymbolProfile", "itemType", "assetSubClass", "currency",
        "dataSource", "date", "fee", "type", "symbol", "tags",
        "userId", "skipErrors", "activitiesCount", "averagePrice",
        "dateOfFirstActivity", "includeInHoldings",
    }

    lines = code.split("\n")
    result = []
    for line in lines:
        modified = line
        for prop in dict_props:
            if f'.{prop}' not in modified or f'self.{prop}' in modified:
                continue

            pattern = re.compile(
                r'(?<!\w)(?!self\.)(\w+)\.' + re.escape(prop) + r'(?!\w)'
            )

            # Check if this line is an assignment TO this property
            stripped = modified.strip()
            assign_pattern = re.compile(
                r'^\s*\w+\.' + re.escape(prop) + r'\s*='
            )
            if assign_pattern.match(stripped):
                # Assignment target: obj.prop = val → obj["prop"] = val
                modified = pattern.sub(
                    lambda m: f'{m.group(1)}["{prop}"]',
                    modified,
                )
            else:
                # Read access: obj.prop → obj.get("prop")
                modified = pattern.sub(
                    lambda m: f'{m.group(1)}.get("{prop}")',
                    modified,
                )
        result.append(modified)
    return "\n".join(result)


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
