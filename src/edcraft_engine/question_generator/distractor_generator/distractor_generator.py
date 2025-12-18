from typing import Any

from edcraft_engine.question_generator.distractor_generator.distractor_strategies.base_strategy import (
    DistractorStrategy,
)
from edcraft_engine.question_generator.distractor_generator.distractor_strategies.output_modification_strategy import (
    OutputModificationStrategy,
)

# from edcraft_engine.question_generator.distractor_generator.distractor_strategies.query_variation_strategy import (
#     QueryVariationStrategy,
# )
from edcraft_engine.question_generator.models import QuestionSpec
from edcraft_engine.step_tracer.models import ExecutionContext


class DistractorGenerator:
    def __init__(
        self,
        strategies: list[DistractorStrategy] | None = None,
    ):
        self.strategies = strategies or [
            # QueryVariationStrategy(), # todo: re-enable after enhancing
            OutputModificationStrategy(),
        ]

    def generate_distractors(
        self,
        correct_options: list[Any],
        exec_ctx: ExecutionContext,
        question_spec: QuestionSpec,
        num_distractors: int,
    ) -> list[Any]:
        """Generate distractors using the defined strategies."""

        distractors: list[Any] = []
        seen: set[str] = set()
        for option in correct_options:
            seen.add(str(option))

        for strategy in self.strategies:
            if len(distractors) >= num_distractors:
                break
            generated_distractors = strategy.generate(
                correct_options=correct_options,
                exec_ctx=exec_ctx,
                question_spec=question_spec,
                num_distractors=num_distractors,
            )

            for distractor in generated_distractors:
                distractor_str = str(distractor)
                if distractor is not None and distractor_str not in seen:
                    distractors.append(distractor)
                    seen.add(distractor_str)
                if len(distractors) >= num_distractors:
                    break

        return distractors[:num_distractors]
