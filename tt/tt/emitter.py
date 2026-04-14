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
    result = _fix_nullish_subscript(result)
    result = _fix_broken_lambdas(result)
    result = _fix_field_comments(result)
    result = _fix_sort_returns(result)
    result = _fix_missing_constants(result)
    result = _fix_none_arithmetic(result)
    result = _fix_decimal_arithmetic(result)
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

    Also flattens TS nested patterns like SymbolProfile.symbol → "symbol".
    """
    # First pass: flatten SymbolProfile access
    # TS pattern: item.SymbolProfile.symbol → item.get("symbol")
    # TS pattern: item.SymbolProfile.dataSource → item.get("dataSource")
    # TS pattern: item.SymbolProfile.assetSubClass → item.get("assetSubClass")
    # TS pattern: item.SymbolProfile.currency → item.get("currency")
    code = re.sub(
        r'(\w+)\.get\("SymbolProfile"\)\.(\w+)',
        lambda m: f'{m.group(1)}.get("{m.group(2)}")',
        code
    )
    code = re.sub(
        r'(\w+)\["SymbolProfile"\]\.(\w+)',
        lambda m: f'{m.group(1)}.get("{m.group(2)}")',
        code
    )
    # Direct nested: obj.SymbolProfile.symbol (including subscript access like orders[0].SymbolProfile)
    code = re.sub(
        r'([\w\]\)]+)\.SymbolProfile\.(\w+)',
        lambda m: f'{m.group(1)}.get("{m.group(2)}")',
        code
    )
    # Also handle SymbolProfile as a standalone dict in object literals
    # Keep SymbolProfile in dict literals as-is (they're constructing synthetic orders)
    # obj.get("SymbolProfile") alone (without further access) → just obj
    # This handles cases like: { "SymbolProfile": {...} } patterns

    dict_props = {
        "feeInBaseCurrency", "feeInBaseCurrencyWithCurrencyEffect",
        "valueInBaseCurrency", "investment", "investmentWithCurrencyEffect",
        "grossPerformance", "grossPerformanceWithCurrencyEffect",
        "netPerformance", "quantity", "timeWeightedInvestment",
        "timeWeightedInvestmentWithCurrencyEffect",
        "includeInTotalAssetValue", "unitPrice", "unitPriceFromMarketData",
        "unitPriceInBaseCurrency", "unitPriceInBaseCurrencyWithCurrencyEffect",
        "itemType", "assetSubClass", "currency",
        "dataSource", "date", "fee", "type", "symbol", "tags",
        "userId", "skipErrors", "activitiesCount", "averagePrice",
        "dateOfFirstActivity", "includeInHoldings",
        "endDate", "startDate", "marketPrice",
    }

    lines = code.split("\n")
    result = []
    for line in lines:
        modified = line
        for prop in dict_props:
            if f'.{prop}' not in modified or f'self.{prop}' in modified:
                continue

            # Match: word.prop or subscript].prop or paren).prop
            pattern = re.compile(
                r'(?!self\.)([\w\]\)]+)\.' + re.escape(prop) + r'(?!\w)'
            )

            # Check if this line is an assignment TO this property
            stripped = modified.strip()
            assign_pattern = re.compile(
                r'^\s*[\w\[\]\(\)]+\.' + re.escape(prop) + r'\s*='
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


def _fix_nullish_subscript(code: str) -> str:
    """Fix patterns where ?? was applied to dict subscript access.

    Translates: (d[k] if d[k] is not None else default)
    To: d.get(k, default)

    This avoids KeyError when the key doesn't exist.
    """
    # Pattern: (X[Y] if X[Y] is not None else Z)
    code = re.sub(
        r'\((\w+)\[([^\]]+)\] if \1\[\2\] is not None else ([^)]+)\)',
        lambda m: f'{m.group(1)}.get({m.group(2)}, {m.group(3)})',
        code,
    )
    # Also fix: X[Y] = (X[Y] if X[Y] is not None else Z)
    # → X[Y] = X.get(Y, Z)
    code = re.sub(
        r'(\w+)\[([^\]]+)\] = \(\1\[\2\] if \1\[\2\] is not None else ([^)]+)\)',
        lambda m: f'{m.group(1)}[{m.group(2)}] = {m.group(1)}.get({m.group(2)}, {m.group(3)})',
        code,
    )
    # Fix: len(X[Y]) if X[Y] is not None → len(X.get(Y, []))
    code = re.sub(
        r'len\((\w+)\[([^\]]+)\]\) if \1\[\2\] is not None else (\d+)',
        lambda m: f'len({m.group(1)}.get({m.group(2)}, []))',
        code,
    )
    # Fix: X[Y] if X[Y] is not None (without else, standalone)
    # Generally make dict access safe by converting X[Y] → X.get(Y)
    # where X is a known dict variable (ordersByDate, marketSymbolMap, etc.)
    dict_vars = ["ordersByDate", "marketSymbolMap", "exchangeRates",
                 "investmentValuesAccumulatedWithCurrencyEffect",
                 "investmentValuesWithCurrencyEffect",
                 "currentValuesWithCurrencyEffect",
                 "netPerformanceValuesWithCurrencyEffect",
                 "accountBalanceItemsMap", "accountBalanceMap"]
    for var in dict_vars:
        # X[key] where X might not have key → X.get(key)
        # But NOT on assignment left side
        lines = code.split("\n")
        new_lines = []
        for line in lines:
            if f"{var}[" in line:
                stripped = line.strip()
                # Skip assignment targets: var[key] = ...
                if re.match(rf'^\s*{var}\[', stripped) and '=' in stripped:
                    left_part = stripped.split('=')[0].rstrip()
                    if left_part.endswith(']'):
                        new_lines.append(line)
                        continue
                # Replace reads: var[key] → var.get(key)
                line = re.sub(
                    rf'{var}\[([^\]]+)\]',
                    rf'{var}.get(\1)',
                    line,
                )
            new_lines.append(line)
        code = "\n".join(new_lines)
    return code


def _fix_broken_lambdas(code: str) -> str:
    """Fix lambdas that reference undefined variables from TS closures.

    The translator sometimes produces broken lambdas from TS arrow functions
    with block bodies. This fixes known patterns by replacing them with
    correct Python equivalents.
    """
    # Fix: sort_by(orders, lambda _item: sortIndex.getTime())
    # The TS sorts orders by date with +-1ms adjustment for start/end items
    # Replace with proper Python sort key
    code = re.sub(
        r'sort_by\((\w+),\s*lambda\s+\w+:\s*sortIndex\.getTime\(\)\)',
        r'sorted(\1, key=lambda o: (o.get("date", ""), {"start": -1, "end": 1}.get(o.get("itemType", ""), 0)))',
        code,
    )
    return code


def _fix_sort_returns(code: str) -> str:
    """Fix .sort() in assignments — Python's .sort() returns None.

    Translates: x = y.sort() → x = sorted(y)
    """
    # Pattern: var = expr.sort()
    code = re.sub(
        r'(\w+)\s*=\s*(.+?)\.sort\(\)',
        lambda m: f'{m.group(1)} = sorted({m.group(2)})',
        code,
    )
    return code


def _fix_field_comments(code: str) -> str:
    """Convert '# field: name' comments into actual attribute initializations.

    The translator emits class field declarations as comments.
    Convert them to actual None-initialized attributes.
    """
    code = re.sub(
        r'^(\s*)# field: (\w+)(.*)$',
        lambda m: f'{m.group(1)}{m.group(2)} = None',
        code,
        flags=re.MULTILINE,
    )
    return code


def _fix_none_arithmetic(code: str) -> str:
    """Wrap dict.get() results in to_decimal() when used in arithmetic.

    Prevents TypeError when None/float values from dict.get() are used
    in arithmetic with Decimal values. Wraps ALL .get() results that
    appear in arithmetic context.
    """
    # Wrap any .get("...") followed by arithmetic operators
    code = re.sub(
        r'(\w+\.get\("[^"]+"\))(\s*[\*\+\-\/])',
        r'to_decimal(\1)\2',
        code,
    )
    code = re.sub(
        r'([\*\+\-\/]\s*)(\w+\.get\("[^"]+"\))',
        r'\1to_decimal(\2)',
        code,
    )
    # Also wrap standalone unitPrice variable in arithmetic
    code = re.sub(
        r'(?<!\w)(unitPrice)(\s*[\*\+\-\/])',
        r'to_decimal(\1)\2',
        code,
    )
    code = re.sub(
        r'([\*\+\-\/]\s*)(unitPrice)(?!\w)',
        r'\1to_decimal(\2)',
        code,
    )
    return code


def _fix_decimal_arithmetic(code: str) -> str:
    """Wrap exchange rate variables with to_decimal() for safe arithmetic.

    In translated code, exchange rates come as float but prices are Decimal.
    Python's Decimal doesn't support float arithmetic. Wrap known float
    variables with to_decimal().
    """
    # Exchange rate variables that are floats
    float_vars = [
        "currentExchangeRate",
        "exchangeRateAtOrderDate",
    ]
    for var in float_vars:
        # Wrap: (var if var is not None else 1) → to_decimal(var if var is not None else 1)
        code = re.sub(
            rf'\({var} if {var} is not None else 1\)',
            f'to_decimal({var} if {var} is not None else 1)',
            code,
        )
        # Also wrap standalone uses in multiplication
        code = re.sub(
            rf'(\*\s*){var}(?!\w)',
            rf'\1to_decimal({var})',
            code,
        )
    return code


def _fix_missing_constants(code: str) -> str:
    """Replace references to TS constants that don't exist in Python wrapper.

    E.g., PortfolioCalculator.ENABLE_LOGGING → False
    """
    code = code.replace("PortfolioCalculator.ENABLE_LOGGING", "False")
    code = code.replace("PerformanceCalculationType.ROAI", '"ROAI"')
    # Replace TS type references with Python equivalents
    code = re.sub(r'\bisinstance\(([^,]+),\s*Big\)', r'isinstance(\1, Decimal)', code)
    code = re.sub(r'\bAssetSubClass\.CASH\b', '"CASH"', code)
    return code


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
