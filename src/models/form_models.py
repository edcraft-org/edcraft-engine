from typing import Any

from pydantic import BaseModel, Field


class FunctionElement(BaseModel):
    """Model representing a function element in the code."""

    name: str = Field(..., description="Name of the function.")
    type: str = Field("function", description="Type of the code element.")
    line_number: int = Field(
        ..., description="Line number where the function is defined."
    )
    parameters: list[str] = Field(
        ..., description="List of parameters for the function."
    )
    is_definition: bool = Field(
        ..., description="Indicates if this is a function definition."
    )


class LoopElement(BaseModel):
    """Model representing a loop element in the code."""

    type: str = Field("loop", description="Type of the code element.")
    line_number: int = Field(..., description="Line number where the loop is located.")
    loop_type: str = Field(..., description="Type of the loop (e.g., for, while).")
    condition: str = Field(..., description="Condition of the loop.")


class BranchElement(BaseModel):
    """Model representing a branch element in the code."""

    type: str = Field("branch", description="Type of the code element.")
    line_number: int = Field(
        ..., description="Line number where the branch is located."
    )
    condition: str = Field(..., description="Condition of the branch.")


class CodeTree(BaseModel):
    """Model representing a node in the code tree."""

    id: int = Field(..., description="Unique identifier for the code element.")
    type: str = Field(
        ..., description="Type of the code element (function, loop, branch)."
    )
    variables: list[str] = Field(
        ..., description="List of variable names in the current code element."
    )
    function_indices: list[int] = Field(
        ..., description="List of indices of functions within this code element."
    )
    loop_indices: list[int] = Field(
        ..., description="List of indices of loops within this code element."
    )
    branch_indices: list[int] = Field(
        ..., description="List of indices of branches within this code element."
    )
    children: list["CodeTree"] = Field(..., description="List of child code elements.")


class CodeInfo(BaseModel):
    """Model representing code structure and code elements."""

    code_tree: CodeTree = Field(
        ..., description="A hierarchical representation of the code structure."
    )
    functions: list[FunctionElement] = Field(
        ..., description="List of available functions in the code."
    )
    loops: list[LoopElement] = Field(
        ..., description="List of available loops in the code."
    )
    branches: list[BranchElement] = Field(
        ..., description="List of available branches in the code."
    )
    variables: list[str] = Field(
        ..., description="List of variable names used in the code."
    )


class FormOption(BaseModel):
    """A form option with its details."""

    id: str = Field(..., description="Unique identifier for the form option.")
    label: str = Field(..., description="Display label")
    value: Any = Field(..., description="Option value")
    description: str = Field(..., description="Description of the form option.")
    depends_on: str | None = Field(
        default=None, description="Id of the option that this option depends on."
    )


class FormElement(BaseModel):
    """A form element with available options."""

    element_type: str = Field(..., description="Type of the form element")
    label: str = Field(..., description="Display label for this element")
    description: str | None = Field(None, description="Help text")
    options: list[FormOption] = Field(..., description="Available options")
    is_required: bool = Field(default=True, description="Whether selection is required")


class FormSchema(BaseModel):
    """Schema representing the form structure."""

    code_info: CodeInfo = Field(
        ..., description="Code structure and elements information."
    )
    form_elements: list[FormElement] = Field(..., description="List of form elements.")
