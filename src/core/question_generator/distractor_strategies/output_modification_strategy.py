import random
from typing import Any, cast, override

from src.core.question_generator.distractor_strategies.base_strategy import (
    DistractorStrategy,
)
from src.models.api_models import GenerateQuestionRequest
from src.models.tracer_models import ExecutionContext


class OutputModificationStrategy(DistractorStrategy):

    @override
    def generate(
        self,
        correct_options: list[Any],
        exec_ctx: ExecutionContext,
        request: GenerateQuestionRequest,
        num_distractors: int,
    ) -> list[Any]:
        if request.question_type == "mcq":
            return self._generate_mcq_distractors(correct_options[0], num_distractors)
        elif request.question_type == "mrq":
            return self._generate_mrq_distractors(correct_options, num_distractors)
        else:
            return []

    def _generate_mcq_distractors(
        self, correct_option: Any, num_needed: int
    ) -> list[Any]:
        distractors: list[Any] = []
        seen: set[str] = set()
        seen.add(str(correct_option))

        for idx, item in enumerate(correct_option):
            if len(distractors) >= num_needed:
                break

            if isinstance(item, int):
                variations = self._generate_numeric_variations(
                    item, num_needed - len(distractors)
                )

                for var in variations:
                    new_option = correct_option.copy()
                    new_option[idx] = var
                    self._add_distractor(distractors, seen, new_option)

            elif isinstance(item, list):
                item = cast(list[Any], item)
                variations = self._generate_list_variations(
                    item, num_needed - len(distractors)
                )

                for var in variations:
                    new_option = correct_option.copy()
                    new_option[idx] = var
                    self._add_distractor(distractors, seen, new_option)

            elif isinstance(item, dict):
                item = cast(dict[Any, Any], item)
                variations = self._generate_dict_variations(
                    item, num_needed - len(distractors)
                )

                for var in variations:
                    new_option = correct_option.copy()
                    new_option[idx] = var
                    self._add_distractor(distractors, seen, new_option)

        return distractors[:num_needed]

    def _generate_mrq_distractors(
        self,
        correct_options: list[Any],
        num_needed: int,
    ) -> list[Any]:
        distractors: list[Any] = []
        seen: set[str] = set()
        for option in correct_options:
            seen.add(str(option))

        for correct_option in correct_options:
            if len(distractors) >= num_needed:
                break

            if isinstance(correct_option, list):
                correct_option = cast(list[Any], correct_option)
                variations = self._generate_list_variations(
                    correct_option, num_needed - len(distractors)
                )
                for var in variations:
                    self._add_distractor(distractors, seen, var)
            elif isinstance(correct_option, int):
                variations = self._generate_numeric_variations(
                    correct_option, num_needed - len(distractors)
                )
                for var in variations:
                    self._add_distractor(distractors, seen, var)
            elif isinstance(correct_option, dict):
                correct_option = cast(dict[Any, Any], correct_option)
                variations = self._generate_dict_variations(
                    correct_option, num_needed - len(distractors)
                )
                for var in variations:
                    self._add_distractor(distractors, seen, var)

        return distractors[:num_needed]

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
        seen: set[int] = set()
        seen.add(correct_option)

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
                value = cast(list[Any], value)
                for var in self._generate_list_variations(
                    value, num_needed - len(variations)
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
