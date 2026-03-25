import random
from typing import Any, cast, override

from step_tracer import ExecutionContext

from edcraft_engine.question_generator.distractor_generator.distractor_strategies.base_strategy import (
    DistractorStrategy,
)
from edcraft_engine.question_generator.models import QuestionSpec


class OutputModificationStrategy(DistractorStrategy):

    @override
    def generate(
        self,
        correct_options: list[Any],
        exec_ctx: ExecutionContext,
        question_spec: QuestionSpec,
        num_distractors: int,
    ) -> list[Any]:
        distractors: list[Any] = []
        seen: set[str] = {str(opt) for opt in correct_options}
        for correct_option in correct_options:
            if len(distractors) >= num_distractors:
                break
            for var in self._generate_variations(
                correct_option, num_distractors - len(distractors)
            ):
                self._add_distractor(distractors, seen, var)
        return distractors[:num_distractors]

    def _generate_variations(self, item: Any, num_needed: int) -> list[Any]:
        if isinstance(item, int):
            return self._generate_numeric_variations(item, num_needed)
        elif isinstance(item, list):
            return self._generate_list_variations(cast(list[Any], item), num_needed)
        elif isinstance(item, dict):
            return self._generate_dict_variations(
                cast(dict[Any, Any], item), num_needed
            )
        return []

    def _generate_list_variations(
        self,
        correct_option: list[Any],
        num_needed: int,
    ) -> list[Any]:
        variations: list[Any] = []
        for _ in range(min(3, num_needed)):
            permuted = correct_option.copy()
            random.shuffle(permuted)
            variations.append(permuted)
        return variations

    def _generate_numeric_variations(
        self,
        correct_option: int,
        num_needed: int,
        max_variation: int = 3,
    ) -> list[Any]:
        variations: list[Any] = (
            []
        )  # in order of closest to farthest from correct answer
        seen: set[int] = {correct_option}

        def add_variation(val: int) -> None:
            if val not in seen:
                if correct_option < 0 and val >= 0:
                    return
                if correct_option >= 0 and val < 0:
                    return
                variations.append(val)
                seen.add(val)

        for diff in range(1, max_variation + 1):
            add_variation(correct_option - diff)
            add_variation(correct_option + diff)
            if len(variations) >= num_needed:
                break

        return variations[:num_needed]

    def _generate_dict_variations(
        self,
        correct_option: dict[Any, Any],
        num_needed: int,
    ) -> list[Any]:
        variations: list[Any] = []

        for key, value in correct_option.items():
            if isinstance(value, int):
                for var in self._generate_numeric_variations(
                    value, num_needed, max_variation=1
                ):
                    variations.append({**correct_option, key: var})
            elif isinstance(value, list):
                for var in self._generate_list_variations(
                    cast(list[Any], value), num_needed - len(variations)
                ):
                    variations.append({**correct_option, key: var})

        random.shuffle(variations)
        return variations[:num_needed]

    def _add_distractor(
        self,
        current_distractors: list[Any],
        seen: set[str],
        incoming_distractor: Any,
    ) -> None:
        incoming_distractor_str = str(incoming_distractor)
        if incoming_distractor is not None and incoming_distractor_str not in seen:
            current_distractors.append(incoming_distractor)
            seen.add(incoming_distractor_str)
