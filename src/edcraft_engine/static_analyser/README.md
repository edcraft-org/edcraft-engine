# Static Analyser

The Static Analyser extracts structural information from Python source code without executing it. It parses code using Python's AST (Abstract Syntax Tree) to identify functions, loops, branches, variables, and their scope relationships - providing the foundation for code analysis and question generation.

## Overview

When analyzing code, we need to understand:
- What functions are defined and called
- Where loops and conditional branches occur
- What variables exist and in what scope
- The hierarchical structure of code elements
- Parent-child relationships between code blocks

The Static Analyser accomplishes this by:
1. Parsing Python source code into an AST
2. Walking the AST to identify code elements
3. Tracking scope and variable visibility
4. Building a hierarchical model of code structure

## Architecture

### Core Components

```
static_analyser/
├── static_analyser.py    # Main StaticAnalyser class
└── models.py             # Data models (Scope, CodeElement, etc.)
```

### StaticAnalyser

The main class that performs static analysis using Python's `ast.NodeVisitor`.

**Key responsibilities:**
- Parse source code into an AST
- Track scope hierarchy as it traverses the tree
- Record functions, loops, and branches
- Manage variable visibility across scopes
- Build parent-child relationships between code elements

**Data tracked:**
- `functions`: List of all function definitions and calls
- `loops`: List of all for and while loops
- `branches`: List of all if/elif statements
- `root_scope`: The module-level scope
- `root_element`: The top-level code element

## How It Works

### Initialization

```python
from edcraft_engine.static_analyser import StaticAnalyser

# Create a StaticAnalyser
analyser = StaticAnalyser()
```

The analyser initializes with:
- A root scope representing module-level variables
- A root code element representing the entire module
- Empty lists for tracking functions, loops, and branches

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
# Module scope (root)
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
# Root element (module)
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

```python
class Scope:
    parent: Scope | None           # Parent scope (None for root)
    variables: set[str]            # Variables defined in this scope
    children: list[Scope]          # Child scopes

    @property
    def visible_variables(self) -> set[str]:
        # Returns all variables visible in this scope
        # (includes parent scope variables)
```

**Key features:**
- Automatic parent-child linking on initialization
- `visible_variables` property provides lexical scoping
- Tracks variables defined at this scope level

### CodeElement

Base class for all code structure elements.

```python
class CodeElement:
    id: int                        # Unique identifier
    type: str                      # Element type (module, function, loop, branch)
    lineno: int                    # Line number in source code
    scope: Scope                   # Associated scope
    parent: CodeElement | None     # Parent element
    children: list[CodeElement]    # Child elements
```

**Properties for querying descendants:**
- `functions`: All function elements in subtree
- `loops`: All loop elements in subtree
- `branches`: All branch elements in subtree
- `variables`: Variables in associated scope

### Function

Represents a function definition or call.

```python
class Function(CodeElement):
    name: str                      # Function name or call chain (e.g., "obj.method")
    parameters: list[str]          # Parameter names (for definitions)
    is_definition: bool            # True for def, False for calls
```

**Usage:**
- Function definitions: `is_definition=True`, includes parameters
- Function calls: `is_definition=False`, name may include attribute access (e.g., `list.append`)

### Loop

Represents a for or while loop.

```python
class Loop(CodeElement):
    loop_type: str                 # "for" or "while"
    condition: str                 # Loop condition as string
```

**Examples:**
- For loop: `loop_type="for"`, `condition="i in range(10)"`
- While loop: `loop_type="while"`, `condition="x < 100"`

### Branch

Represents an if statement.

```python
class Branch(CodeElement):
    condition: str                 # Branch condition as string
```

**Note:** Tracks the if statement; elif and else are part of the if node's structure.

### CodeAnalysis

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

### Example 4: Hierarchy Navigation

```python
code = """
def foo():
    for i in range(10):
        if i % 2 == 0:
            print(i)
"""

analyser = StaticAnalyser()
analysis = analyser.analyse(code)

# Navigate from root to nested elements
root = analysis.root_element
print(f"Root children: {len(root.children)}")   # 1 (foo function)

foo_func = root.children[0]
print(f"Foo children: {len(foo_func.children)}") # 1 (for loop)

for_loop = foo_func.children[0]
print(f"Loop children: {len(for_loop.children)}") # 2 (if branch + print call)

# Query all functions in foo
print(f"Functions in foo: {len(foo_func.functions)}")  # 2 (range, print calls)
```

### Example 5: Distinguishing Definitions from Calls

```python
code = """
def greet(name):
    message = f"Hello, {name}"
    print(message)

greet("Alice")
greet("Bob")
"""

analyser = StaticAnalyser()
analysis = analyser.analyse(code)

# Separate definitions from calls
definitions = [f for f in analysis.functions if f.is_definition]
calls = [f for f in analysis.functions if not f.is_definition]

print(f"Definitions: {[f.name for f in definitions]}")  # ['greet']
print(f"Calls: {[f.name for f in calls]}")              # ['print', 'greet', 'greet']

# Count function call occurrences
from collections import Counter
call_counts = Counter(f.name for f in calls)
print(f"greet called: {call_counts['greet']} times")    # 2 times
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

## Integration with Question Generator

The Static Analyser provides structural information used by the Question Generator:

1. **Function Tracking**: Identifies functions to target in questions
2. **Scope Analysis**: Determines which variables are visible at each point
3. **Element Hierarchy**: Maps code structure for navigating execution traces
4. **Line Numbers**: Links code elements to specific source lines

This static analysis complements dynamic analysis (execution tracing) to enable comprehensive questions.
