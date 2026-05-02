from abc import ABC, abstractmethod
from typing import Any

from step_tracer import ExecutionContext

from edcraft_engine.question_generator.models import QuestionSpec


class DistractorStrategy(ABC):
    """Abstract base class for distractor generation strategies."""

    priority: float = 0.0

    def score(self) -> float:
        """Optional dynamic scoring override."""
        return self.priority

    @abstractmethod
    def generate(
        self,
        correct_options: list[Any],
        exec_ctx: ExecutionContext,
        question_spec: QuestionSpec,
        num_distractors: int,
    ) -> list[Any]:
        pass
