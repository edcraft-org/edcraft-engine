# Distractor Generator

The **Distractor Generator** creates plausible but incorrect answer options for MCQ and MRQ questions.

It works by generating answers that are:

* Close to the correct answer
* Structurally similar
* Slightly incorrect in meaningful ways

## Core Idea

Instead of random wrong answers, we generate distractors by:

1. **Modifying the correct answer** (small mistakes)
2. **Changing how the answer is queried** (logical variations)

## How It Works

1. Start with the correct answer(s)
2. Apply strategies one by one
3. Collect valid distractors
4. Remove duplicates and correct answers
5. Return the required number

## Strategies

### 1. Output Modification Strategy

**Idea:** Make small changes to the correct answer.

#### Examples

```python
correct = 10
→ generated: 9, 11, 8
```

```python
correct = [1, 2, 3]

# generated:
→ [2, 1, 3]        # permutation
→ [1, 3, 3]        # small mutation
```

```python
correct = {"a": 5}

# generated:
→ {"a": 4}
→ {"a": 6}
```

#### Behavior

* Works recursively (handles nested lists/dicts)
* Changes **one part at a time**
* Keeps structure intact

### 2. Query Variation Strategy

**Idea:** Change the *question logic* slightly and recompute answers.

#### Techniques

* Change output type:

  ```
  first → list
  ```
* Remove context layers:

  ```
  function, followed by variable → just variable
  ```
* Change modifiers:

  ```
  branch_true ↔ branch_false
  ```

#### Example

```python
correct = 2
query result (variation) = [1, 3]
→ distractors = 1, 3
```

```python
correct = [6]
query result = [5]
→ distractor = [5]
```

#### Important Rules

* If correct answer is scalar → list outputs are flattened
* If correct answer is list → structure must match exactly
* Invalid types (e.g. internal objects) are discarded

## Usage

```python
generator = DistractorGenerator()

distractors = generator.generate_distractors(
    correct_options=[42],
    exec_ctx=execution_context,
    question_spec=question_spec,
    num_distractors=3,
)
```

## Custom Strategies

You can define your own strategy:

```python
class CustomStrategy(DistractorStrategy):
    def generate(self, correct_options, exec_ctx, question_spec, num_distractors):
        return [...]
```

Then plug it in:

```python
generator = DistractorGenerator(
    strategies=[CustomStrategy(), OutputModificationStrategy()]
)
```

## Current Limitations

The current system works but has noticeable limitations:

### 1. Distractor Quality

* Sometimes too obvious (e.g. ±1 for numbers)
* Sometimes not semantically meaningful
* Lacks understanding of “common mistakes”

### 2. Strategy Priority

* Strategies are applied in order of predefined priority
* No strong scoring or ranking according to answer/question

### 3. Type Handling

* Limited support: int, list, dict
* No handling for: strings, floats, custom objects, etc.

### 4. Query Variations

* Can produce invalid outputs
* Requires filtering/validation
* Not all variations are useful

### 5. Deduplication

* Uses `str()` → can be unreliable for complex objects

## Possible Enhancements

### Better Distractor Quality

* Add semantic-aware mutations
  * e.g. off-by-one errors in loops
  * wrong ordering logic
* Use common misconception patterns
* Add LLM-based distractor generation

### Strategy Ranking

* Score distractors based on:
  * similarity to correct answer
  * difficulty level
* Prioritize higher-quality ones instead of simple ordering

### Smarter Query Variations

* Filter out low-value variations early
* Add scoring for variations
* Track which variations produce useful results

### More Data Type Support

Extend output modification to handle:

* strings (typos, casing, substring errors)
* floats (rounding, precision errors)
* tuples / sets
* nested complex structures

### Better Validation

* Replace heuristic validation with **schema-based validation**
* Enforce:

  * exact structure
  * type consistency
  * expected cardinality

### Strategy Composition

* Combine strategies instead of running independently

  * e.g. query variation → then modify result
* Allow multi-step transformations

### Performance

* Cache query results
* Avoid redundant variation execution
