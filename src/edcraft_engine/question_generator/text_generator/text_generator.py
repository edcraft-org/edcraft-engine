from typing import Any

from edcraft_engine.question_generator.models import (
    QuestionSpec,
    QuestionType,
    TargetElement,
)


class TextGenerator:
    def generate_question(
        self,
        question_spec: QuestionSpec,
        input_data: dict[str, Any],
    ) -> str:
        """Generates a question text based on the provided request."""

        # Build the question parts
        context = self._build_context(question_spec.target[:-1])
        target_phrase = self._build_target(
            question_spec.target[-1], question_spec.output_type
        )
        question_type_phrase = self._build_question_type(question_spec.question_type)
        input_data_phrase = self._build_input_data_phrase(input_data)

        # Compose the final question
        question = f"{context}, {target_phrase}? {question_type_phrase}\nGiven input: {input_data_phrase}"
        return question

    def _build_context(self, targets: list[TargetElement]) -> str:
        """Build the context phrase that describes where/when to look."""

        context_parts: list[str] = []

        # Process targets in order to build hierarchical context
        for target in targets:
            if target.type == "function":
                func_name = target.name if target.name else "function"
                line_info = (
                    f" (line {target.line_number})" if target.line_number else ""
                )
                context_parts.append(f"for each `{func_name}()` call{line_info}")

            elif target.type == "loop":
                if target.modifier == "loop_iterations":
                    if target.line_number:
                        context_parts.append(
                            f"for each loop iteration (line {target.line_number})"
                        )
                    else:
                        context_parts.append("for each loop iteration")
                else:
                    if target.line_number:
                        context_parts.append(
                            f"in the loop at line {target.line_number}"
                        )
                    else:
                        context_parts.append("in the loop")

            elif target.type == "branch":
                context_parts.append(
                    f"in each `{target.name}` branch (line {target.line_number})"
                )
                if target.modifier:
                    condition_str = (
                        "true" if target.modifier == "branch_true" else "false"
                    )
                    context_parts.append(f"when the condition is {condition_str}")

        # If we have context parts, join them with commas
        if context_parts:
            # Capitalize the first letter
            context_parts[0] = context_parts[0][0].upper() + context_parts[0][1:]
            return ", ".join(context_parts)

        return "During execution"

    def _build_target(self, target: TargetElement, output_type: str) -> str:
        """Build the target phrase that describes what to query."""
        if target.type == "function":
            return self._build_func_target(target, output_type)
        elif target.type == "loop":
            return self._build_loop_target(target, output_type)
        elif target.type == "branch":
            return self._build_branch_target(target, output_type)
        elif target.type == "variable":
            return self._build_variable_target(target, output_type)
        else:
            return "unknown target"

    def _build_func_target(self, target: TargetElement, output_type: str) -> str:
        """Build the target for function type targets."""
        if output_type == "count":
            if target.modifier == "arguments":
                return f"how many unique sets of arguments were passed to function `{target.name}()`"
            elif target.modifier == "return_value":
                return f"how many unique return values were produced by function `{target.name}()`"
            return f"how many times was function `{target.name}()` called"

        if output_type == "first":
            quantifier = "the first"
        elif output_type == "last":
            quantifier = "the last"
        else:
            quantifier = "each"

        if target.modifier == "arguments":
            return f"what are the arguments passed to {quantifier} function `{target.name}()` call"
        elif target.modifier == "return_value":
            return f"what is the return value of {quantifier} function `{target.name}()` call"
        else:
            if output_type == "list":
                return f"what are the function `{target.name}()` calls"
            return f"what is {quantifier} function `{target.name}()` call"

    def _build_loop_target(self, target: TargetElement, output_type: str) -> str:
        """Build the target for loop type targets."""
        if target.modifier == "loop_iterations":
            if output_type == "count":
                return f"how many loop iterations are there in each loop execution (line {target.line_number})"
            elif output_type == "first":
                return f"what is the first loop iteration for each loop execution (line {target.line_number})"
            elif output_type == "last":
                return f"what is the last loop iteration for each loop execution (line {target.line_number})"
            else:
                return f"what are the loop iterations for each loop execution (line {target.line_number})"
        else:
            if output_type == "count":
                return (
                    f"how many times does the loop (line {target.line_number}) execute"
                )
            elif output_type == "first":
                return f"what is the first execution of the loop (line {target.line_number})"
            elif output_type == "last":
                return f"what is the last execution of the loop (line {target.line_number})"
            else:
                return (
                    f"what are the executions of the loop (line {target.line_number})"
                )

    def _build_branch_target(self, target: TargetElement, output_type: str) -> str:
        """Build the target for branch type targets."""
        if output_type == "count":
            question = "how many times do"
        elif output_type == "list":
            question = "what are the times"
        elif output_type == "first":
            question = "what is the first time"
        else:
            question = "what is the last time"

        if target.modifier == "branch_true":
            context = " when the condition is true"
        elif target.modifier == "branch_false":
            context = " when the condition is false"
        else:
            context = ""

        return f"{question} we enter the branch `{target.name}` (line {target.line_number}){context}"

    def _build_variable_target(self, target: TargetElement, output_type: str) -> str:
        """Build the target for variable type targets."""
        if output_type == "count":
            return f"how many times was the variable `{target.name}` modified"
        elif output_type == "first":
            return f"what is the value of the variable `{target.name}` at the beginning"
        elif output_type == "last":
            return f"what is the value of the variable `{target.name}` at the end"
        else:
            return f"what are the values of the variable `{target.name}`"

    def _build_question_type(self, question_type: QuestionType) -> str:
        """Build the question type phrase."""
        if question_type == "mcq":
            return "Choose the correct option."
        elif question_type == "mrq":
            return "Select all that apply."
        else:
            return "Provide the answer."

    def _build_input_data_phrase(self, input_data: dict[str, Any]) -> str:
        """
        Format the input data for display.

        For example: "arr = [5, 2, 8, 1]"
        """
        if not input_data:
            return ""

        parts: list[str] = []
        for key, value in input_data.items():
            if isinstance(value, str):
                parts.append(f'{key} = "{value}"')
            else:
                parts.append(f"{key} = {value}")

        return ", ".join(parts)
