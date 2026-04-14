# Person A: Build the Translator

## Your Mission

Build the tree-sitter based TypeScript-to-Python translator. The entire `tt/tt/` pipeline — parsing, AST walking, transforming, emitting Python. Your goal: maximize the number of API tests that pass.

## Architecture

```
.ts source files
     ↓
tree-sitter (Python bindings) → typed syntax tree
     ↓
Visitor/Transformer (Python) → walks the tree, maps TS constructs to Python
     ↓
Python code emitter → formatted .py files
     ↓
translations/ghostfolio_pytx/app/implementation/
```

## Module Structure to Build

```
tt/tt/
├── translator.py              # Pipeline orchestration: parse → transform → emit
├── parser.py                  # tree-sitter setup, parse TS → AST
├── visitor.py                 # AST walker, dispatches to transform handlers
├── emitter.py                 # Python code builder (indentation, imports, formatting)
├── transformers/
│   ├── types.py               # string→str, number→float, Array<T>→List[T], etc.
│   ├── classes.py             # class, extends, constructor → __init__, this→self
│   ├── functions.py           # methods, arrow functions, async/await
│   ├── interfaces.py          # interface → @dataclass
│   ├── enums.py               # enum → Python Enum
│   ├── imports.py             # import/export → Python imports
│   ├── expressions.py         # ?., ??, ternary, template literals, spread
│   └── control_flow.py        # if/else, for..of, switch, try/catch
└── runtime/
    └── helpers.py             # Small runtime shims for translated code
```

## Implementation Order

### Step 1: tree-sitter setup + parse verification

```bash
cd tt && uv add tree-sitter tree-sitter-typescript
```

Build `parser.py`:
- Initialize tree-sitter with TypeScript grammar
- `parse_file(path) → Tree`
- Verify on the main calculator file:
  ```
  projects/ghostfolio/apps/api/src/app/portfolio/calculator/roai/portfolio-calculator.ts
  ```

**Commit.**

### Step 2: Type mappings

```
TypeScript          → Python
string              → str
number              → float
boolean             → bool
any                 → Any
void                → None
null/undefined      → None
Array<T>            → List[T]
Record<K,V>         → Dict[K, V]
Promise<T>          → T (unwrap)
T | null            → Optional[T]
Date                → datetime
Big                 → Decimal
```

**Commit.**

### Step 3: Class + method translation

```
export class Foo extends Bar {    →    class Foo(Bar):
  private x: number;              →        # field absorbed into __init__
  constructor(private svc: X) {   →        def __init__(self, svc: X):
    super();                      →            super().__init__()
    this.x = 0                    →            self.x = 0
  }
  protected calc(): number {      →        def calc(self) -> float:
    return this.x * 2;            →            return self.x * 2
  }
}
```

**Commit.**

### Step 4: Imports, enums, interfaces

```
import { Foo } from './bar';      →    from .bar import Foo
enum Color { Red = 'RED' }        →    class Color(str, Enum): Red = 'RED'
interface Pos { symbol: string }   →    @dataclass\nclass Pos: symbol: str
```

**Commit.**

### Step 5: Expressions + control flow

```
x?.foo          →    x.foo if x is not None else None
x ?? default    →    x if x is not None else default
cond ? a : b    →    a if cond else b
`hi ${name}`    →    f"hi {name}"
for (x of arr)  →    for x in arr:
switch/case     →    if/elif/else
```

**Commit.**

### Step 6: Emitter + pipeline wiring

Assemble translated fragments into valid Python files with:
- Correct indentation
- Sorted/deduplicated imports
- `pass` in empty bodies
- Trailing newline

Wire into `translator.py` so `uv run --project tt tt translate` runs the full pipeline.

**Commit.**

### Step 7: Iterate on test results

```bash
make evaluate_tt_ghostfolio
```

Read failures → identify untranslated TS pattern → add/fix transformer → rerun. **Commit after each fix.**

## Key TypeScript Files to Translate

```
# Main calculator (most important)
projects/ghostfolio/apps/api/src/app/portfolio/calculator/roai/portfolio-calculator.ts

# Base class
projects/ghostfolio/apps/api/src/app/portfolio/calculator/portfolio-calculator.ts

# Types and interfaces
projects/ghostfolio/libs/common/src/lib/interfaces/
```

## tree-sitter Tips

Common AST node types you'll encounter:
- `class_declaration`, `class_heritage`
- `method_definition`, `public_field_definition`
- `function_declaration`, `arrow_function`
- `if_statement`, `for_in_statement`, `switch_statement`
- `call_expression`, `member_expression`, `optional_chain_expression`
- `ternary_expression`, `template_string`
- `type_annotation`, `generic_type`, `union_type`

Dump any file's AST:
```python
tree = parser.parse_file("path/to/file.ts")
print(tree.root_node.sexp())
```

## Workflow

```bash
scripts/new-task.sh translator "Build tree-sitter TS→Python translator"
cd .worktrees/translator && claude
```

Iterate: edit → `uv run --project tt tt translate` → `make spinup-and-test-ghostfolio_pytx` → commit.

## Rules

- NO LLMs in the translation pipeline
- NO hardcoded ghostfolio logic — the translator must genuinely translate TS constructs
- Use `tt_import_map.json` in scaffold for project-specific import mappings
- Wrapper files are immutable — only write to `app/implementation/`
- `make detect_rule_breaches` before every commit
