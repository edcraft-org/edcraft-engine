from typing import Any, Literal

from pydantic import BaseModel, Field

TargetElementType = Literal["function", "loop", "branch", "variable"]
OutputType = Literal["list", "count", "first", "last"]
QuestionType = Literal["mcq", "mrq", "short_answer"]
TargetModifier = Literal[
    "arguments", "return_value", "loop_iterations", "branch_true", "branch_false"
]


class TargetElement(BaseModel):
    """Represents a single element in the target path."""

    type: TargetElementType = Field(
        ..., description="Type of the target element (function, loop, branch, variable)"
    )
    id: list[int] = Field(
        ...,
        description="Indices of the element in the respective array "
        "(functions/loops/branches)",
    )
    name: str | None = Field(
        None, description="Name of the element (e.g., function name)"
    )
    line_number: int | None = Field(
        None, description="Line number where the element appears"
    )
    modifier: TargetModifier | None = Field(None, description="Modifier for target")

    def __post_init__(self) -> None:
        if not self.modifier:
            return

        if self.modifier == "loop_iterations" and self.type != "loop":
            raise ValueError("Loop iterations modifier is only valid for loops.")

        if self.modifier in ("branch_true", "branch_false") and self.type != "branch":
            raise ValueError("Branch modifiers are only valid for branches.")

        if self.modifier in ("arguments", "return_value") and self.type != "function":
            raise ValueError("Function modifiers are only valid for functions.")


class Question(BaseModel):
    """Represents a generated question."""

    text: str = Field(..., description="The text of the question")
    answer: Any = Field(..., description="The answer to the question")
    options: list[Any] | None = Field(
        None, description="List of options for MCQ or MRQ types"
    )
    correct_indices: list[int] | None = Field(
        None, description="List of indices of correct options for MCQ or MRQ types"
    )
    question_type: QuestionType = Field(
        ..., description="Type of the question (mcq, mrq, short_answer, etc.)"
    )


class QuestionSpec(BaseModel):
    """Specification for the question to be generated."""

    target: list[TargetElement] = Field(
        ..., description="Target elements in the execution to query"
    )
    output_type: OutputType = Field(
        ..., description="Type of output to generate (list, count, first, last)"
    )
    question_type: QuestionType = Field(
        ..., description="Type of question to generate (mcq, mrq, short_answer)"
    )


class ExecutionSpec(BaseModel):
    """Specification for code execution."""

    entry_function: str = Field(..., description="Name of the entry function to execute")
    input_data: dict[str, Any] = Field(
        ..., description="Input data to pass to the entry function"
    )


class GenerationOptions(BaseModel):
    """Options for question generation."""

    num_distractors: int = Field(
        default=4, description="Number of distractors to generate for MCQ/MRQ questions"
    )
