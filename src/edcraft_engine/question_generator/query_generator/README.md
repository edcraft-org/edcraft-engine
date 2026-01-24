# Query Generator

The Query Generator creates queries to extract specific data from code execution traces. It translates high-level question specifications into executable queries that retrieve values from execution contexts, enabling automated question generation based on actual code behavior.

## Overview

When generating questions about code execution, we need to:
- Target specific elements in the execution trace (functions, loops, branches, variables)
- Extract relevant data (values, counts, iterations, etc.)
- Handle complex relationships between execution elements
- Support different query output formats

The Query Generator accomplishes this by building structured queries that filter, join, and aggregate execution trace data.

## Architecture

### Core Components

```
query_generator/
└── query_generator.py          # Main QueryGenerator class
```

### QueryGenerator

The main class orchestrates query building based on question specifications.

**Key responsibilities:**
- Translates target elements into query filters and joins
- Applies output type transformations (count, first, last, list)
- Handles complex nested queries with multiple target elements
- Cleans output to return only relevant data

**Dependencies:**
- `query_engine.QueryEngine`: Provides the underlying query execution engine
- `step_tracer.ExecutionContext`: Contains execution trace and variable data

## How It Works

### Initialization

```python
from edcraft_engine.question_generator.query_generator import QueryGenerator
from step_tracer import ExecutionContext

# Create a QueryGenerator with an execution context
generator = QueryGenerator(exec_ctx)
```

The generator initializes with:
- A `QueryEngine` instance for query building
- Combined execution trace and variable data
- A join index tracker for handling nested queries

### Query Generation Flow

The `generate_query()` method processes queries in three stages:

1. **Target Selection**: Filters and joins data based on target elements
2. **Output Type Application**: Transforms data according to output type
3. **Output Cleaning**: Selects only relevant fields from results


## Target Elements

Target elements specify what to query from the execution trace. Each element has:

- **type**: Element type (`function`, `loop`, `branch`, `variable`)
- **name**: Optional name (function name, variable name, etc.)
- **line_number**: Optional line number filter
- **modifier**: Optional modifier for specialized queries

### Supported Modifiers

#### Function Modifiers
- `arguments`: Extract function arguments
- `return_value`: Extract function return value

#### Loop Modifiers
- `loop_iterations`: Get all iterations of a loop

#### Branch Modifiers
- `branch_true`: Filter for branches that evaluated to true
- `branch_false`: Filter for branches that evaluated to false

### Single Target Queries

For a single target element (first element in the target list):

```python
target = [TargetElement(type="function", name="calculate_sum")]
query = generator.generate_query(target, output_type="first")
```

The generator creates a base query with `where` clauses:
- Filters by statement type
- Filters by name (if specified)
- Filters by line number (if specified)
- Applies modifier-specific logic

### Multi-Target Queries (Joins)

For multiple target elements, the generator performs left joins:

```python
target = [
    TargetElement(type="function", name="process"),
    TargetElement(type="loop"),
    TargetElement(type="variable", name="total")
]
```

Each subsequent target element joins with previous results based on:
- **Execution time range**: Element must execute within parent's time range
- **Statement type matching**: Matches the specified element type
- **Name matching**: Matches element name if specified
- **Line number matching**: Matches line number if specified
- **Modifier conditions**: Applies modifier-specific filters

The generator assigns aliases (`0`, `1`, `2`, etc.) to each join level for reference.

## Output Types

### `list`
Returns all matching items without transformation.

```python
query = generator.generate_query(target, output_type="list")
# Result: [item1, item2, item3]
```

### `count`
Counts matching items, grouping by parent execution contexts.

```python
query = generator.generate_query(target, output_type="count")
# Result: [3]  (number of matching items)
```

### `first`
Returns the first matching item (by execution order).

```python
query = generator.generate_query(target, output_type="first")
# Result: [item1]
```

Uses execution ID and variable ID to determine ordering.

### `last`
Returns the last matching item (by execution order).

```python
query = generator.generate_query(target, output_type="last")
# Result: [item3]
```

Uses execution ID and variable ID to determine ordering.

## Usage Examples

### Example 1: Get Function Return Value

```python
from edcraft_engine.question_generator.models import TargetElement

target = [
    TargetElement(
        type="function",
        name="calculate_total",
        modifier="return_value"
    )
]

query = generator.generate_query(target, output_type="first")
# Returns: The return value of calculate_total
```

### Example 2: Count Loop Iterations

```python
target = [
    TargetElement(
        type="loop",
        line_number=1,
        modifier="loop_iterations"
    )
]

query = generator.generate_query(target, output_type="count")
# Returns: Number of times the loop executed
```

### Example 3: Get Variable Value in Specific Branch

```python
target = [
    TargetElement(type="branch", name="x > 0", modifier="branch_true"),
    TargetElement(type="variable", name="result")
]

query = generator.generate_query(target, output_type="last")
# Returns: The last value of 'result' when branch was true
```

### Example 4: Get All Variables in a Loop

```python
target = [
    TargetElement(type="function", name="process_items"),
    TargetElement(type="loop"),
    TargetElement(type="variable")
]

query = generator.generate_query(target, output_type="list")
# Returns: All variables from all loop iterations
```

## Query Building Details

### Time Range Filtering

For nested queries, the generator ensures temporal consistency:

**For non-variable targets:**
```python
parent.execution_id <= child.execution_id <= parent.end_execution_id
```

**For variable targets:**
```python
child.execution_id <= parent.end_execution_id
```

This ensures that child elements only match if they occurred during the parent's execution.

### Grouping and Aggregation

When using `count`, `first`, or `last` with joins:
- Groups by all parent execution IDs
- Ensures aggregation happens at the correct level
- Prevents duplicate results from cross-joins

### Output Cleaning

The final stage selects relevant fields:

**For variables:**
- If name is specified: Returns only `value`
- If name is not specified: Returns `name` and `value`

**For count queries:**
- Returns only the count value

**For other element types:**
- Returns the full item (with prefix for joined queries)

## Design Considerations

### Join Index Tracking

The `join_idx` tracks the current depth of joins:
- Starts at 0 for the first target
- Increments with each join operation
- Used to reference correct aliases in nested queries

### Alias Management

Each join level gets a unique alias:
- Left side: Current join index
- Right side: Next join index
- Referenced in group_by and select operations

### Modifier Handling

Modifiers are handled differently for first vs. subsequent targets:
- **First target**: Uses `select()` or `where()` clauses
- **Subsequent targets**: Embedded in join conditions

### Branch Modifier Logic

Branch modifiers filter based on condition evaluation:
- `branch_true`: `condition_result == True`
- `branch_false`: `condition_result == False`

These filters apply both in initial queries and in join conditions.

## Performance Considerations

- Queries are lazy-evaluated by the QueryEngine
- Joins are performed in-memory on execution trace data
- Complex nested queries with multiple joins may be slower
- Grouping operations require iteration over all matching items

## Integration with Question Generation

The Query Generator is used by the question generation system to:

1. **Extract correct answers**: Run queries to get the actual execution values
2. **Support distractor generation**: Provide query variations for the QueryVariationStrategy
3. **Enable flexible question types**: Support various output formats and target combinations
