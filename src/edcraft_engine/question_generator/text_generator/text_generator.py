from collections.abc import Callable
from typing import Any

from edcraft_engine.question_generator.models import (
    QuestionSpec,
    QuestionType,
    TargetElement,
)


class TextGenerator:
    # -----------------------------
    # Maps
    # -----------------------------

    QUESTION_TYPE_MAP: dict[str, str] = {
        "mcq": "Choose the correct option.",
        "mrq": "Select all that apply.",
    }

    QUANTIFIER_MAP: dict[str, str] = {
        "first": "the first",
        "last": "the last",
        "list": "each",
    }

    VARIABLE_TEMPLATES: dict[str, str] = {
        "count": "how many times was the variable `{name}` modified",
        "first": "what is the value of the variable `{name}` at the beginning",
        "last": "what is the value of the variable `{name}` at the end",
        "list": "what are the values of the variable `{name}`",
    }

    BRANCH_QUESTION_MAP: dict[str, str] = {
        "count": "how many times do",
        "list": "what are the times",
        "first": "what is the first time",
        "last": "what is the last time",
    }

    BRANCH_CONDITION_MAP: dict[str, str] = {
        "branch_true": " when the condition is true",
        "branch_false": " when the condition is false",
    }

    # -----------------------------
    # Public API
    # -----------------------------

    def generate_question(
        self,
        question_spec: QuestionSpec,
        input_data: dict[str, Any] | None = None,
    ) -> str:
        """Generates a question text based on the provided request."""

        context = self._build_context(question_spec.target[:-1])
        target_phrase = self._build_target(
            question_spec.target[-1], question_spec.output_type
        )
        question_type_phrase = self._build_question_type(question_spec.question_type)

        base = f"{context}, {target_phrase}? {question_type_phrase}"

        if not input_data:
            return base

        input_data_phrase = self._build_input_data_phrase(input_data)
        return f"{base}\nGiven input: {input_data_phrase}"

    # -----------------------------
    # Context Builders
    # -----------------------------

    def _build_context(self, targets: list[TargetElement]) -> str:
        context_parts: list[str] = []

        for target in targets:
            builder = self._context_builders().get(target.type)
            if builder:
                context_parts.extend(builder(target))

        if context_parts:
            context_parts[0] = context_parts[0].capitalize()
            return ", ".join(context_parts)

        return "During execution"

    def _context_builders(self) -> dict[str, Callable[[TargetElement], list[str]]]:
        return {
            "function": self._context_function,
            "loop": self._context_loop,
            "branch": self._context_branch,
        }

    def _context_function(self, target: TargetElement) -> list[str]:
        func_name = target.name or "function"
        line_info = f" (line {target.line_number})" if target.line_number else ""
        return [f"for each `{func_name}()` call{line_info}"]

    def _context_loop(self, target: TargetElement) -> list[str]:
        if target.modifier == "loop_iterations":
            if target.line_number:
                return [f"for each loop iteration (line {target.line_number})"]
            return ["for each loop iteration"]
        else:
            if target.line_number:
                return [f"in the loop at line {target.line_number}"]
            return ["in the loop"]

    def _context_branch(self, target: TargetElement) -> list[str]:
        parts = [f"in each `{target.name}` branch (line {target.line_number})"]
        if target.modifier:
            condition = "true" if target.modifier == "branch_true" else "false"
            parts.append(f"when the condition is {condition}")
        return parts

    # -----------------------------
    # Target Builders
    # -----------------------------

    def _target_builders(self) -> dict[str, Callable[[TargetElement, str], str]]:
        return {
            "function": self._build_func_target,
            "loop": self._build_loop_target,
            "branch": self._build_branch_target,
            "variable": self._build_variable_target,
        }

    def _build_target(self, target: TargetElement, output_type: str) -> str:
        builder = self._target_builders().get(target.type)
        if not builder:
            return "unknown target"
        return builder(target, output_type)

    def _get_quantifier(self, output_type: str) -> str:
        return self.QUANTIFIER_MAP.get(output_type, "each")

    def _build_func_target(self, target: TargetElement, output_type: str) -> str:
        name = target.name
        modifier = target.modifier

        if output_type == "count":
            count_templates = {
                "arguments": "how many unique sets of arguments were passed to function `{name}()`",
                "return_value": "how many unique return values were produced by function `{name}()`",
                None: "how many times was function `{name}()` called",
            }
            template = count_templates.get(modifier, count_templates[None])
            return template.format(name=name)

        quantifier = self._get_quantifier(output_type)

        def format_args_keys() -> str:
            if not target.argument_keys:
                return ""
            return f" ({', '.join(target.argument_keys)})"

        templates = {
            ("arguments", "default"): (
                "what are the arguments{keys} passed to {quantifier} function `{name}()` call"
            ),
            ("return_value", "default"): (
                "what is the return value of {quantifier} function `{name}()` call"
            ),
            (None, "list"): "what are the function `{name}()` calls",
            (None, "default"): "what is {quantifier} function `{name}()` call",
        }

        key = (modifier, output_type if output_type == "list" else "default")
        template = templates.get(key, templates[(None, "default")])

        return template.format(
            name=name,
            quantifier=quantifier,
            keys=format_args_keys(),
        )

    def _build_loop_target(self, target: TargetElement, output_type: str) -> str:
        line = f" (line {target.line_number})" if target.line_number else ""

        if target.modifier == "loop_iterations":
            templates = {
                "count": "how many loop iterations are there in each loop execution{line}",
                "first": "what is the first loop iteration for each loop execution{line}",
                "last": "what is the last loop iteration for each loop execution{line}",
                "list": "what are the loop iterations for each loop execution{line}",
            }
        else:
            templates = {
                "count": "how many times does the loop{line} execute",
                "first": "what is the first execution of the loop{line}",
                "last": "what is the last execution of the loop{line}",
                "list": "what are the executions of the loop{line}",
            }

        template = templates.get(output_type, templates["list"])
        return template.format(line=line)

    def _build_branch_target(self, target: TargetElement, output_type: str) -> str:
        question = self.BRANCH_QUESTION_MAP.get(output_type, "what is the last time")
        condition = (
            self.BRANCH_CONDITION_MAP.get(target.modifier, "")
            if target.modifier
            else ""
        )

        return (
            f"{question} we enter the branch `{target.name}` "
            f"(line {target.line_number}){condition}"
        )

    def _build_variable_target(self, target: TargetElement, output_type: str) -> str:
        template = self.VARIABLE_TEMPLATES.get(
            output_type, self.VARIABLE_TEMPLATES["list"]
        )
        return template.format(name=target.name)

    # -----------------------------
    # Question Type Builder
    # -----------------------------

    def _build_question_type(self, question_type: QuestionType) -> str:
        return self.QUESTION_TYPE_MAP.get(question_type, "Provide the answer.")

    # -----------------------------
    # Input Data Builder
    # -----------------------------

    def _build_input_data_phrase(self, input_data: dict[str, Any]) -> str:
        if not input_data:
            return ""

        parts: list[str] = []
        for key, value in input_data.items():
            if isinstance(value, str):
                parts.append(f'{key} = "{value}"')
            else:
                parts.append(f"{key} = {value}")

        return ", ".join(parts)
