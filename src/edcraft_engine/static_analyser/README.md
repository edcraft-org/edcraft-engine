# Static Analyser

The Static Analyser extracts structural information from Python source code without executing it. It parses code using Python's AST (Abstract Syntax Tree) to identify functions, loops, branches, variables, and their scope relationships.

## Overview

When analyzing code, we need to understand:
- Code elements like functions, loops and branches
- The hierarchical structure of code elements

The Static Analyser accomplishes this by:
1. Parsing Python source code into an AST
2. Walking the AST to identify code elements
3. Tracking scope and variable visibility
4. Building a hierarchical model of code structure

## Static Analyser

- Parse source code into an AST
- Track scope hierarchy as it traverses the tree
- Record functions, loops, and branches
- Manage variable visibility across scopes
- Build parent-child relationships between code elements

## Usage

### Initialization

```python
from edcraft_engine.static_analyser import StaticAnalyser

analyser = StaticAnalyser()
```

### Analysis Flow

The `analyse()` method processes source code in these steps:

1. **Parse Source Code**: Converts string source code into an AST
2. **Visit AST Nodes**: Walks the tree, visiting each node
3. **Track Scope**: Enters and exits scopes as it encounters code blocks
4. **Record Elements**: Captures functions, loops, branches, and variables
5. **Build Hierarchy**: Maintains parent-child relationships
6. **Return Analysis**: Returns a CodeAnalysis object with all extracted information

### Scope Management

The analyser maintains a stack-like scope hierarchy:

```python
Module scope (root)
├── Function scope (foo)
│   ├── Variables: [x, y]
│   └── Loop scope (for loop)
│       └── Variables: [i]
└── Function scope (bar)
    └── Variables: [result]
```

As the visitor traverses the AST:
- `_enter_scope()`: Creates a new child scope
- `_leave_scope()`: Returns to parent scope
- Variables are added to the current scope

### Code Element Hierarchy

Code elements form a tree structure mirroring the code's logical organization:

```python
Root element (module)
├── Function element (foo)
│   ├── Loop element (for loop)
│   └── Branch element (if statement)
└── Function element (bar)
    └── Loop element (while loop)
```

As the visitor traverses:
- `_enter_code_block()`: Sets current element to new child
- `_leave_code_block()`: Returns to parent element
- Each element tracks its scope, parent, and children

## Data Models

### Scope

Represents a variable scope with parent-child relationships.

- Automatic parent-child linking on initialization
- `visible_variables` property provides lexical scoping
- Tracks variables defined at this scope level

### CodeElement

Base class for all code structure elements.

- `id`: unique identifier
- `type`: element type (module, function, loop, branch)
- `functions`: All function elements in subtree
- `loops`: All loop elements in subtree
- `branches`: All branch elements in subtree
- `variables`: Variables in associated scope

### Function

Represents a function definition or call.

- Function definitions: `is_definition=True`, includes parameters
- Function calls: `is_definition=False`, name may include attribute access (e.g., `list.append`)

### Loop

Represents a for or while loop.

- `loop_type`: `for` / `while`
- `condition`: loop condition as string (e.g. `x < 100`, `i in range(10)`)

### Branch

Represents an if statement.

- `condition`: branch condition as string

Tracks the if statement; elif and else are part of the if node's structure.

## CodeAnalysis

The complete analysis result containing all extracted information.

```python
class CodeAnalysis:
    root_scope: Scope              # Module-level scope
    root_element: CodeElement      # Module-level element
    functions: list[Function]      # All functions found
    loops: list[Loop]              # All loops found
    branches: list[Branch]         # All branches found

    @property
    def variables(self) -> set[str]:
        # Returns all variables across all scopes
```

## Usage Examples

### Example 1: Analyzing Simple Function

```python
from edcraft_engine.static_analyser import StaticAnalyser

code = """
def calculate_sum(arr):
    total = 0
    for num in arr:
        total += num
    return total
"""

analyser = StaticAnalyser()
analysis = analyser.analyse(code)

# Check what was found
print(f"Functions: {len(analysis.functions)}")  # 1 definition
print(f"Loops: {len(analysis.loops)}")          # 1 for loop
print(f"Variables: {analysis.variables}")       # {'arr', 'total', 'num'}

# Get function details
func = analysis.functions[0]
print(f"Function: {func.name}")                 # calculate_sum
print(f"Is definition: {func.is_definition}")   # True
print(f"Line: {func.lineno}")                   # 2

# Get loop details
loop = analysis.loops[0]
print(f"Loop type: {loop.loop_type}")           # for
print(f"Condition: {loop.condition}")           # num in arr
print(f"Line: {loop.lineno}")                   # 4
```

### Example 2: Analyzing Nested Structures

```python
code = """
def process_items(items):
    results = []
    for item in items:
        if item > 0:
            results.append(item * 2)
    return results
"""

analyser = StaticAnalyser()
analysis = analyser.analyse(code)

# Analyze structure
print(f"Functions: {len(analysis.functions)}")  # 2 (def + append call)
print(f"Loops: {len(analysis.loops)}")          # 1
print(f"Branches: {len(analysis.branches)}")    # 1

# Check function calls
for func in analysis.functions:
    if not func.is_definition:
        print(f"Call: {func.name} at line {func.lineno}")
        # Output: "Call: results.append at line 6"

# Check branch condition
branch = analysis.branches[0]
print(f"Branch condition: {branch.condition}")  # item > 0
```

### Example 3: Scope and Variable Tracking

```python
code = """
x = 10

def outer(a):
    y = 20
    def inner(b):
        z = 30
        return a + b + z
    return inner(y)
"""

analyser = StaticAnalyser()
analysis = analyser.analyse(code)

# Module-level variables
print(f"Module vars: {analysis.root_scope.variables}")  # {'x'}

# Function scopes
outer_func = [f for f in analysis.functions if f.name == 'outer'][0]
print(f"Outer vars: {outer_func.scope.variables}")      # {'a', 'y', 'inner'}

inner_func = [f for f in analysis.functions if f.name == 'inner'][0]
print(f"Inner vars: {inner_func.scope.variables}")      # {'b', 'z'}

# Visible variables (with parent scopes)
print(f"Visible in inner: {inner_func.scope.visible_variables}")
# Output: {'b', 'z', 'a', 'y', 'inner', 'x'}
```

## Implementation Details

### AST Visitor Pattern

The StaticAnalyser uses Python's `ast.NodeVisitor` to traverse the AST:

```python
def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
    # Enter new scope for function
    self._enter_scope()

    # Add parameters to scope
    for arg in node.args.args:
        self.current_scope.variables.add(arg.arg)

    # Record function
    func = self._record_function(...)
    self._enter_code_block(func)

    # Visit function body
    self.generic_visit(node)

    # Exit scope and code block
    self._leave_code_block()
    self._leave_scope()
```

### Variable Extraction

The `_extract_names()` method handles various assignment patterns:

```python
# Simple assignment
x = 5                    # Extracts: ['x']

# Tuple unpacking
a, b = 1, 2             # Extracts: ['a', 'b']

# Nested unpacking
(x, y), z = (1, 2), 3   # Extracts: ['x', 'y', 'z']

# Starred assignment
first, *rest = [1, 2, 3] # Extracts: ['first', 'rest']

# Attribute assignment
obj.attr = 5            # Extracts: ['obj']

# Subscript assignment
arr[0] = 10             # Extracts: ['arr']
```

### Function Name Resolution

The `_get_access_chain()` method resolves attribute access in function calls:

```python
# Simple call
print(x)                # Chain: ['print']

# Method call
list.append(x)          # Chain: ['list', 'append']

# Nested attribute access
obj.method.call()       # Chain: ['obj', 'method', 'call']
```

This produces fully qualified names like `"list.append"` for better tracking.

### Condition Unparsing

Loop and branch conditions are converted back to strings using `ast.unparse()`:

```python
# For loop
for i in range(10):     # Condition: "i in range(10)"

# While loop
while x < 100:          # Condition: "x < 100"

# If statement
if len(items) > 0:      # Condition: "len(items) > 0"
```

This preserves the original logic as human-readable text.
