# EdCraft

## Step Tracer

The Step Tracer uses **Abstract Syntax Tree (AST)** transformation to automatically insert code and capture detailed execution information. This allows you to analyze program behavior, track variable changes, and answer questions about code execution without manually modifying the original source code.

### Overview

The Step Tracer transforms your Python code by injecting code that records:

-   Variables
-   Function calls
-   Loop iterations
-   Branch execution
-   Execution timeline

### What We Capture

#### **Variables**

Every variable assignment and mutation is captured with

-   Variable **name**
-   **Value** at assignment time
-   **Access path** of variable assignment
-   **Line number** where assignment occured
-   **Scope** where the variable was initialised
-   **Execution context** where the assignment occured

```python
# Original code:
x = 10
lst = [0, 1, 2]
lst[0] = 3

# We capture:
# - Variable 'x': value=10, access_path=x, line_number=1, scope=global, execution_context=global
# - Variable 'lst':
#   - value=[0, 1, 2], access_path=lst, line=2, scope=global, execution_context=global
#   - value=3, access_path=lst[0], line=3, scope=global, execution_context=global
```

A deepcopy of the variable will be made where possible to handle mutable variables.

#### **Loop Execution Details**

For every loop, we record:

-   **Loop type** (for/while)
-   **Iterations** executed

#### **Function Call Information**

Function executions include:

-   **Function name**
-   **Arugments** (parameter names and arugment values)
-   **Return value**
-   **Line number** of **function declaration**
-   **Line number** of **function call**
-   **Execution context** in which function was called

#### **Branch Information**

For every if/else branch, we record:

-   Value of branch **condition**
