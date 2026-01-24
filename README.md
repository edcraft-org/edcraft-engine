# EdCraft Engine

A Python package for generating algorithmic questions through code analysis and execution tracing. EdCraft Engine analyzes Python source code both statically and dynamically to create educational questions about code behavior, making it ideal for programming education and assessment.

## Features

- **Static Code Analysis**: Extract structural information from Python code using AST parsing
- **Question Generation**: Create multiple-choice, multiple-response, and short-answer questions
- **Smart Distractors**: Generate plausible incorrect options for multiple-choice questions
- **Execution Tracing**: Trace code execution to extract runtime behavior
- **Flexible Targeting**: Query specific functions, loops, variables, and return values
- **Template Previews**: Generate question templates without executing code

## Installation

Install using pip:

```bash
pip install edcraft-engine
```

Or using uv:

```bash
uv add edcraft-engine
```

For development:

```bash
git clone https://github.com/edcraft-org/edcraft-engine.git
cd edcraft-engine
make install
```

## Quick Start

Here's a simple example of generating a multiple-choice question:

```python
from edcraft_engine import QuestionGenerator
from edcraft_engine.question_generator import (
    QuestionSpec,
    ExecutionSpec,
    GenerationOptions,
    TargetElement,
)

# Initialize the generator
generator = QuestionGenerator()

# Define the code to analyze
code = """
def calculate_sum(arr):
    total = 0
    for num in arr:
        total += num
    return total
"""

# Specify what to ask about
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

# Specify execution parameters
execution_spec = ExecutionSpec(
    entry_function="calculate_sum",
    input_data={"arr": [1, 2, 3, 4, 5]}
)

# Generate the question
question = generator.generate_question(
    code=code,
    question_spec=question_spec,
    execution_spec=execution_spec,
    generation_options=GenerationOptions(num_distractors=3),
)

print(question.text)
# Output: "During execution, what is the return value of the first function
#          `calculate_sum()` call? Choose the correct option.
#          Given input: arr = [1, 2, 3, 4, 5]"

print(question.options)
# Output: [13, 15, 14, 16] (shuffled, with correct answer included)

print(question.answer)
# Output: "15"
```

## Project Structure

```
edcraft-engine/
├── src/edcraft_engine/
│   ├── question_generator/     # Question generation orchestration
│   │   ├── text_generator/     # Natural language question text generation
│   │   ├── query_generator/    # Answer extraction from execution traces
│   │   └── distractor_generator/ # Incorrect option generation
│   └── static_analyser/        # Static code analysis using AST
├── tests/                      # Test suite
├── pyproject.toml             # Project configuration
└── README.md                  # This file
```

## Core Components

### Question Generator

The orchestration layer that coordinates all components to generate complete questions. It executes code, traces execution, generates question text, computes answers, and creates distractors.

[Learn more →](src/edcraft_engine/question_generator/README.md)

### Static Analyser

Extracts structural information from Python source code without executing it. Identifies functions, loops, branches, variables, and their scope relationships using AST parsing.

[Learn more →](src/edcraft_engine/static_analyser/README.md)

### Text Generator

Generates natural language question text from question specifications. Creates human-readable questions that ask about code execution behavior.

[Learn more →](src/edcraft_engine/question_generator/text_generator/README.md)

### Query Generator

Extracts answers from execution traces by building and executing queries against traced program state.

[Learn more →](src/edcraft_engine/question_generator/query_generator/README.md)

### Distractor Generator

Creates plausible incorrect options for multiple-choice questions using various strategies like value modification, common mistakes, and pattern-based generation.

[Learn more →](src/edcraft_engine/question_generator/distractor_generator/README.md)

## Development

### Setup

```bash
# Install dependencies
make install

# Run tests
make test

# Run linter
make lint

# Run type checker
make type-check

# Run all checks
make all-checks
```

### Testing

Tests are written using pytest:

```bash
uv run pytest
```

### Code Quality

The project uses:
- **Ruff** for linting and code formatting
- **MyPy** for static type checking
- **Pre-commit** hooks for automated checks

## Dependencies

- Python 3.12+
- [step-tracer](https://github.com/edcraft-org/step-tracer): Code execution tracing
- [query-engine](https://github.com/edcraft-org/query-engine): Query execution against traces
- Pydantic 2.12+: Data validation and modeling

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Related Projects

- [step-tracer](https://github.com/edcraft-org/step-tracer): Execution tracing library
- [query-engine](https://github.com/edcraft-org/query-engine): Query execution engine
