from typing import Any, Literal

from pydantic import BaseModel, Field

# Type aliases for clarity
TargetElementType = Literal["function", "loop", "branch", "variable"]
TargetModifier = Literal["arguments", "return_value"]
OutputType = Literal["list", "count", "first", "last"]
QuestionType = Literal["mcq", "mrq", "short_answer"]
ScopeModifier = Literal["loop_iterations", "branch_true", "branch_false"]


class ScopePathItem(BaseModel):
    """Represents a single element in the scope path (breadcrumb navigation)."""

    type: TargetElementType = Field(
        ..., description="Type of the scope element (function, loop, branch, variable)"
    )
    id: int = Field(
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
    modifier: ScopeModifier | None = Field(
        None,
        description="Modifier for loops and branches "
        "(e.g., 'loop_iterations', 'branch_true')",
    )


class TargetSelection(BaseModel):
    """Defines the target element to query in the algorithm."""

    type: TargetElementType = Field(
        ..., description="Type of the target element (function, loop, branch, variable)"
    )
    element_id: int | list[int] = Field(..., description="Single ID or array of IDs")
    name: str | None = Field(None, description="Name of the target element")
    line_number: int | None = Field(
        None, description="Line number of the target element"
    )
    scope_path: list[ScopePathItem] = Field(
        ..., description="Parent selections leading to this target"
    )
    modifier: TargetModifier | None = Field(None, description="Modifier for target")


class AlgorithmInput(BaseModel):
    """Execution parameters for running the algorithm."""

    entry_function: str = Field(
        ..., description="Name of the entry point function to execute"
    )
    test_data: dict[str, Any] = Field(
        ..., description="Input parameters for the algorithm as key-value pairs"
    )


class GenerateQuestionRequest(BaseModel):
    """Request to generate a question based on form selections."""

    code: str = Field(..., description="Original algorithm source code")
    target: TargetSelection = Field(
        ..., description="The target element to query in the algorithm"
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


class GenerateQuestionResponse(BaseModel):
    """Response containing the generated question."""

    question: str = Field(..., description="The generated question text")
    answer: Any | None = Field(None, description="The answer to the question")
    # Additional fields will be added as the backend implementation evolves
