# Text Generator

The Text Generator creates human-readable question text from structured question specifications. It translates technical execution trace queries into natural language questions that students can understand, enabling automated generation of clear and contextually appropriate questions about code execution.

## Overview

When generating a question about code execution, we need to:

* Describe **where/when** to look (context)
* Specify **what** to query (target)
* Format the question for the **question type**
* Optionally include **input data**

The Text Generator builds a question by combining these pieces into a natural sentence.

## How It Works

### Question Structure

All generated questions follow this format:

```
[Context], [Target]? [Instruction]
[Optional: Given input: ...]
```

**Example:**

```
For each `calculate_sum()` call, what is the return value? Choose the correct option.
Given input: arr = [1, 2, 3]
```

### Generation Flow

`generate_question()` works in three steps:

1. **Context** → built from all target elements *except the last*
2. **Target** → built from the last element + output type
3. **Composition** → combines everything into the final question

## Core Concepts

### 1. Context (Where to look)

Context describes *where or when* in the execution trace to look.

It is built from all target elements except the last.

#### Examples

```python
TargetElement(type="function", name="process")
→ "For each `process()` call"

TargetElement(type="loop", line_number=10)
→ "in the loop at line 10"

TargetElement(type="branch", name="x > 0", modifier="branch_true")
→ "in each `x > 0` branch, when the condition is true"
```

Multiple context elements are combined:

```
For each `process()` call, in the loop at line 5
```

If no context exists:

```
During execution
```

---

### 2. Target (What to query)

The target defines *what the question is asking*.

It depends on:

* `type` (function, loop, branch, variable)
* `output_type` (count, first, last, list)
* `modifier` (arguments, return_value, etc.)

#### Examples

**Function**

```python
count → "how many times was function `foo()` called"
first → "what is the first function `foo()` call"
arguments → "what are the arguments passed to the first function `foo()` call"
```

**Loop**

```python
count → "how many times does the loop execute"
iterations → "how many loop iterations are there"
```

**Branch**

```python
count → "how many times do we enter the branch `x > 0`"
```

**Variable**

```python
count → "how many times was the variable `total` modified"
first → "what is the value of the variable `total` at the beginning"
```

---

### 3. Question Type (Instruction)

Defines how the user should answer:

```python
mcq → "Choose the correct option."
mrq → "Select all that apply."
default → "Provide the answer."
```

### 4. Input Data

If provided, input data is appended:

```python
{"arr": [1, 2, 3]}
→ "Given input: arr = [1, 2, 3]"
```

## Usage

### Basic Example

```python
generator = TextGenerator()

question = generator.generate_question(spec)
```

The generator is **stateless** and requires no setup.

### Example Output

```md
During execution, what is the return value of the first function `calculate_sum()` call? Choose the correct option.
```

## Extensibility

### Add a new target type

1. Implement a new target builder
2. Register it in the target builder registry

### Add new phrasing

Update or add templates—no need to change logic.

### Add new modifiers

Handle them inside the relevant builder (function, loop, etc.)
