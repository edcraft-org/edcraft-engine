# Question Generator

The Question Generator is the orchestration layer that coordinates all components to generate complete algorithmic questions from code. It executes code, traces execution, generates question text, computes correct answers, and creates plausible distractors - all from a simple specification.

## Overview

When generating questions about code execution, we need to:
- Execute code with specific inputs and trace its behavior
- Generate natural language question text
- Extract correct answers from execution traces
- Create plausible incorrect options (distractors) for multiple-choice questions
- Assemble everything into a complete question object

The Question Generator accomplishes this by orchestrating four key components:
1. **StepTracer**: Executes and traces code execution
2. **TextGenerator**: Creates human-readable question text
3. **QueryGenerator**: Extracts answers from execution traces
4. **DistractorGenerator**: Generates plausible incorrect options

## Architecture

### Core Components

```
question_generator/
├── question_generator.py          # Main QuestionGenerator orchestrator
├── models.py                       # Data models (Question, QuestionSpec, etc.)
├── text_generator/                 # Question text generation
├── query_generator/                # Answer extraction from traces
└── distractor_generator/           # Distractor generation
```

### QuestionGenerator

The main class orchestrates the entire question generation pipeline.

**Key responsibilities:**
- Executes code with input data and generates execution traces
- Coordinates text, answer, and distractor generation
- Assembles complete Question objects
- Supports template preview generation (without code execution)

**Dependencies:**
- `step_tracer.StepTracer`: Code execution and tracing
- `TextGenerator`: Question text generation
- `QueryGenerator`: Answer extraction
- `DistractorGenerator`: Distractor generation

## How It Works

### Initialization

```python
from edcraft_engine.question_generator import QuestionGenerator

# Create a QuestionGenerator
generator = QuestionGenerator()
```

The generator initializes with:
- A StepTracer instance for code execution and tracing
- A TextGenerator for creating question text
- A DistractorGenerator with default strategies

### Question Generation Flow

The `generate_question()` method orchestrates question generation in four stages:

1. **Generate Question Text**: Uses TextGenerator to create natural language question
2. **Execute and Trace Code**: Injects input data, transforms code, and executes with tracing
3. **Extract Answer**: Builds query from specification and executes against trace
4. **Generate Distractors**: Creates incorrect options for MCQ/MRQ questions (if applicable)

### Template Preview Flow

The `generate_template_preview()` method creates question previews without executing code:

1. **Generate Template Text**: Creates question text with placeholder syntax
2. **Create Placeholder Values**: Generates placeholder answer and options
3. **Return Preview**: Returns Question object with template placeholders

This is useful for previewing question structure before providing actual inputs.

## Data Models

### QuestionSpec

Specifies what question to generate:

```python
from edcraft_engine.question_generator import QuestionSpec, TargetElement

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
```

**Fields:**
- `target`: List of TargetElement objects specifying what to query
- `output_type`: How to aggregate results (`list`, `count`, `first`, `last`)
- `question_type`: Question format (`mcq`, `mrq`, `short_answer`)

### ExecutionSpec

Specifies how to execute the code:

```python
from edcraft_engine.question_generator import ExecutionSpec

exec_spec = ExecutionSpec(
    entry_function="calculate_sum",
    input_data={"arr": [1, 2, 3, 4, 5]}
)
```

**Fields:**
- `entry_function`: Name of the function to call
- `input_data`: Dictionary of arguments to pass (optional for templates)

### GenerationOptions

Controls question generation parameters:

```python
from edcraft_engine.question_generator import GenerationOptions

options = GenerationOptions(
    num_distractors=3
)
```

**Fields:**
- `num_distractors`: Number of incorrect options to generate (default: 4)

### Question

The generated question object:

```python
class Question:
    text: str                          # Question text
    answer: Any                        # Correct answer
    options: list[Any] | None          # Options for MCQ/MRQ
    correct_indices: list[int] | None  # Indices of correct options
    question_type: str                 # Question type
```

## Usage Examples

### Example 1: Simple MCQ About Function Return Value

```python
from edcraft_engine.question_generator import (
    QuestionGenerator,
    QuestionSpec,
    ExecutionSpec,
    GenerationOptions,
    TargetElement,
)

# Initialize generator
generator = QuestionGenerator()

# Define the code
code = """
def calculate_sum(arr):
    total = 0
    for num in arr:
        total += num
    return total
"""

# Specify what to ask
question_spec = QuestionSpec(
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

# Specify execution
execution_spec = ExecutionSpec(
    entry_function="calculate_sum",
    input_data={"arr": [1, 2, 3, 4, 5]}
)

# Generate options
generation_options = GenerationOptions(num_distractors=3)

# Generate question
question = generator.generate_question(
    code=code,
    question_spec=question_spec,
    execution_spec=execution_spec,
    generation_options=generation_options,
)

# Result:
# {
#   "text": "During execution, what is the return value of the first function `calculate_sum()` call? Choose the correct option.\nGiven input: arr = [1, 2, 3, 4, 5]",
#   "answer": "15",
#   "options": [13, 15, 14, 16],  # Shuffled with correct answer
#   "correct_indices": [1],  # Index of correct answer (15)
#   "question_type": "mcq"
# }
```

### Example 2: Short Answer About Variable Value

```python
# Specify what to ask
question_spec = QuestionSpec(
    target=[
        TargetElement(type="function", name="calculate_sum", id=[0]),
        TargetElement(type="loop", line_number=3, id=[0]),
        TargetElement(type="variable", name="total", id=[0])
    ],
    output_type="last",
    question_type="short_answer"
)

# Same execution spec as before
execution_spec = ExecutionSpec(
    entry_function="calculate_sum",
    input_data={"arr": [1, 2, 3, 4, 5]}
)

# No distractors needed for short answer
generation_options = GenerationOptions()

# Generate question
question = generator.generate_question(
    code=code,
    question_spec=question_spec,
    execution_spec=execution_spec,
    generation_options=generation_options,
)

# Result:
# {
#   "text": "For each `calculate_sum()` call, in the loop at line 3, what is the value of the variable `total` at the end? Provide the answer.\nGiven input: arr = [1, 2, 3, 4, 5]",
#   "answer": "15",
#   "options": None,
#   "correct_indices": None,
#   "question_type": "short_answer"
# }
```

### Example 3: MRQ About Loop Iterations

```python
code = """
def process_items(items):
    results = []
    for item in items:
        if item > 0:
            results.append(item * 2)
    return results
"""

question_spec = QuestionSpec(
    target=[
        TargetElement(type="function", name="process_items", id=[0]),
        TargetElement(type="loop", line_number=3, modifier="loop_iterations", id=[0]),
        TargetElement(type="variable", name="item", id=[0])
    ],
    output_type="list",
    question_type="mrq"
)

execution_spec = ExecutionSpec(
    entry_function="process_items",
    input_data={"items": [1, -2, 3, -4, 5]}
)

generation_options = GenerationOptions(num_distractors=3)

question = generator.generate_question(
    code=code,
    question_spec=question_spec,
    execution_spec=execution_spec,
    generation_options=generation_options,
)

# Result:
# {
#   "text": "For each `process_items()` call, for each loop iteration (line 3), what are the values of the variable `item`? Select all that apply.\nGiven input: items = [1, -2, 3, -4, 5]",
#   "answer": "[1, -2, 3, -4, 5]",
#   "options": [[1, -2, 3, -4, 5], [-2, 1, 3, -4, 5], ...],  # Shuffled
#   "correct_indices": [0, 3],  # Multiple correct answers
#   "question_type": "mrq"
# }
```

### Example 4: Template Preview

```python
# Generate preview without executing code
question_spec = QuestionSpec(
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

generation_options = GenerationOptions(num_distractors=3)

preview = generator.generate_template_preview(
    question_spec=question_spec,
    generation_options=generation_options,
)

# Result:
# {
#   "text": "During execution, what is the return value of the first function `calculate_sum()` call? Choose the correct option.",
#   "answer": "<placeholder_answer>",
#   "options": ["<option_1>", "<option_2>", "<option_3>", "<option_4>"],
#   "correct_indices": [0],
#   "question_type": "mcq"
# }
```

## Implementation Details

### Input Data Injection

The `_inject_input_data()` method prepares code for execution:

```python
# Original code
code = "def calculate_sum(arr): ..."

# After injection
"""
def calculate_sum(arr): ...

# Execute the function
calculate_sum(**{'arr': [1, 2, 3]})
"""
```

This appends a function call with the specified input data to enable tracing.

### Option Shuffling

The `_shuffle_options()` method randomizes answer options while tracking correct positions:

```python
options = [42, 41, 43, 40]  # First item is correct
num_correct = 1

shuffled, indices = generator._shuffle_options(options, num_correct)
# shuffled: [43, 42, 40, 41]
# indices: [1]  # Correct answer moved to index 1
```

For MRQ questions with multiple correct answers:

```python
options = [1, 3, 5, 2, 4, 6]  # First 3 are correct
num_correct = 3

shuffled, indices = generator._shuffle_options(options, num_correct)
# shuffled: [4, 1, 6, 5, 2, 3]
# indices: [1, 3, 4, 5]  # Tracks all correct answer positions
```

### Question Type Handling

**MCQ (Multiple Choice Question):**
- Single correct answer
- Wraps answer in list for distractor generation
- Returns single correct index

**MRQ (Multiple Response Question):**
- Multiple correct answers
- Uses answer list directly for distractor generation
- Returns list of correct indices

**Short Answer:**
- No options or indices generated
- Returns answer as string
