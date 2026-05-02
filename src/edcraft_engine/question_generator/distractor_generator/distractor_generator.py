from collections.abc import Iterable
from typing import Any

from step_tracer import ExecutionContext

from edcraft_engine.question_generator.distractor_generator.distractor_strategies import (
    DistractorStrategy,
    OutputModificationStrategy,
    QueryVariationStrategy,
)
from edcraft_engine.question_generator.models import QuestionSpec


class DistractorGenerator:
    def __init__(
        self,
        strategies: list[DistractorStrategy] | None = None,
    ):
        self.strategies = strategies or [
            OutputModificationStrategy(),
            QueryVariationStrategy(),
        ]

    def generate_distractors(
        self,
        correct_options: list[Any],
        exec_ctx: ExecutionContext,
        question_spec: QuestionSpec,
        num_distractors: int,
    ) -> list[Any]:
        """Generate unique distractors using multiple strategies."""

        strategies = sorted(
            self.strategies,
            key=lambda s: s.score(),
            reverse=True,
        )

        if num_distractors <= 0:
            return []

        seen = {self._key(opt) for opt in correct_options}
        distractors: list[Any] = []

        for strategy in strategies:
            if len(distractors) >= num_distractors:
                break

            generated = strategy.generate(
                correct_options=correct_options,
                exec_ctx=exec_ctx,
                question_spec=question_spec,
                num_distractors=num_distractors - len(distractors),
            )

            self._accumulate(distractors, seen, generated, num_distractors)

        return distractors[:num_distractors]

    def _accumulate(
        self,
        distractors: list[Any],
        seen: set[str],
        candidates: Iterable[Any],
        limit: int,
    ) -> None:
        for item in candidates:
            if len(distractors) >= limit:
                break

            key = self._key(item)
            if item is not None and key not in seen:
                distractors.append(item)
                seen.add(key)

    def _key(self, value: Any) -> str:
        return str(value)
