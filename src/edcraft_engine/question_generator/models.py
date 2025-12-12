from typing import Any, Literal

from pydantic import BaseModel, Field

# Type aliases for clarity
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
    id: int | list[int] = Field(
        ...,
        description="Index of the element in the respective array "
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


class AlgorithmInput(BaseModel):
    """Execution parameters for running the algorithm."""

    entry_function: str = Field(
        ..., description="Name of the entry point function to execute"
    )
    input_data: dict[str, Any] = Field(
        ..., description="Input parameters for the algorithm as key-value pairs"
    )


class GenerateQuestionRequest(BaseModel):
    """Request to generate a question based on form selections."""

    code: str = Field(..., description="Original algorithm source code")
    target: list[TargetElement] = Field(
        ..., description="The target elements to query in the algorithm"
    )
    output_type: OutputType = Field(
        ..., description="Type of output to query (list, count, first, last)"
    )
    question_type: QuestionType = Field(
        ..., description="Type of question to generate (mcq, mrq, short_answer)"
    )
    algorithm_input: AlgorithmInput = Field(
        ..., description="Input parameters for executing the algorithm"
    )
    num_distractors: int = Field(
        default=4, description="Number of distractor options for MCQ/MRQ (default: 4)"
    )
