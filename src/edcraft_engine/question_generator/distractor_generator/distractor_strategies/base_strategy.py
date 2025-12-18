from abc import ABC, abstractmethod
from typing import Any

from edcraft_engine.question_generator.models import QuestionSpec
from edcraft_engine.step_tracer.models import ExecutionContext


class DistractorStrategy(ABC):
    """Abstract base class for distractor generation strategies."""

    @abstractmethod
    def generate(
        self,
        correct_options: list[Any],
        exec_ctx: ExecutionContext,
        question_spec: QuestionSpec,
        num_distractors: int,
    ) -> list[Any]:
        pass
