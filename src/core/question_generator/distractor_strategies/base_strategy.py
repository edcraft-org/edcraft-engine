from abc import ABC, abstractmethod
from typing import Any

from src.models.api_models import GenerateQuestionRequest
from src.models.tracer_models import ExecutionContext


class DistractorStrategy(ABC):
    """Abstract base class for distractor generation strategies."""

    @abstractmethod
    def generate(
        self,
        correct_options: list[Any],
        exec_ctx: ExecutionContext,
        request: GenerateQuestionRequest,
        num_distractors: int,
    ) -> list[Any]:
        pass
