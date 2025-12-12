import random
from typing import Any

# from edcraft_engine.question_generator.distractor_strategies.query_variation_strategy import (
#     QueryVariationStrategy,
# )
from edcraft_engine.models.question_models import GenerateQuestionRequest
from edcraft_engine.models.tracer_models import ExecutionContext
from edcraft_engine.question_generator.distractor_strategies.base_strategy import (
    DistractorStrategy,
)
from edcraft_engine.question_generator.distractor_strategies.output_modification_strategy import (
    OutputModificationStrategy,
)


class DistractorGenerator:
    def __init__(
        self,
        exec_ctx: ExecutionContext,
        request: GenerateQuestionRequest,
        strategies: list[DistractorStrategy] | None = None,
    ):
        self.exec_ctx = exec_ctx
        self.request = request
        self.strategies = strategies or [
            # QueryVariationStrategy(), # todo: re-enable after enhancing
            OutputModificationStrategy(),
        ]

    def create_options(self, answers: Any) -> tuple[list[Any], list[int]]:
        """
        Create shuffled options including the correct answer and distractors.

        Args:
            answers: The correct answers to the question

        Returns:
            Tuple of (shuffled_options, correct_indices)
            - shuffled_options: List of all options (correct + distractors) in random order
            - correct_indices: Indices of correct answer(s) in the shuffled list
        """

        correct_options = answers if self.request.question_type == "mrq" else [answers]
        distractors = self.generate_distractors(correct_options)
        all_options = correct_options + distractors
        return self._shuffle(all_options, len(correct_options))

    def generate_distractors(self, correct_options: list[Any]) -> list[Any]:
        """Generate distractors using the defined strategies."""

        distractors: list[Any] = []
        seen: set[str] = set()
        for option in correct_options:
            seen.add(str(option))

        for strategy in self.strategies:
            if len(distractors) >= self.request.num_distractors:
                break
            generated_distractors = strategy.generate(
                correct_options=correct_options,
                exec_ctx=self.exec_ctx,
                request=self.request,
                num_distractors=self.request.num_distractors,
            )

            for distractor in generated_distractors:
                distractor_str = str(distractor)
                if distractor is not None and distractor_str not in seen:
                    distractors.append(distractor)
                    seen.add(distractor_str)
                if len(distractors) >= self.request.num_distractors:
                    break

        return distractors[: self.request.num_distractors]

    def _shuffle(
        self, options: list[Any], num_correct: int
    ) -> tuple[list[Any], list[int]]:
        """
        Shuffle options while tracking where correct answers end up.

        Args:
            options: List where first num_correct items are correct answers
            num_correct: Number of correct answers at the start of the list

        Returns:
            Tuple of (shuffled_options, correct_indices)
        """
        indexed_options = [(i, option) for i, option in enumerate(options)]

        random.shuffle(indexed_options)

        shuffled_options = [option for _, option in indexed_options]
        correct_indices = [
            new_idx
            for new_idx, (old_idx, _) in enumerate(indexed_options)
            if old_idx < num_correct
        ]

        return shuffled_options, correct_indices
