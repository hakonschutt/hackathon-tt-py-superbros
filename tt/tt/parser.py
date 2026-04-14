"""Tree-sitter based TypeScript parser.

Wraps tree-sitter with the TypeScript grammar to parse .ts files into ASTs.
"""
from __future__ import annotations

from pathlib import Path

import tree_sitter_typescript as ts_typescript
from tree_sitter import Language, Parser, Node, Tree

TS_LANGUAGE = Language(ts_typescript.language_typescript())


def create_parser() -> Parser:
    """Create a tree-sitter parser configured for TypeScript."""
    parser = Parser(TS_LANGUAGE)
    return parser


def parse_source(source: str) -> Tree:
    """Parse TypeScript source code string into a syntax tree."""
    parser = create_parser()
    return parser.parse(source.encode("utf-8"))


def parse_file(path: Path) -> Tree:
    """Parse a TypeScript file into a syntax tree."""
    source = path.read_text(encoding="utf-8")
    return parse_source(source)


def get_node_text(node: Node) -> str:
    """Extract the source text of an AST node."""
    return node.text.decode("utf-8")


def dump_tree(node: Node, indent: int = 0) -> str:
    """Debug helper: dump AST as indented string."""
    lines = [f"{'  ' * indent}{node.type} [{node.start_point[0]}:{node.start_point[1]}]"]
    for child in node.children:
        lines.append(dump_tree(child, indent + 1))
    return "\n".join(lines)
