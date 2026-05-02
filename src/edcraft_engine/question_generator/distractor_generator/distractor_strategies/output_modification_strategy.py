import random
from collections.abc import Callable
from typing import Any, override

from step_tracer import ExecutionContext

from edcraft_engine.question_generator.distractor_generator.distractor_strategies.base_strategy import (
    DistractorStrategy,
)
from edcraft_engine.question_generator.models import QuestionSpec

VariationHandler = Callable[[Any, int], list[Any]]


class OutputModificationStrategy(DistractorStrategy):
    """Generates distractors by modifying correct outputs."""

    priority: float = 0.5

    def __init__(self) -> None:
        self._registry: dict[type, VariationHandler] = {
            int: self._numeric,
            list: self._list,
            dict: self._dict,
        }

    @override
    def generate(
        self,
        correct_options: list[Any],
        exec_ctx: ExecutionContext,
        question_spec: QuestionSpec,
        num_distractors: int,
    ) -> list[Any]:
        if num_distractors <= 0:
            return []

        distractors: list[Any] = []
        seen: set[str] = {self._key(opt) for opt in correct_options}

        for option in correct_options:
            variations = self._generate_variations(option, num_distractors)

            for var in variations:
                key = self._key(var)

                if var is not None and key not in seen:
                    distractors.append(var)
                    seen.add(key)

                if len(distractors) >= num_distractors:
                    return distractors

        return distractors

    # =========================
    # Core Dispatcher
    # =========================

    def _generate_variations(self, item: Any, limit: int) -> list[Any]:
        handler = self._registry.get(type(item))
        if handler:
            return handler(item, limit)
        return []

    # =========================
    # List Handling
    # =========================

    def _list(self, value: list[Any], limit: int) -> list[Any]:
        variations: list[Any] = []

        # Permutations
        for perm in self._list_permutations(value, limit):
            variations.append(perm)
            if len(variations) >= limit:
                return variations

        # Modify elements recursively
        for i, elem in enumerate(value):
            sub_variations = self._generate_variations(elem, limit)

            for sv in sub_variations:
                new_list = value.copy()
                new_list[i] = sv
                variations.append(new_list)

                if len(variations) >= limit:
                    return variations

        return variations

    # =========================
    # Dict Handling
    # =========================

    def _dict(self, value: dict[Any, Any], limit: int) -> list[Any]:
        variations: list[Any] = []

        for key, val in value.items():
            sub_variations = self._generate_variations(val, limit)

            for sv in sub_variations:
                new_dict = dict(value)
                new_dict[key] = sv
                variations.append(new_dict)

                if len(variations) >= limit:
                    return variations

        return variations

    # =========================
    # Numeric Variations
    # =========================

    def _numeric(self, value: int, limit: int) -> list[Any]:
        variations: list[int] = []
        seen: set[int] = {value}

        for diff in range(1, limit + 3):
            for candidate in (value - diff, value + diff):
                if candidate in seen:
                    continue

                # Preserve sign
                if (value >= 0 and candidate < 0) or (value < 0 and candidate >= 0):
                    continue

                variations.append(candidate)
                seen.add(candidate)

                if len(variations) >= limit:
                    return variations

        return variations

    # =========================
    # Permutations
    # =========================

    def _list_permutations(self, value: list[Any], limit: int) -> list[list[Any]]:
        variations: list[list[Any]] = []
        attempts = 0

        while len(variations) < limit and attempts < limit * 3:
            permuted = value.copy()
            random.shuffle(permuted)

            if permuted != value and permuted not in variations:
                variations.append(permuted)

            attempts += 1

        return variations

    # =========================
    # Utilities
    # =========================

    def _key(self, value: Any) -> str:
        return str(value)
