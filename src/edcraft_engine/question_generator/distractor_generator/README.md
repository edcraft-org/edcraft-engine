# Distractor Generator

The Distractor Generator creates plausible but incorrect answer options (distractors) for multiple-choice questions (MCQ) and multiple-response questions (MRQ). It uses a strategy-based architecture to generate distractors that are similar to the correct answer but contain subtle differences.

## Overview

When generating questions about code execution, the system needs to provide incorrect options that:
- Look plausible to someone who hasn't fully understood the code
- Test specific misconceptions or partial understanding
- Are similar enough to the correct answer to be challenging

The Distractor Generator accomplishes this by applying various strategies to modify correct answers in controlled ways.

## Architecture

### Core Components

```
distractor_generator/
├── distractor_generator.py          # Main orchestrator
└── distractor_strategies/
    ├── base_strategy.py              # Abstract base class
    ├── output_modification_strategy.py  # Modifies answer values
    └── query_variation_strategy.py   # Varies query parameters
```

### DistractorGenerator

The main class (distractor_generator.py) orchestrates multiple strategies to generate distractors.

**Key responsibilities:**
- Manages a list of distractor generation strategies
- Applies strategies sequentially until enough distractors are generated
- Deduplicates distractors to ensure unique options
- Prevents correct answers from appearing as distractors

### Strategy Pattern

All distractor strategies inherit from `DistractorStrategy` (base_strategy.py) and implement:

```python
def generate(
    self,
    correct_options: list[Any],
    exec_ctx: ExecutionContext,
    question_spec: QuestionSpec,
    num_distractors: int,
) -> list[Any]:
    pass
```

## Available Strategies

### 1. Output Modification Strategy

**Purpose:** Generates distractors by modifying the values in correct answers while preserving their structure.

**Techniques:**

- **Numeric variations**: For integer values, creates variations by adding/subtracting small amounts (±1, ±2, ±3)
  - Example: `42` → `[41, 43, 40, 44, 39, 45]`
  - Maintains sign (doesn't convert negative to positive)

- **List variations**: Shuffles list elements to create permutations
  - Example: `[1, 2, 3]` → `[2, 1, 3]`, `[3, 2, 1]`

- **Dictionary variations**: Modifies values within dictionaries
  - Varies numeric values
  - Shuffles list values
  - Preserves dictionary structure

**Question type handling:**
- **MCQ**: Modifies elements within the single correct option
- **MRQ**: Generates variations of each correct option

### 2. Query Variation Strategy

**Purpose:** Generates distractors by executing modified versions of the original query against the execution context.

**Techniques:**

- **Output type variations**: Changes query output type
  - Example: `first` → `list` (returns all items instead of just first)

- **Target path variations**: Removes context layers from the target path
  - Example: `[function > loop > variable]` → `[function > variable]`

- **Modifier variations**: Changes target modifiers
  - `branch_true` ↔ `branch_false`
  - `branch` → specific branch paths
  - `loop` → `loop_iterations`

## Usage

### Basic Usage

```python
from edcraft_engine.question_generator.distractor_generator import DistractorGenerator

# Create generator with default strategies
generator = DistractorGenerator()

# Generate distractors
distractors = generator.generate_distractors(
    correct_options=[42],
    exec_ctx=execution_context,
    question_spec=question_spec,
    num_distractors=3
)
# Result: [41, 43, 40]
```

### Custom Strategy Configuration

```python
from edcraft_engine.question_generator.distractor_generator import DistractorGenerator
from edcraft_engine.question_generator.distractor_generator.distractor_strategies import (
    OutputModificationStrategy,
    QueryVariationStrategy,
)

# Use specific strategies
generator = DistractorGenerator(
    strategies=[
        QueryVariationStrategy(),
        OutputModificationStrategy(),
    ]
)
```

## How It Works

### Generation Flow

1. **Initialize seen set**: Track correct options to prevent duplicates

2. **Apply strategies sequentially**: Each strategy generates distractors until target count is reached

3. **Deduplicate**: Filter out distractors that match correct answers or other distractors

4. **Limit results**: Return exactly the requested number of distractors

### Example Generation Process

Given:
- Correct answer: `[1, 2, 3]`
- Requested distractors: 3

Process:
1. OutputModificationStrategy generates shuffled permutations: `[2, 1, 3]`, `[3, 1, 2]`, `[1, 3, 2]`
2. Distractors are deduplicated (none match correct answer)
3. Return first 3: `[[2, 1, 3], [3, 1, 2], [1, 3, 2]]`

## Extending with Custom Strategies

### Creating a Custom Strategy

```python
from edcraft_engine.question_generator.distractor_generator.distractor_strategies import DistractorStrategy

class CustomStrategy(DistractorStrategy):
    def generate(
        self,
        correct_options: list[Any],
        exec_ctx: ExecutionContext,
        question_spec: QuestionSpec,
        num_distractors: int,
    ) -> list[Any]:
        distractors = []

        # Your custom distractor generation logic here
        for option in correct_options:
            # Generate variations
            variation = self._create_variation(option)
            distractors.append(variation)

        return distractors[:num_distractors]

    def _create_variation(self, option: Any) -> Any:
        # Custom variation logic
        pass
```

### Using Custom Strategies

```python
generator = DistractorGenerator(
    strategies=[
        CustomStrategy(),
        OutputModificationStrategy(),
    ]
)
```

## Design Considerations

### Deduplication Strategy

The generator uses string representation for deduplication:
```python
distractor_str = str(distractor)
if distractor_str not in seen:
    distractors.append(distractor)
```

This works for most data types but may need refinement for complex objects with custom `__str__` methods.

### Strategy Ordering

Strategies are applied in order. Place more specific or higher-quality strategies first to ensure they're used before fallback strategies.

### Performance Considerations

- Strategies stop generating once `num_distractors` is reached
- QueryVariationStrategy executes code, which can be slow for complex execution contexts
- OutputModificationStrategy is lightweight and generates distractors quickly
