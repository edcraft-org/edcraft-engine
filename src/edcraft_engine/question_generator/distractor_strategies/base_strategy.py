from abc import ABC, abstractmethod
from typing import Any

from edcraft_engine.question_generator.models import (
    OutputType,
    QuestionType,
    TargetElement,
)
from edcraft_engine.step_tracer.models import ExecutionContext


class DistractorStrategy(ABC):
    """Abstract base class for distractor generation strategies."""

    @abstractmethod
    def generate(
        self,
        correct_options: list[Any],
        exec_ctx: ExecutionContext,
        target: list[TargetElement],
        output_type: OutputType,
        question_type: QuestionType,
        num_distractors: int,
    ) -> list[Any]:
        pass
