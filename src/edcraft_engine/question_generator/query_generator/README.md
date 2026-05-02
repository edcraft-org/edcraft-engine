# Query Generator

The Query Generator turns high-level question specs into executable queries over program execution traces. It lets you extract things like values, counts, and variable states from actual runs of code.

## Overview

`QueryGenerator` builds queries using a `QueryEngine`, based on a list of `TargetElement`s.

## Quick Start

```python
from edcraft_engine.question_generator.query_generator import QueryGenerator

generator = QueryGenerator(exec_ctx)
query = generator.generate_query(target, output_type)
```

## How It Works

`generate_query()` runs in four steps:

1. **Select targets**
   Filters and joins execution data based on `TargetElement`s

2. **Apply output type**
   Shapes the result (`count`, `list`, `first`, `last`)

3. **Apply modifier**
   Extracts fields like `arguments` or `return_value`

4. **Clean output**
   Removes internal fields and returns final values

## TargetElement

Each query is built from one or more `TargetElement`s.

| Field           | Description                                                          |
| --------------- | -------------------------------------------------------------------- |
| `type`          | `"function"`, `"loop"`, `"branch"`, `"variable"`, `"loop_iteration"` |
| `name`          | Optional. Can be comma-separated (`"x, y"`)                          |
| `line_number`   | Optional line filter                                                 |
| `modifier`      | Optional (see below)                                                 |
| `argument_keys` | Optional (used with `arguments`)                                     |

### Modifiers

| Modifier          | Use                             |
| ----------------- | ------------------------------- |
| `arguments`       | Get function arguments          |
| `return_value`    | Get function return value       |
| `loop_iterations` | Expand loop into its iterations |
| `branch_true`     | Only true branch executions     |
| `branch_false`    | Only false branch executions    |

### Name Matching

* `function` → `func_full_name`
* `branch` → `condition_str`
* others → `name`

Comma-separated names match any.

## Single vs Multi Target

### Single Target

Applies a simple filter:

```python
target = [TargetElement(type="function", name="foo")]
```

### Multiple Targets (Joins)

Each additional target joins to the previous one.

Joins are based on:

* statement type
* name (if provided)
* line number (if provided)
* execution order (time range)
* scope (for variables)
* loop/branch modifiers (if used)

Each step is internally tracked with aliases like `"0"`, `"1"`, etc.

## Output Types

| Type    | Result               |
| ------- | -------------------- |
| `list`  | All matching results |
| `count` | Number of matches    |
| `first` | Earliest match       |
| `last`  | Latest match         |

### Notes

* Variable results are ordered using `var_id`
* Multi-variable queries (`"x, y"`) return grouped results
* Joined variable queries apply special logic to pick relevant values relative to parent scope

## Output Behavior

* Variables with a name → return `value`
* Variables without a name → return `{name, value}`
* `arguments` → returns dict or filtered keys
* `count` → returns a number

## Examples

### Function return value

```python
target = [
    TargetElement(type="function", name="calculate_total", modifier="return_value")
]
query = generator.generate_query(target, "first")
```

### Specific argument

```python
target = [
    TargetElement(type="function", name="process", modifier="arguments", argument_keys=["x"])
]
```

### Count loop iterations

```python
target = [
    TargetElement(type="loop", line_number=10, modifier="loop_iterations")
]
```

### Variable after a branch

```python
target = [
    TargetElement(type="branch", name="x > 0", modifier="branch_true"),
    TargetElement(type="variable", name="result"),
]
```

### All variables inside a loop

```python
target = [
    TargetElement(type="function", name="process_items"),
    TargetElement(type="loop"),
    TargetElement(type="variable"),
]
```

### Multiple variables

```python
target = [TargetElement(type="variable", name="x, y")]
# → {"x": [...], "y": [...]}
```

## Enhancements

* **Safer output cleaning**
  Improve output sanitization to ensure internal objects (e.g. `JoinResult`, execution items) are never exposed to consumers. This could include stricter final mapping to plain Python types (e.g. primitives, dicts, lists) and validation before returning results.
