"""Recursive AST visitor that translates TypeScript nodes to Python source.

Walks the tree-sitter AST and dispatches to handler methods based on node type.
Each handler returns a Python source string. This is the core of the translator.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from tree_sitter import Node

from tt.parser import get_node_text

# TypeScript type → Python type mapping
TYPE_MAP: dict[str, str] = {
    "string": "str",
    "number": "float",
    "boolean": "bool",
    "any": "Any",
    "void": "None",
    "null": "None",
    "undefined": "None",
    "never": "None",
    "unknown": "Any",
    "object": "dict",
    "Date": "datetime",
    "Big": "Decimal",
}

# Big.js method → Python operator/function
BIG_METHOD_MAP: dict[str, str] = {
    "plus": "+",
    "add": "+",
    "minus": "-",
    "sub": "-",
    "mul": "*",
    "times": "*",
    "div": "/",
    "eq": "==",
    "gt": ">",
    "lt": "<",
    "gte": ">=",
    "lte": "<=",
}

# date-fns function translations
DATE_FN_MAP: dict[str, str] = {
    "differenceInDays": "difference_in_days",
    "isBefore": "is_before",
    "isAfter": "is_after",
    "format": "format_date",
    "addMilliseconds": "add_milliseconds",
    "startOfDay": "start_of_day",
    "endOfDay": "end_of_day",
    "startOfYear": "start_of_year",
    "endOfYear": "end_of_year",
    "eachDayOfInterval": "each_day_of_interval",
    "eachYearOfInterval": "each_year_of_interval",
    "isWithinInterval": "is_within_interval",
    "isThisYear": "is_this_year",
    "subDays": "sub_days",
    "min": "min_date",
    "parseDate": "parse_date",
    "resetHours": "reset_hours",
}

# lodash function translations
LODASH_MAP: dict[str, str] = {
    "cloneDeep": "copy.deepcopy",
    "sortBy": "sort_by",
    "uniqBy": "uniq_by",
    "isNumber": "is_number",
    "sum": "sum",
}

# Helper function translations (camelCase → snake_case)
HELPER_FN_MAP: dict[str, str] = {
    "getFactor": "get_factor",
    "getIntervalFromDateRange": "get_interval_from_date_range",
    "getSum": "sum",
}


class NodeVisitor:
    """Translates tree-sitter TypeScript AST nodes to Python source code."""

    def __init__(self, import_map: dict[str, str | None] | None = None) -> None:
        self.import_map = import_map or {}
        self.imports: list[str] = []
        self.indent_level: int = 0
        self._class_name: str = ""
        self._parent_class: str = ""
        self._in_class: bool = False
        self._collected_fields: list[dict] = []

    def visit(self, node: Node) -> str:
        """Visit a node and return Python source."""
        method_name = f"visit_{node.type.replace('-', '_')}"
        visitor = getattr(self, method_name, None)
        if visitor:
            return visitor(node)
        return self._visit_children(node)

    def _visit_children(self, node: Node) -> str:
        """Default: visit all children and join results."""
        parts = []
        for child in node.children:
            result = self.visit(child)
            if result:
                parts.append(result)
        return "\n".join(parts)

    def _indent(self) -> str:
        return "    " * self.indent_level

    # ── Program / Module ─────────────────────────────────────────────

    def visit_program(self, node: Node) -> str:
        """Top-level program node."""
        parts = []
        for child in node.children:
            if child.type == "import_statement":
                # Skip TS imports — we generate Python imports
                self._collect_import(child)
                continue
            result = self.visit(child)
            if result and result.strip():
                parts.append(result)
        return "\n\n".join(parts)

    # ── Imports ──────────────────────────────────────────────────────

    def _collect_import(self, node: Node) -> None:
        """Collect import information for later Python import generation."""
        # We handle imports via the import_map and generated headers
        pass

    # ── Class ────────────────────────────────────────────────────────

    def visit_class_declaration(self, node: Node) -> str:
        return self._translate_class(node)

    def visit_export_statement(self, node: Node) -> str:
        """Handle 'export class ...', 'export function ...' etc."""
        for child in node.children:
            if child.type in ("class_declaration", "function_declaration",
                              "lexical_declaration"):
                return self.visit(child)
        return ""

    def _translate_class(self, node: Node) -> str:
        name_node = node.child_by_field_name("name")
        self._class_name = get_node_text(name_node) if name_node else "UnknownClass"

        # Find parent class
        heritage = None
        for child in node.children:
            if child.type == "class_heritage":
                heritage = child
                break

        if heritage:
            for child in heritage.children:
                if child.type == "extends_clause":
                    for c in child.children:
                        if c.type in ("identifier", "type_identifier"):
                            self._parent_class = get_node_text(c)

        parent = f"({self._parent_class})" if self._parent_class else ""
        header = f"class {self._class_name}{parent}:"

        self._in_class = True
        self._collected_fields = []
        self.indent_level = 1

        body_node = node.child_by_field_name("body")
        body_parts = []
        if body_node:
            for child in body_node.children:
                if child.type in ("{", "}"):
                    continue
                result = self.visit(child)
                if result and result.strip():
                    body_parts.append(result)

        self._in_class = False
        self.indent_level = 0

        if not body_parts:
            body_parts = [f"    pass"]

        return header + "\n" + "\n\n".join(body_parts)

    # ── Methods / Functions ──────────────────────────────────────────

    def visit_method_definition(self, node: Node) -> str:
        return self._translate_method(node)

    def visit_function_declaration(self, node: Node) -> str:
        return self._translate_function(node)

    def _translate_method(self, node: Node) -> str:
        name_node = node.child_by_field_name("name")
        name = get_node_text(name_node) if name_node else "unknown"

        # Convert camelCase to snake_case? No — keep original names for now
        # The wrapper expects specific method names

        params = self._translate_params(node)
        return_type = self._get_return_type(node)

        ret_annotation = f" -> {return_type}" if return_type else ""

        if self._in_class:
            if name == "constructor":
                sig = f"{self._indent()}def __init__(self, {params}){ret_annotation}:"
            else:
                param_str = f"self, {params}" if params else "self"
                sig = f"{self._indent()}def {name}({param_str}){ret_annotation}:"
        else:
            sig = f"{self._indent()}def {name}({params}){ret_annotation}:"

        body = self._translate_body(node)
        if not body.strip():
            body = f"{self._indent()}    pass"

        return sig + "\n" + body

    def _translate_function(self, node: Node) -> str:
        name_node = node.child_by_field_name("name")
        name = get_node_text(name_node) if name_node else "unknown"
        params = self._translate_params(node)
        return_type = self._get_return_type(node)
        ret_annotation = f" -> {return_type}" if return_type else ""

        sig = f"{self._indent()}def {name}({params}){ret_annotation}:"
        body = self._translate_body(node)
        if not body.strip():
            body = f"{self._indent()}    pass"
        return sig + "\n" + body

    def _translate_params(self, node: Node) -> str:
        """Extract and translate function parameters."""
        params_node = node.child_by_field_name("parameters")
        if not params_node:
            return ""

        params = []
        for child in params_node.children:
            if child.type in ("(", ")", ","):
                continue
            if child.type in ("required_parameter", "optional_parameter"):
                param = self._translate_param(child)
                if param:
                    params.append(param)
        return ", ".join(params)

    def _translate_param(self, node: Node) -> str:
        """Translate a single parameter."""
        name = ""
        type_ann = ""
        default = ""
        is_optional = node.type == "optional_parameter"
        destructured_names = []

        for child in node.children:
            if child.type == "identifier":
                name = get_node_text(child)
            elif child.type == "object_pattern":
                # Destructured parameter: { a, b, c }
                for c in child.children:
                    if c.type == "shorthand_property_identifier_pattern":
                        destructured_names.append(get_node_text(c))
                    elif c.type == "pair_pattern":
                        for cc in c.children:
                            if cc.type in ("identifier", "shorthand_property_identifier_pattern"):
                                destructured_names.append(get_node_text(cc))
                                break
            elif child.type == "type_annotation":
                type_ann = self._translate_type_annotation(child)
            elif child.type == "?":
                is_optional = True
            elif child.type == "=":
                continue
            elif child.type not in ("accessibility_modifier", "readonly"):
                # Could be default value
                if name:
                    default = self._translate_expression(child)

        # Handle destructured parameters — use **kwargs style or named params
        if destructured_names:
            # Convert to individual named parameters
            return ", ".join(destructured_names)

        # Skip 'this' keyword parameters (TS constructor shorthand)
        if name == "this":
            return ""

        # Remove 'private', 'public', 'protected' from param names
        result = name
        if type_ann:
            result += f": {type_ann}"
        if default:
            result += f" = {default}"
        elif is_optional and not default:
            result += " = None"
        return result

    def _get_return_type(self, node: Node) -> str:
        """Get the return type annotation."""
        for child in node.children:
            if child.type == "type_annotation":
                return self._translate_type_annotation(child)
        return ""

    def _translate_type_annotation(self, node: Node) -> str:
        """Translate a type annotation node."""
        for child in node.children:
            if child.type == ":":
                continue
            return self._translate_type(child)
        return ""

    def _translate_type(self, node: Node) -> str:
        """Translate a type node to Python type hint."""
        if node.type == "predefined_type":
            ts_type = get_node_text(node)
            return TYPE_MAP.get(ts_type, ts_type)

        if node.type == "type_identifier":
            ts_type = get_node_text(node)
            return TYPE_MAP.get(ts_type, ts_type)

        if node.type == "generic_type":
            name_node = node.child_by_field_name("name") or node.children[0]
            name = get_node_text(name_node)
            args = []
            for child in node.children:
                if child.type == "type_arguments":
                    for tc in child.children:
                        if tc.type not in ("<", ">", ","):
                            args.append(self._translate_type(tc))

            mapped = TYPE_MAP.get(name, name)
            if name == "Array":
                return f"list[{args[0]}]" if args else "list"
            if name == "Record":
                return f"dict[{', '.join(args)}]" if args else "dict"
            if name == "Promise":
                return args[0] if args else "Any"
            if name == "Map":
                return f"dict[{', '.join(args)}]" if args else "dict"
            if name == "Set":
                return f"set[{args[0]}]" if args else "set"
            if args:
                return f"{mapped}[{', '.join(args)}]"
            return mapped

        if node.type == "union_type":
            types = []
            for child in node.children:
                if child.type != "|":
                    t = self._translate_type(child)
                    types.append(t)
            # T | null → Optional[T]
            non_none = [t for t in types if t != "None"]
            has_none = len(non_none) < len(types)
            if has_none and len(non_none) == 1:
                return f"{non_none[0]} | None"
            return " | ".join(types)

        if node.type == "intersection_type":
            # Just use the first type
            for child in node.children:
                if child.type != "&":
                    return self._translate_type(child)

        if node.type == "object_type":
            return "dict"

        if node.type == "array_type":
            for child in node.children:
                if child.type not in ("[", "]"):
                    inner = self._translate_type(child)
                    return f"list[{inner}]"
            return "list"

        if node.type == "parenthesized_type":
            for child in node.children:
                if child.type not in ("(", ")"):
                    return self._translate_type(child)

        if node.type == "literal_type":
            return get_node_text(node)

        if node.type == "function_type":
            return "Callable"

        if node.type == "index_type_query":
            return "str"

        return get_node_text(node)

    # ── Statements ───────────────────────────────────────────────────

    def _translate_body(self, node: Node) -> str:
        """Translate a function/method body (statement_block)."""
        body_node = node.child_by_field_name("body")
        if not body_node:
            return f"{self._indent()}    pass"

        old_indent = self.indent_level
        self.indent_level += 1
        lines = self._translate_statements(body_node)
        self.indent_level = old_indent

        if not lines.strip():
            return f"{self._indent()}    pass"
        return lines

    def _translate_statements(self, node: Node) -> str:
        """Translate a block of statements."""
        parts = []
        for child in node.children:
            if child.type in ("{", "}"):
                continue
            result = self._translate_statement(child)
            if result is not None and result.strip():
                parts.append(result)
        return "\n".join(parts)

    def _translate_statement(self, node: Node) -> str:
        """Translate a single statement."""
        # Handle comments first
        if node.type == "comment":
            return self.visit_comment(node)

        handler = getattr(self, f"_stmt_{node.type}", None)
        if handler:
            return handler(node)

        # Expression statements
        if node.type == "expression_statement":
            return self._stmt_expression_statement(node)

        # Default: try to translate as expression
        expr = self._translate_expression(node)
        if expr:
            return f"{self._indent()}{expr}"
        return ""

    def _stmt_expression_statement(self, node: Node) -> str:
        for child in node.children:
            if child.type == ";":
                continue
            expr = self._translate_expression(child)
            if expr:
                return f"{self._indent()}{expr}"
        return ""

    def _stmt_lexical_declaration(self, node: Node) -> str:
        """Handle let/const declarations."""
        parts = []
        for child in node.children:
            if child.type == "variable_declarator":
                parts.append(self._translate_variable_declarator(child))
        return "\n".join(parts)

    def _stmt_variable_declaration(self, node: Node) -> str:
        return self._stmt_lexical_declaration(node)

    def _translate_variable_declarator(self, node: Node) -> str:
        name_node = node.child_by_field_name("name")
        value_node = node.child_by_field_name("value")

        if not name_node:
            return ""

        # Handle destructuring
        if name_node.type == "object_pattern":
            return self._translate_object_destructuring(name_node, value_node)
        if name_node.type == "array_pattern":
            return self._translate_array_destructuring(name_node, value_node)

        name = get_node_text(name_node)
        # Strip type annotation from name if present
        type_ann = ""
        for child in node.children:
            if child.type == "type_annotation":
                type_ann = self._translate_type_annotation(child)

        if value_node:
            value = self._translate_expression(value_node)
            if type_ann:
                return f"{self._indent()}{name}: {type_ann} = {value}"
            return f"{self._indent()}{name} = {value}"
        else:
            if type_ann:
                return f"{self._indent()}{name}: {type_ann} = None"
            return f"{self._indent()}{name} = None"

    def _translate_object_destructuring(self, pattern: Node, value_node: Node | None) -> str:
        """Translate const { a, b } = expr."""
        names = []
        for child in pattern.children:
            if child.type == "shorthand_property_identifier_pattern":
                names.append(get_node_text(child))
            elif child.type == "pair_pattern":
                # { key: alias }
                key = None
                val = None
                for c in child.children:
                    if c.type == "property_identifier":
                        key = get_node_text(c)
                    elif c.type == "identifier":
                        val = get_node_text(c)
                if val:
                    names.append(val)
                elif key:
                    names.append(key)

        if not value_node:
            return ""

        value = self._translate_expression(value_node)
        lines = []
        for n in names:
            lines.append(f"{self._indent()}{n} = {value}[\"{n}\"]" if "." not in value
                         else f"{self._indent()}{n} = {value}.{n}")
        # Use simpler attribute access if value looks like an object
        # Actually, use dict access since TS objects map to Python dicts
        result_lines = []
        for n in names:
            result_lines.append(f"{self._indent()}{n} = {value}.get(\"{n}\")")
        return "\n".join(result_lines)

    def _translate_array_destructuring(self, pattern: Node, value_node: Node | None) -> str:
        """Translate const [a, b] = expr."""
        names = []
        for child in pattern.children:
            if child.type == "identifier":
                names.append(get_node_text(child))
            elif child.type not in ("[", "]", ","):
                names.append(get_node_text(child))
        if not value_node:
            return ""
        value = self._translate_expression(value_node)
        return f"{self._indent()}{', '.join(names)} = {value}"

    def _stmt_return_statement(self, node: Node) -> str:
        for child in node.children:
            if child.type in ("return", ";"):
                continue
            expr = self._translate_expression(child)
            return f"{self._indent()}return {expr}"
        return f"{self._indent()}return"

    def _stmt_if_statement(self, node: Node) -> str:
        condition = node.child_by_field_name("condition")
        consequence = node.child_by_field_name("consequence")
        alternative = node.child_by_field_name("alternative")

        cond = self._translate_expression(condition) if condition else "True"
        # Remove outer parens from condition
        cond = cond.strip()
        if cond.startswith("(") and cond.endswith(")"):
            cond = cond[1:-1]

        result = f"{self._indent()}if {cond}:"

        if consequence:
            old_indent = self.indent_level
            self.indent_level += 1
            body = self._translate_statements(consequence) if consequence.type == "statement_block" else self._translate_statement(consequence)
            self.indent_level = old_indent
            if not body.strip():
                body = f"{self._indent()}    pass"
            result += "\n" + body

        if alternative:
            # alternative is an else_clause node
            for child in alternative.children:
                if child.type == "if_statement":
                    # else if → elif
                    elif_result = self._stmt_if_statement(child)
                    # Replace the first "if" with "elif"
                    elif_result = elif_result.replace(f"{self._indent()}if ", f"{self._indent()}elif ", 1)
                    result += "\n" + elif_result
                elif child.type == "statement_block":
                    result += f"\n{self._indent()}else:"
                    old_indent = self.indent_level
                    self.indent_level += 1
                    body = self._translate_statements(child)
                    self.indent_level = old_indent
                    if not body.strip():
                        body = f"{self._indent()}    pass"
                    result += "\n" + body
                elif child.type not in ("else",):
                    result += f"\n{self._indent()}else:"
                    old_indent = self.indent_level
                    self.indent_level += 1
                    body = self._translate_statement(child)
                    self.indent_level = old_indent
                    result += "\n" + body

        return result

    def _stmt_for_statement(self, node: Node) -> str:
        """Translate C-style for loop."""
        init = node.child_by_field_name("initializer")
        cond = node.child_by_field_name("condition")
        update = node.child_by_field_name("increment")
        body = node.child_by_field_name("body")

        # Try to detect for (let i = 0; i < N; i++) pattern
        init_text = get_node_text(init).strip() if init else ""
        cond_text = get_node_text(cond).strip().rstrip(";") if cond else ""
        update_text = get_node_text(update).strip() if update else ""

        # Simple for-i loop detection
        m_init = re.match(r'(?:let|const|var)\s+(\w+)\s*=\s*(\d+)', init_text)
        m_cond = re.match(r'(\w+)\s*<\s*(.+)', cond_text)
        m_update = re.match(r'(\w+)\s*\+\+|(\w+)\s*\+=\s*1', update_text)

        if m_init and m_cond:
            var = m_init.group(1)
            start = m_init.group(2)
            end_expr = self._translate_expression(cond.children[-1]) if cond else m_cond.group(2)
            # Check for step
            step_match = re.match(r'(\w+)\s*\+=\s*(\d+)', update_text)
            if step_match and step_match.group(2) != "1":
                step = step_match.group(2)
                range_expr = f"range({start}, {end_expr}, {step})" if start != "0" else f"range(0, {end_expr}, {step})"
            else:
                range_expr = f"range({end_expr})" if start == "0" else f"range({start}, {end_expr})"

            result = f"{self._indent()}for {var} in {range_expr}:"
        else:
            # Fallback: while loop
            if init:
                init_stmt = self._translate_statement(init)
            else:
                init_stmt = ""
            cond_expr = self._translate_expression(cond) if cond else "True"
            result = ""
            if init_stmt:
                result += init_stmt + "\n"
            result += f"{self._indent()}while {cond_expr}:"

        if body:
            old_indent = self.indent_level
            self.indent_level += 1
            body_str = self._translate_statements(body) if body.type == "statement_block" else self._translate_statement(body)
            if update and not (m_init and m_cond):
                update_str = self._translate_expression(update)
                body_str += f"\n{self._indent()}{update_str}"
            self.indent_level = old_indent
            if not body_str.strip():
                body_str = f"{self._indent()}    pass"
            result += "\n" + body_str

        return result

    def _stmt_for_in_statement(self, node: Node) -> str:
        """Translate for...of / for...in loops."""
        left = node.child_by_field_name("left")
        right = node.child_by_field_name("right")
        body = node.child_by_field_name("body")
        kind = node.child_by_field_name("kind")

        var_name = ""
        if left:
            # Could be destructuring pattern or identifier
            if left.type in ("identifier",):
                var_name = get_node_text(left)
            elif left.type == "object_pattern":
                names = []
                for child in left.children:
                    if child.type == "shorthand_property_identifier_pattern":
                        names.append(get_node_text(child))
                var_name = ", ".join(names) if names else "_"
            elif left.type == "array_pattern":
                names = []
                for child in left.children:
                    if child.type == "identifier":
                        names.append(get_node_text(child))
                var_name = ", ".join(names)
            else:
                # Look for identifier child
                for child in left.children:
                    if child.type == "identifier":
                        var_name = get_node_text(child)
                        break
                    elif child.type == "object_pattern":
                        names = []
                        for c in child.children:
                            if c.type == "shorthand_property_identifier_pattern":
                                names.append(get_node_text(c))
                        var_name = ", ".join(names)
                        break
                if not var_name:
                    var_name = get_node_text(left).strip().split()[-1]

        iterable = self._translate_expression(right) if right else "[]"

        # Determine if it's for...of (iterate values) or for...in (iterate keys)
        is_of = False
        for child in node.children:
            if child.type == "of":
                is_of = True
                break

        if not is_of:
            # for...in → iterate keys
            iterable = f"{iterable}"

        result = f"{self._indent()}for {var_name} in {iterable}:"

        if body:
            old_indent = self.indent_level
            self.indent_level += 1
            body_str = self._translate_statements(body) if body.type == "statement_block" else self._translate_statement(body)
            self.indent_level = old_indent
            if not body_str.strip():
                body_str = f"{self._indent()}    pass"
            result += "\n" + body_str

        return result

    def _stmt_switch_statement(self, node: Node) -> str:
        """Translate switch/case to if/elif/else."""
        value = node.child_by_field_name("value")
        body = node.child_by_field_name("body")

        switch_val = self._translate_expression(value) if value else ""

        cases = []
        if body:
            for child in body.children:
                if child.type == "switch_case":
                    cases.append(("case", child))
                elif child.type == "switch_default":
                    cases.append(("default", child))

        if not cases:
            return f"{self._indent()}pass  # empty switch"

        result_parts = []
        for i, (kind, case_node) in enumerate(cases):
            if kind == "case":
                case_value = None
                for child in case_node.children:
                    if child.type not in ("case", ":", "comment"):
                        if case_value is None and child.type != "expression_statement":
                            case_value = self._translate_expression(child)
                            break

                keyword = "if" if i == 0 else "elif"
                result_parts.append(f"{self._indent()}{keyword} {switch_val} == {case_value}:")
            else:
                result_parts.append(f"{self._indent()}else:")

            old_indent = self.indent_level
            self.indent_level += 1
            body_parts = []
            found_body = False
            for child in case_node.children:
                if child.type in ("case", "default", ":"):
                    found_body = True
                    continue
                if not found_body:
                    continue
                if child.type == "break_statement":
                    continue
                stmt = self._translate_statement(child)
                if stmt and stmt.strip():
                    body_parts.append(stmt)
            self.indent_level = old_indent

            if not body_parts:
                result_parts.append(f"{self._indent()}    pass")
            else:
                result_parts.extend(body_parts)

        return "\n".join(result_parts)

    def _stmt_try_statement(self, node: Node) -> str:
        body = node.child_by_field_name("body")
        handler = node.child_by_field_name("handler")
        finalizer = node.child_by_field_name("finalizer")

        result = f"{self._indent()}try:"
        if body:
            old_indent = self.indent_level
            self.indent_level += 1
            body_str = self._translate_statements(body)
            self.indent_level = old_indent
            if not body_str.strip():
                body_str = f"{self._indent()}    pass"
            result += "\n" + body_str

        if handler:
            param = ""
            for child in handler.children:
                if child.type == "identifier":
                    param = get_node_text(child)
            exc_clause = f" as {param}" if param else ""
            result += f"\n{self._indent()}except Exception{exc_clause}:"
            body_node = handler.child_by_field_name("body")
            if body_node:
                old_indent = self.indent_level
                self.indent_level += 1
                body_str = self._translate_statements(body_node)
                self.indent_level = old_indent
                if not body_str.strip():
                    body_str = f"{self._indent()}    pass"
                result += "\n" + body_str
            else:
                result += f"\n{self._indent()}    pass"

        if finalizer:
            result += f"\n{self._indent()}finally:"
            old_indent = self.indent_level
            self.indent_level += 1
            body_str = self._translate_statements(finalizer)
            self.indent_level = old_indent
            if not body_str.strip():
                body_str = f"{self._indent()}    pass"
            result += "\n" + body_str

        return result

    def _stmt_throw_statement(self, node: Node) -> str:
        for child in node.children:
            if child.type not in ("throw", ";"):
                expr = self._translate_expression(child)
                return f"{self._indent()}raise Exception({expr})"
        return f"{self._indent()}raise Exception()"

    def _stmt_continue_statement(self, node: Node) -> str:
        return f"{self._indent()}continue"

    def _stmt_break_statement(self, node: Node) -> str:
        return f"{self._indent()}break"

    def _stmt_while_statement(self, node: Node) -> str:
        condition = node.child_by_field_name("condition")
        body = node.child_by_field_name("body")
        cond = self._translate_expression(condition) if condition else "True"
        if cond.startswith("(") and cond.endswith(")"):
            cond = cond[1:-1]
        result = f"{self._indent()}while {cond}:"
        if body:
            old_indent = self.indent_level
            self.indent_level += 1
            body_str = self._translate_statements(body) if body.type == "statement_block" else self._translate_statement(body)
            self.indent_level = old_indent
            if not body_str.strip():
                body_str = f"{self._indent()}    pass"
            result += "\n" + body_str
        return result

    # ── Expressions ──────────────────────────────────────────────────

    def _translate_expression(self, node: Node) -> str:
        """Translate an expression node to Python."""
        if node is None:
            return ""

        handler = getattr(self, f"_expr_{node.type}", None)
        if handler:
            return handler(node)

        # Fallback: raw text with basic cleanup
        text = get_node_text(node)
        return self._basic_cleanup(text)

    def _basic_cleanup(self, text: str) -> str:
        """Basic TS→Python text cleanup."""
        text = text.rstrip(";")
        # Strip inline comments
        text = re.sub(r'//[^\n]*', '', text)
        text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
        # Replace smart quotes
        text = text.replace("\u2019", "'").replace("\u2018", "'")
        text = text.replace("\u201c", '"').replace("\u201d", '"')
        text = text.replace("this.", "self.")
        text = text.replace("null", "None")
        text = text.replace("undefined", "None")
        text = text.replace("true", "True")
        text = text.replace("false", "False")
        text = text.replace("===", "==")
        text = text.replace("!==", "!=")
        text = text.replace("&&", " and ")
        text = text.replace("||", " or ")
        text = re.sub(r'!(\w)', r'not \1', text)
        text = re.sub(r'new Big\((\d+)\)', r'Decimal("\1")', text)
        text = re.sub(r'new Big\(([^)]+)\)', r'Decimal(str(\1))', text)
        text = re.sub(r'new Date\(\)', 'datetime.now()', text)
        text = re.sub(r'new Date\(([^)]+)\)', r'parse_date(\1)', text)
        # Remove type assertions
        text = re.sub(r'\s+as\s+\w+[\[\]<>,\s\w]*', '', text)
        # Collapse whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _expr_identifier(self, node: Node) -> str:
        text = get_node_text(node)
        if text == "this":
            return "self"
        if text == "null":
            return "None"
        if text == "undefined":
            return "None"
        if text == "true":
            return "True"
        if text == "false":
            return "False"
        if text == "Number":
            return "float"
        if text == "EPSILON":
            return "1e-15"
        return text

    def _expr_property_identifier(self, node: Node) -> str:
        return get_node_text(node)

    def _expr_number(self, node: Node) -> str:
        return get_node_text(node)

    def _expr_string(self, node: Node) -> str:
        text = get_node_text(node)
        # Convert single quotes to double if needed
        return text

    def _expr_true(self, node: Node) -> str:
        return "True"

    def _expr_false(self, node: Node) -> str:
        return "False"

    def _expr_null(self, node: Node) -> str:
        return "None"

    def _expr_this(self, node: Node) -> str:
        return "self"

    def _expr_parenthesized_expression(self, node: Node) -> str:
        for child in node.children:
            if child.type not in ("(", ")"):
                inner = self._translate_expression(child)
                return f"({inner})"
        return "()"

    def _expr_assignment_expression(self, node: Node) -> str:
        left = node.child_by_field_name("left")
        right = node.child_by_field_name("right")
        op = "="
        for child in node.children:
            if child.type in ("=", "+=", "-=", "*=", "/=", "??="):
                op = get_node_text(child)
                if op == "??=":
                    # x ??= val → x = x if x is not None else val
                    left_expr = self._translate_expression(left)
                    right_expr = self._translate_expression(right)
                    return f"{left_expr} = {left_expr} if {left_expr} is not None else {right_expr}"

        left_expr = self._translate_expression(left)
        right_expr = self._translate_expression(right)
        return f"{left_expr} {op} {right_expr}"

    def _expr_augmented_assignment_expression(self, node: Node) -> str:
        return self._expr_assignment_expression(node)

    def _expr_binary_expression(self, node: Node) -> str:
        left = node.child_by_field_name("left")
        right = node.child_by_field_name("right")
        op_node = node.child_by_field_name("operator")

        left_expr = self._translate_expression(left)
        right_expr = self._translate_expression(right)

        op = get_node_text(op_node) if op_node else ""
        # Find operator from children
        if not op:
            for child in node.children:
                if child.type in ("===", "!==", "==", "!=", "<", ">", "<=", ">=",
                                  "+", "-", "*", "/", "%", "&&", "||", "??",
                                  "instanceof", "in", "&", "|", "^", "<<", ">>",
                                  ">>>"):
                    op = get_node_text(child)
                    break

        # Translate operators
        if op == "===":
            op = "=="
        elif op == "!==":
            op = "!="
        elif op == "&&":
            op = "and"
        elif op == "||":
            op = "or"
        elif op == "??":
            return f"({left_expr} if {left_expr} is not None else {right_expr})"
        elif op == "instanceof":
            return f"isinstance({left_expr}, {right_expr})"

        return f"{left_expr} {op} {right_expr}"

    def _expr_unary_expression(self, node: Node) -> str:
        op = ""
        operand = None
        for child in node.children:
            if child.type in ("!", "-", "+", "~", "typeof", "void", "delete"):
                op = get_node_text(child)
            else:
                operand = child

        operand_expr = self._translate_expression(operand) if operand else ""

        if op == "!":
            return f"not {operand_expr}"
        if op == "typeof":
            return f"type({operand_expr}).__name__"
        if op == "void":
            return "None"
        if op == "delete":
            return f"del {operand_expr}"
        return f"{op}{operand_expr}"

    def _expr_update_expression(self, node: Node) -> str:
        """Handle i++, i--, ++i, --i."""
        text = get_node_text(node)
        if "++" in text:
            var = text.replace("++", "").strip()
            var = self._basic_cleanup(var)
            return f"{var} += 1"
        if "--" in text:
            var = text.replace("--", "").strip()
            var = self._basic_cleanup(var)
            return f"{var} -= 1"
        return self._basic_cleanup(text)

    def _expr_ternary_expression(self, node: Node) -> str:
        condition = node.child_by_field_name("condition")
        consequence = node.child_by_field_name("consequence")
        alternative = node.child_by_field_name("alternative")

        cond = self._translate_expression(condition)
        cons = self._translate_expression(consequence)
        alt = self._translate_expression(alternative)

        return f"({cons} if {cond} else {alt})"

    def _expr_call_expression(self, node: Node) -> str:
        func = node.child_by_field_name("function")
        args_node = node.child_by_field_name("arguments")

        func_text = self._translate_expression(func)
        args = self._translate_arguments(args_node)

        # Handle special function calls
        return self._transform_call(func_text, args, node)

    def _translate_arguments(self, node: Node) -> list[str]:
        """Translate argument list."""
        if not node:
            return []
        args = []
        for child in node.children:
            if child.type in ("(", ")", ",", "comment"):
                continue
            expr = self._translate_expression(child)
            if expr and expr.strip():
                args.append(expr)
        return args

    def _transform_call(self, func: str, args: list[str], node: Node) -> str:
        """Transform known function calls to Python equivalents."""
        # Big.js method calls: x.plus(y) → x + y
        for big_method, py_op in BIG_METHOD_MAP.items():
            if func.endswith(f".{big_method}"):
                obj = func[:-len(f".{big_method}")]
                if args:
                    return f"({obj} {py_op} {args[0]})"
                return f"{obj}"

        # .abs() → abs(...)
        if func.endswith(".abs"):
            obj = func[:-4]
            return f"abs({obj})"

        # .toNumber() → float(...)
        if func.endswith(".toNumber"):
            obj = func[:-9]
            return f"float({obj})"

        # .toFixed(n) → round(..., n)
        if func.endswith(".toFixed"):
            obj = func[:-8]
            return f"round(float({obj}), {args[0] if args else 2})"

        # new Big(...) → Decimal(...)
        if func == "Big" or func.endswith(".Big"):
            arg = args[0] if args else "'0'"
            return f"Decimal(str({arg}))"

        # Array methods
        if func.endswith(".push"):
            obj = func[:-5]
            return f"{obj}.append({', '.join(args)})"

        if func.endswith(".includes"):
            obj = func[:-9]
            return f"({args[0]} in {obj})" if args else f"False"

        if func.endswith(".concat"):
            obj = func[:-7]
            return f"{obj} + {args[0]}" if args else obj

        if func.endswith(".findIndex"):
            obj = func[:-10]
            if args:
                arg = args[0]
                # If arg is a lambda, extract its body for the comprehension
                if arg.startswith("lambda ") and ": " in arg:
                    param_part, body_part = arg.split(": ", 1)
                    param = param_part.replace("lambda ", "").strip()
                    return f"next((i for i, {param} in enumerate({obj}) if {body_part}), -1)"
                return f"next((i for i, _fi in enumerate({obj}) if {arg}), -1)"
            return f"-1"

        if func.endswith(".at"):
            obj = func[:-3]
            if args:
                return f"{obj}[{args[0]}]"
            return f"{obj}[-1]"

        if func.endswith(".indexOf"):
            obj = func[:-8]
            if args:
                return f"{obj}.index({args[0]}) if {args[0]} in {obj} else -1"
            return "-1"

        if func.endswith(".join"):
            obj = func[:-5]
            sep = args[0] if args else "''"
            return f"{sep}.join({obj})"

        if func.endswith(".substring"):
            obj = func[:-10]
            if len(args) >= 2:
                return f"{obj}[{args[0]}:{args[1]}]"
            return f"{obj}[{args[0]}:]" if args else obj

        if func.endswith(".startsWith"):
            obj = func[:-11]
            return f"{obj}.startswith({args[0]})" if args else f"False"

        if func.endswith(".endsWith"):
            obj = func[:-9]
            return f"{obj}.endswith({args[0]})" if args else f"False"

        # Object methods
        if func.endswith(".keys") and not args:
            obj = func[:-5]
            return f"list({obj}.keys())"

        if func.endswith(".values") and not args:
            obj = func[:-7]
            return f"list({obj}.values())"

        if func.endswith(".entries") and not args:
            obj = func[:-8]
            return f"list({obj}.items())"

        # console.log → pass (remove)
        if func in ("console.log", "console.warn", "console.error",
                     "Logger.warn", "Logger.debug", "Logger.error"):
            return "pass"

        # date-fns functions
        for ts_fn, py_fn in DATE_FN_MAP.items():
            if func == ts_fn or func.endswith(f".{ts_fn}"):
                return f"{py_fn}({', '.join(args)})"

        # lodash functions
        for ts_fn, py_fn in LODASH_MAP.items():
            if func == ts_fn or func.endswith(f".{ts_fn}"):
                return f"{py_fn}({', '.join(args)})"

        # Helper functions (camelCase → snake_case)
        for ts_fn, py_fn in HELPER_FN_MAP.items():
            if func == ts_fn or func.endswith(f".{ts_fn}"):
                return f"{py_fn}({', '.join(args)})"

        # Array.from, Object.keys, etc.
        if func == "Array.from":
            return f"list({', '.join(args)})"
        if func == "Object.keys":
            return f"list({args[0]}.keys())" if args else "[]"
        if func == "Object.values":
            return f"list({args[0]}.values())" if args else "[]"
        if func == "Object.entries":
            return f"list({args[0]}.items())" if args else "[]"
        if func == "JSON.parse":
            return f"json.loads({', '.join(args)})"
        if func == "JSON.stringify":
            return f"json.dumps({', '.join(args)})"

        # Math functions
        if func == "Math.round":
            return f"round({', '.join(args)})"
        if func == "Math.min":
            return f"min({', '.join(args)})"
        if func == "Math.max":
            return f"max({', '.join(args)})"
        if func == "Math.abs":
            return f"abs({', '.join(args)})"
        if func == "Math.floor":
            return f"int({args[0]})" if args else "0"

        # .filter() → list comprehension
        if func.endswith(".filter"):
            obj = func[:-7]
            if args:
                # If the arg is a lambda, integrate it into the comprehension
                arg = args[0]
                if arg.startswith("lambda ") and ": " in arg:
                    param_part, body_part = arg.split(": ", 1)
                    param = param_part.replace("lambda ", "").strip()
                    if param:
                        return f"[{param} for {param} in {obj} if {body_part}]"
                return f"[_fitem for _fitem in {obj} if {arg}]"
            return obj

        # .map() → list comprehension
        if func.endswith(".map"):
            obj = func[:-4]
            if args:
                arg = args[0]
                if arg.startswith("lambda ") and ": " in arg:
                    param_part, body_part = arg.split(": ", 1)
                    param = param_part.replace("lambda ", "").strip()
                    if param:
                        return f"[{body_part} for {param} in {obj}]"
                return f"[{arg} for _mitem in {obj}]"
            return obj

        # .reduce() — complex, return as-is with note
        if func.endswith(".reduce"):
            obj = func[:-7]
            # Best effort
            return f"functools.reduce({', '.join(args)}, {obj})" if args else obj

        # .sort() / .localeCompare()
        if func.endswith(".sort"):
            obj = func[:-5]
            return f"{obj}.sort()"

        if func.endswith(".localeCompare"):
            obj = func[:-14]
            if args:
                return f"(({obj} > {args[0]}) - ({obj} < {args[0]}))"

        # .find()
        if func.endswith(".find"):
            obj = func[:-5]
            if args:
                arg = args[0]
                if arg.startswith("lambda ") and ": " in arg:
                    param_part, body_part = arg.split(": ", 1)
                    param = param_part.replace("lambda ", "").strip()
                    return f"next(({param} for {param} in {obj} if {body_part}), None)"
                return f"next((_fd for _fd in {obj} if {arg}), None)"
            return "None"

        # new Foo(...) → handled in _expr_new_expression
        # Regular function call
        args_str = ", ".join(args)
        return f"{func}({args_str})"

    def _expr_member_expression(self, node: Node) -> str:
        obj = node.child_by_field_name("object")
        prop = node.child_by_field_name("property")

        obj_text = self._translate_expression(obj) if obj else ""
        prop_text = self._translate_expression(prop) if prop else ""

        # Check for optional chain (?.)
        has_optional_chain = any(c.type == "optional_chain" for c in node.children)

        # Handle computed properties: obj[key]
        for child in node.children:
            if child.type == "[":
                # Subscript access
                index = node.child_by_field_name("property") or node.children[-2]
                index_text = self._translate_expression(index)
                if has_optional_chain:
                    return f"({obj_text}[{index_text}] if {obj_text} is not None else None)"
                return f"{obj_text}[{index_text}]"

        # .length → len(...)
        if prop_text == "length":
            if has_optional_chain:
                return f"(len({obj_text}) if {obj_text} is not None else 0)"
            return f"len({obj_text})"

        # Number.EPSILON
        if obj_text == "float" and prop_text == "EPSILON":
            return "1e-15"
        if obj_text == "Number" and prop_text == "EPSILON":
            return "1e-15"

        # For optional chain, keep the regular dotted access
        # (the ?. null safety is handled at the call site or by ?? operator)
        return f"{obj_text}.{prop_text}"

    def _expr_subscript_expression(self, node: Node) -> str:
        obj = node.child_by_field_name("object")
        index = node.child_by_field_name("index")

        obj_text = self._translate_expression(obj) if obj else ""
        index_text = self._translate_expression(index) if index else ""

        # Handle optional chaining: obj?.[key]
        return f"{obj_text}.get({index_text})" if "?" in get_node_text(node) else f"{obj_text}[{index_text}]"

    def _expr_optional_chain_expression(self, node: Node) -> str:
        """Handle x?.foo → x.foo if x is not None else None."""
        # Just translate the inner expression and add None check if needed
        text = get_node_text(node)
        # Simple approach: replace ?. with .
        result = self._basic_cleanup(text.replace("?.", ".").replace("?.[", "["))
        return result

    def _expr_new_expression(self, node: Node) -> str:
        constructor = node.child_by_field_name("constructor")
        args_node = node.child_by_field_name("arguments")

        cons_text = self._translate_expression(constructor) if constructor else ""
        args = self._translate_arguments(args_node)

        # new Big(x) → Decimal(str(x))
        if cons_text == "Big":
            arg = args[0] if args else "'0'"
            # If arg is a number literal, quote it
            try:
                float(arg)
                return f"Decimal('{arg}')"
            except (ValueError, TypeError):
                return f"Decimal(str({arg}))"

        # new Date() → datetime.now()
        if cons_text == "Date":
            if not args:
                return "datetime.now()"
            return f"parse_date({args[0]})"

        # new Set() → set()
        if cons_text == "Set":
            if args:
                return f"set({args[0]})"
            return "set()"

        # new Map() → {}
        if cons_text == "Map":
            return "{}"

        args_str = ", ".join(args)
        return f"{cons_text}({args_str})"

    def _expr_template_string(self, node: Node) -> str:
        """Translate template literals to f-strings."""
        parts = []
        for child in node.children:
            if child.type == "template_chars" or child.type == "string_fragment":
                parts.append(get_node_text(child))
            elif child.type == "template_substitution":
                for c in child.children:
                    if c.type not in ("${", "}"):
                        expr = self._translate_expression(c)
                        parts.append(f"{{{expr}}}")
            elif child.type in ("`",):
                continue
            else:
                parts.append(get_node_text(child))
        return f'f"{"".join(parts)}"'

    def _expr_arrow_function(self, node: Node) -> str:
        """Translate arrow functions to lambda or inline."""
        params = node.child_by_field_name("parameters")
        body = node.child_by_field_name("body")

        param_names = []
        has_destructuring = False
        destructured_names = []

        if params:
            if params.type == "identifier":
                param_names.append(get_node_text(params))
            else:
                for child in params.children:
                    if child.type in ("(", ")", ","):
                        continue
                    if child.type == "identifier":
                        param_names.append(get_node_text(child))
                    elif child.type == "required_parameter":
                        # Check for destructuring inside required_parameter
                        for c in child.children:
                            if c.type == "identifier":
                                name = get_node_text(c)
                                if ":" in name:
                                    name = name.split(":")[0].strip()
                                param_names.append(name)
                            elif c.type == "object_pattern":
                                has_destructuring = True
                                for cc in c.children:
                                    if cc.type == "shorthand_property_identifier_pattern":
                                        destructured_names.append(get_node_text(cc))
                    elif child.type == "object_pattern":
                        has_destructuring = True
                        for c in child.children:
                            if c.type == "shorthand_property_identifier_pattern":
                                destructured_names.append(get_node_text(c))

        if has_destructuring and destructured_names:
            # For destructured params, use a single param and access attributes
            param = "_item"
            param_names = [param]

        params_str = ", ".join(param_names) if param_names else "_"

        if body and body.type != "statement_block":
            # Simple expression body: (x) => x + 1
            expr = self._translate_expression(body)
            # Replace destructured names with dict access
            if has_destructuring and destructured_names:
                for dn in destructured_names:
                    expr = expr.replace(dn, f'_item.get("{dn}")')
            return f"lambda {params_str}: {expr}" if params_str else f"lambda: {expr}"

        # Block body — extract return statement
        if body:
            for child in body.children:
                if child.type in ("{", "}"):
                    continue
                if child.type == "return_statement":
                    for c in child.children:
                        if c.type not in ("return", ";"):
                            expr = self._translate_expression(c)
                            if has_destructuring and destructured_names:
                                for dn in destructured_names:
                                    expr = expr.replace(dn, f'_item.get("{dn}")')
                            return f"lambda {params_str}: {expr}" if params_str else f"lambda: {expr}"

        return f"lambda {params_str}: None"

    def _expr_object(self, node: Node) -> str:
        """Translate object literal to Python dict."""
        pairs = []
        for child in node.children:
            if child.type == "pair":
                key = child.child_by_field_name("key")
                value = child.child_by_field_name("value")
                key_text = self._translate_expression(key)
                # If key is an identifier, quote it
                if key and key.type in ("property_identifier", "identifier"):
                    key_text = f'"{key_text}"'
                value_text = self._translate_expression(value)
                pairs.append(f"{key_text}: {value_text}")
            elif child.type in ("shorthand_property", "shorthand_property_identifier"):
                name = get_node_text(child)
                pairs.append(f'"{name}": {name}')
            elif child.type == "spread_element":
                for c in child.children:
                    if c.type != "...":
                        expr = self._translate_expression(c)
                        pairs.append(f"**{expr}")
            elif child.type == "method_definition":
                # Inline method in object literal — skip for now
                pass
            elif child.type == "comment":
                pass
        return "{" + ", ".join(pairs) + "}"

    def _expr_array(self, node: Node) -> str:
        """Translate array literal to Python list."""
        items = []
        for child in node.children:
            if child.type in ("[", "]", ","):
                continue
            if child.type == "spread_element":
                for c in child.children:
                    if c.type != "...":
                        expr = self._translate_expression(c)
                        items.append(f"*{expr}")
            else:
                items.append(self._translate_expression(child))
        return "[" + ", ".join(items) + "]"

    def _expr_as_expression(self, node: Node) -> str:
        """Type assertion: x as Type → just x."""
        for child in node.children:
            if child.type not in ("as", "type_identifier", "predefined_type",
                                  "generic_type", "array_type", "union_type"):
                return self._translate_expression(child)
        return ""

    def _expr_non_null_assertion_expression(self, node: Node) -> str:
        """Handle x! → x (remove non-null assertion)."""
        for child in node.children:
            if child.type != "!":
                return self._translate_expression(child)
        return ""

    def _expr_spread_element(self, node: Node) -> str:
        for child in node.children:
            if child.type != "...":
                expr = self._translate_expression(child)
                return f"*{expr}"
        return ""

    def _expr_await_expression(self, node: Node) -> str:
        """Translate await expr → expr (strip await, we run sync)."""
        for child in node.children:
            if child.type != "await":
                return self._translate_expression(child)
        return ""

    def _expr_type_assertion(self, node: Node) -> str:
        """Handle <Type>expr → expr."""
        for child in node.children:
            if child.type not in ("type_identifier", "<", ">"):
                return self._translate_expression(child)
        return ""

    def _expr_satisfies_expression(self, node: Node) -> str:
        """Handle expr satisfies Type → expr."""
        for child in node.children:
            if child.type not in ("satisfies", "type_identifier"):
                return self._translate_expression(child)
        return ""

    # ── Class members ────────────────────────────────────────────────

    def visit_public_field_definition(self, node: Node) -> str:
        """Class field declarations — collect for __init__."""
        name_node = node.child_by_field_name("name")
        value_node = node.child_by_field_name("value")
        if name_node:
            name = get_node_text(name_node)
            if value_node:
                value = self._translate_expression(value_node)
                return f"{self._indent()}# field: {name} = {value}"
            return f"{self._indent()}# field: {name}"
        return ""

    def visit_property_declaration(self, node: Node) -> str:
        return self.visit_public_field_definition(node)

    # ── Comments ─────────────────────────────────────────────────────

    def visit_comment(self, node: Node) -> str:
        text = get_node_text(node)
        # Replace smart quotes and other problematic Unicode
        text = text.replace("\u2019", "'").replace("\u2018", "'")
        text = text.replace("\u201c", '"').replace("\u201d", '"')
        text = text.replace("\u2014", "-").replace("\u2013", "-")
        if text.startswith("//"):
            return f"{self._indent()}# {text[2:].strip()}"
        if text.startswith("/*"):
            inner = text[2:-2].strip()
            lines = inner.split("\n")
            if len(lines) == 1:
                return f'{self._indent()}# {lines[0].strip()}'
            result = []
            for line in lines:
                clean = line.strip().lstrip("* ")
                if clean:
                    result.append(f"{self._indent()}# {clean}")
            return "\n".join(result)
        return ""

    # ── Enum ─────────────────────────────────────────────────────────

    def visit_enum_declaration(self, node: Node) -> str:
        name_node = node.child_by_field_name("name")
        name = get_node_text(name_node) if name_node else "UnknownEnum"
        body = node.child_by_field_name("body")

        members = []
        if body:
            for child in body.children:
                if child.type == "enum_assignment":
                    member_name = None
                    member_value = None
                    for c in child.children:
                        if c.type == "property_identifier":
                            member_name = get_node_text(c)
                        elif c.type not in ("=",):
                            member_value = self._translate_expression(c)
                    if member_name:
                        val = member_value or f'"{member_name}"'
                        members.append(f"    {member_name} = {val}")
                elif child.type == "property_identifier":
                    mn = get_node_text(child)
                    members.append(f"    {mn} = \"{mn}\"")

        result = f"class {name}(str, Enum):"
        if members:
            result += "\n" + "\n".join(members)
        else:
            result += "\n    pass"
        return result

    # ── Interface ────────────────────────────────────────────────────

    def visit_interface_declaration(self, node: Node) -> str:
        name_node = node.child_by_field_name("name")
        name = get_node_text(name_node) if name_node else "UnknownInterface"
        body = node.child_by_field_name("body")

        fields = []
        if body:
            for child in body.children:
                if child.type == "property_signature":
                    fname = None
                    ftype = "Any"
                    for c in child.children:
                        if c.type == "property_identifier":
                            fname = get_node_text(c)
                        elif c.type == "type_annotation":
                            ftype = self._translate_type_annotation(c)
                    if fname:
                        fields.append(f"    {fname}: {ftype} = None")

        result = f"@dataclass\nclass {name}:"
        if fields:
            result += "\n" + "\n".join(fields)
        else:
            result += "\n    pass"
        return result

    # ── Type alias ───────────────────────────────────────────────────

    def visit_type_alias_declaration(self, node: Node) -> str:
        """Handle type aliases — emit as TypeAlias comment."""
        name_node = node.child_by_field_name("name")
        value_node = node.child_by_field_name("value")
        if name_node:
            name = get_node_text(name_node)
            if value_node:
                val = self._translate_type(value_node)
                return f"{name} = {val}  # type alias"
        return ""

    # ── Empty / structural ───────────────────────────────────────────

    def visit_empty_statement(self, node: Node) -> str:
        return ""

    def visit_statement_block(self, node: Node) -> str:
        return self._translate_statements(node)
