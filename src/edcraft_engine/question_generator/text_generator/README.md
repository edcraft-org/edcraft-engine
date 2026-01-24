# Text Generator

The Text Generator creates human-readable question text from structured question specifications. It translates technical execution trace queries into natural language questions that students can understand, enabling automated generation of clear and contextually appropriate questions about code execution.

## Overview

When generating questions about code execution, we need to:
- Describe execution context in natural language (which function, loop, or branch)
- Clearly specify what to query (variable values, return values, iteration counts, etc.)
- Format the question appropriately for the question type (MCQ, MRQ, short answer)
- Include input data when relevant

The Text Generator accomplishes this by composing question text from three main components: context, target, and question type instructions.

## Architecture

### Core Components

```
text_generator/
└── text_generator.py          # Main TextGenerator class
```

### TextGenerator

The main class orchestrates question text generation based on question specifications.

**Key responsibilities:**
- Builds hierarchical context from target element paths
- Generates target phrases based on element type, output type, and modifiers
- Formats question type instructions (MCQ, MRQ, short answer)
- Composes final question text with optional input data

## How It Works

### Initialization

```python
from edcraft_engine.question_generator.text_generator import TextGenerator

# Create a TextGenerator
generator = TextGenerator()
```

No initialization parameters needed - the generator is stateless.

### Question Generation Flow

The `generate_question()` method composes questions in three stages:

1. **Context Building**: Creates hierarchical context from all target elements except the last
2. **Target Building**: Generates the query phrase from the last target element and output type
3. **Composition**: Combines context, target, question type instruction, and optional input data

### Question Structure

Generated questions follow this format:

```
[Context], [Target]? [Question Type Instruction]
[Optional: Given input: [Input Data]]
```

**Example:**
```
For each `calculate_sum()` call, what is the return value? Choose the correct option.
Given input: arr = [1, 2, 3]
```

## Question Components

### 1. Context Building

The context describes **where** and **when** to look in the execution trace. It's built from all target elements except the last one.

#### Function Context

```python
TargetElement(type="function", name="process_data")
# Output: "For each `process_data()` call"

TargetElement(type="function", name="calculate", line_number=5)
# Output: "For each `calculate()` call (line 5)"
```

#### Loop Context

```python
# Regular loop
TargetElement(type="loop", line_number=10)
# Output: "in the loop at line 10"

# Loop iterations
TargetElement(type="loop", line_number=10, modifier="loop_iterations")
# Output: "for each loop iteration (line 10)"
```

#### Branch Context

```python
TargetElement(type="branch", name="x > 0", line_number=7)
# Output: "in each `x > 0` branch (line 7)"

# With condition modifier
TargetElement(type="branch", name="x > 0", line_number=7, modifier="branch_true")
# Output: "in each `x > 0` branch (line 7), when the condition is true"
```

#### Hierarchical Context

Multiple context elements are joined with commas:

```python
target = [
    TargetElement(type="function", name="process"),
    TargetElement(type="loop", line_number=5),
    # ... (last element becomes the target, not context)
]
# Output: "For each `process()` call, in the loop at line 5"
```

### 2. Target Building

The target describes **what** to query. It's built from the last target element and the output type.

#### Function Targets

**Basic function queries:**
```python
# Count calls
target = TargetElement(type="function", name="foo")
output_type = "count"
# Output: "how many times was function `foo()` called"

# First/last call
output_type = "first"  # or "last"
# Output: "what is the first function `foo()` call"

# All calls
output_type = "list"
# Output: "what are the function `foo()` calls"
```

**With modifiers:**
```python
# Arguments
target = TargetElement(type="function", name="foo", modifier="arguments")
output_type = "first"
# Output: "what are the arguments passed to the first function `foo()` call"

# Return value
target = TargetElement(type="function", name="bar", modifier="return_value")
output_type = "last"
# Output: "what is the return value of the last function `bar()` call"

# Count unique return values
output_type = "count"
# Output: "how many unique return values were produced by function `bar()`"
```

#### Loop Targets

```python
# Count loop executions
target = TargetElement(type="loop", line_number=5)
output_type = "count"
# Output: "how many times does the loop (line 5) execute"

# Count loop iterations
target = TargetElement(type="loop", line_number=5, modifier="loop_iterations")
output_type = "count"
# Output: "how many loop iterations are there in each loop execution (line 5)"

# Get specific iteration
output_type = "first"  # or "last"
# Output: "what is the first loop iteration for each loop execution (line 5)"
```

#### Branch Targets

```python
# Count branch executions
target = TargetElement(type="branch", name="x > 0", line_number=7)
output_type = "count"
# Output: "how many times do we enter the branch `x > 0` (line 7)"

# With condition modifier
target = TargetElement(type="branch", name="x > 0", line_number=7, modifier="branch_true")
output_type = "first"
# Output: "what is the first time we enter the branch `x > 0` (line 7) when the condition is true"
```

#### Variable Targets

```python
# Count modifications
target = TargetElement(type="variable", name="total")
output_type = "count"
# Output: "how many times was the variable `total` modified"

# Get value at start/end
output_type = "first"  # or "last"
# Output: "what is the value of the variable `total` at the beginning"
# Output: "what is the value of the variable `total` at the end"

# Get all values
output_type = "list"
# Output: "what are the values of the variable `total`"
```

### 3. Question Type Instructions

```python
# Multiple Choice Question (MCQ)
question_type = "mcq"
# Output: "Choose the correct option."

# Multiple Response Question (MRQ)
question_type = "mrq"
# Output: "Select all that apply."

# Short Answer
question_type = "short_answer"
# Output: "Provide the answer."
```

### 4. Input Data Formatting

When input data is provided, it's formatted and appended to the question:

```python
input_data = {"arr": [5, 2, 8, 1], "target": 8}
# Output: "Given input: arr = [5, 2, 8, 1], target = 8"

input_data = {"name": "Alice"}
# Output: 'Given input: name = "Alice"'
```

## Usage Examples

### Example 1: Simple Function Return Value

```python
from edcraft_engine.question_generator.text_generator import TextGenerator
from edcraft_engine.question_generator.models import QuestionSpec, TargetElement

generator = TextGenerator()

spec = QuestionSpec(
    target=[
        TargetElement(
            type="function",
            name="calculate_sum",
            modifier="return_value",
            id=[0]
        )
    ],
    output_type="first",
    question_type="mcq"
)

question = generator.generate_question(spec)
# Output: "During execution, what is the return value of the first function `calculate_sum()` call? Choose the correct option."
```

### Example 2: Variable in Loop Context

```python
spec = QuestionSpec(
    target=[
        TargetElement(type="function", name="process_items", id=[0]),
        TargetElement(type="loop", line_number=5, id=[0]),
        TargetElement(type="variable", name="total", id=[0])
    ],
    output_type="last",
    question_type="short_answer"
)

question = generator.generate_question(spec)
# Output: "For each `process_items()` call, in the loop at line 5, what is the value of the variable `total` at the end? Provide the answer."
```

### Example 3: Counting Loop Iterations

```python
spec = QuestionSpec(
    target=[
        TargetElement(
            type="loop",
            line_number=10,
            modifier="loop_iterations",
            id=[0]
        )
    ],
    output_type="count",
    question_type="mcq"
)

question = generator.generate_question(spec)
# Output: "During execution, how many loop iterations are there in each loop execution (line 10)? Choose the correct option."
```

### Example 4: Branch with Condition

```python
spec = QuestionSpec(
    target=[
        TargetElement(type="function", name="validate", id=[0]),
        TargetElement(
            type="branch",
            name="x > 0",
            line_number=7,
            modifier="branch_true",
            id=[0]
        ),
        TargetElement(type="variable", name="result", id=[0])
    ],
    output_type="first",
    question_type="mrq"
)

question = generator.generate_question(spec)
# Output: "For each `validate()` call, in each `x > 0` branch (line 7), when the condition is true, what is the value of the variable `result` at the beginning? Select all that apply."
```

### Example 5: With Input Data

```python
spec = QuestionSpec(
    target=[
        TargetElement(
            type="function",
            name="find_max",
            modifier="return_value",
            id=[0]
        )
    ],
    output_type="first",
    question_type="mcq"
)

input_data = {"numbers": [5, 2, 8, 1, 9]}

question = generator.generate_question(spec, input_data)
# Output: "During execution, what is the return value of the first function `find_max()` call? Choose the correct option.\nGiven input: numbers = [5, 2, 8, 1, 9]"
```

## Design Considerations

### Hierarchical Context

The context is built from all target elements **except the last one**. This creates a natural hierarchy:

- The last element becomes the target (what to query)
- All preceding elements become the context (where to look)

This separation ensures questions read naturally:
```
[Where to look], [what to query]?
```

### Natural Language Quantifiers

The generator uses appropriate quantifiers based on output type:

- `count`: "how many"
- `first`: "the first", "what is"
- `last`: "the last", "what is"
- `list`: "each", "what are"

### Modifier Integration

Modifiers are integrated differently based on context:

**In context elements:**
- `loop_iterations`: Changes loop description to "for each loop iteration"
- `branch_true/false`: Adds "when the condition is true/false"

**In target elements:**
- `arguments`: Focuses on function arguments
- `return_value`: Focuses on function return values
- `loop_iterations`: Asks about iterations within each loop
- `branch_true/false`: Filters by condition result

### Input Data Formatting

Input data is formatted with:
- Strings enclosed in double quotes
- Other types displayed using Python's default string representation
- Multiple inputs separated by commas

### Empty Context Handling

If there are no context elements (single target element), the default context is:
```
"During execution"
```

## Integration with Question Generation

The Text Generator is used by the question generation system to:

1. **Create question text**: Transform technical specifications into readable questions
2. **Maintain consistency**: Use uniform phrasing across all generated questions
3. **Support all question types**: Handle MCQ, MRQ, and short answer formats
4. **Include context**: Provide necessary input data information to students

## Extensibility

### Adding New Target Types

To support new target element types:

1. Add a new `_build_<type>_target()` method
2. Update `_build_target()` to route to the new method
3. Update `_build_context()` to handle the new type in contexts

### Adding New Modifiers

To support new modifiers:

1. Update the relevant `_build_<type>_target()` method
2. Add context handling in `_build_context()` if needed
3. Ensure natural language phrasing is clear and unambiguous
