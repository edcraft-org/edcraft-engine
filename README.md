# EdCraft Engine

EdCraft Engine is a Python library for generating **algorithmic programming questions** through code analysis and execution tracing.

It analyzes Python code both **statically (structure)** and **dynamically (runtime behavior)** to automatically generate educational questions about how code works, making it useful for learning programming and creating assessments.

## Features

* **Static Code Analysis**
  Extract structural information (functions, loops, branches, variables) using AST parsing

* **Execution Tracing**
  Track runtime behavior to understand how code executes step by step

* **Question Generation**
  Generate multiple-choice (MCQ), multiple-response (MRQ), and short-answer questions

* **Distractor Generation**
  Produce plausible incorrect answers based on execution context and common mistakes

* **Flexible Targeting**
  Ask questions about specific functions, variables, loops, or return values

## Installation

Install via pip:

```bash
pip install edcraft-engine
```

Or with uv:

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

This example generates a multiple-choice question from a Python function.

```python
from edcraft_engine import QuestionGenerator
from edcraft_engine.question_generator import (
    QuestionSpec,
    ExecutionSpec,
    GenerationOptions,
    TargetElement,
)

generator = QuestionGenerator()

code = """
def calculate_sum(arr):
    total = 0
    for num in arr:
        total += num
    return total
"""

question_spec = QuestionSpec(
    target=[
        TargetElement(
            type="function",
            name="calculate_sum",
            modifier="return_value",
            id=[0],
        )
    ],
    output_type="first",
    question_type="mcq",
)

execution_spec = ExecutionSpec(
    entry_function="calculate_sum",
    input_data={"arr": [1, 2, 3, 4, 5]},
)

question = generator.generate_question(
    code=code,
    question_spec=question_spec,
    execution_spec=execution_spec,
    generation_options=GenerationOptions(num_distractors=3),
)

print(question.text)
print(question.options)
print(question.answer)
```

### What happens here?

1. The code is **instrumented and executed**
2. Execution is **traced step-by-step**
3. A **query extracts the correct answer**
4. Distractors are generated based on context
5. A complete question is assembled

## How It Works

EdCraft Engine follows a pipeline:

```
Code → Static Analysis → Execution Tracing → Querying → Question Generation
```

* **Static analysis** identifies structure (functions, loops, etc.)
* **Execution tracing** captures runtime values and flow
* **Querying** extracts the specific answer
* **Generators** produce the final question and distractors

## Project Structure

```
edcraft-engine/
├── src/edcraft_engine/
│   ├── question_generator/
│   │   ├── text_generator/
│   │   ├── query_generator/
│   │   └── distractor_generator/
│   └── static_analyser/
├── tests/
├── pyproject.toml
└── README.md
```

## Core Components

### Question Generator

Coordinates the full pipeline: execution, tracing, answer extraction, and question assembly.

[Learn more →](src/edcraft_engine/question_generator/README.md)

### Static Analyser

Parses Python code using AST to extract structure without executing it.

[Learn more →](src/edcraft_engine/static_analyser/README.md)

### Text Generator

Generates natural language questions from specifications.

[Learn more →](src/edcraft_engine/question_generator/text_generator/README.md)

### Query Generator

Builds and executes queries on execution traces to extract answers.

[Learn more →](src/edcraft_engine/question_generator/query_generator/README.md)

### Distractor Generator

Generates plausible incorrect options for MCQ/MRQ questions.

[Learn more →](src/edcraft_engine/question_generator/distractor_generator/README.md)

## Development

### Setup

```bash
make install
```

### Run Tests

```bash
make test
# or
uv run pytest
```

### Code Quality

```bash
make lint
make type-check
make all-checks
```

Tools used:

* **Ruff** (linting & formatting)
* **MyPy** (type checking)
* **Pre-commit** (automated checks)

## Dependencies

* Python 3.12+
* [step-tracer](https://github.com/edcraft-org/step-tracer)
* [query-engine](https://github.com/edcraft-org/query-engine)
* Pydantic 2.12+

## License

MIT License — see [LICENSE](LICENSE)

## Related Projects

* [step-tracer](https://github.com/edcraft-org/step-tracer)
* [query-engine](https://github.com/edcraft-org/query-engine)
* [input-gen](https://github.com/edcraft-org/input-gen)
