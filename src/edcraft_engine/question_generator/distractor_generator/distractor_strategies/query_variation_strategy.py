from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, override

from step_tracer import ExecutionContext

from edcraft_engine.question_generator.distractor_generator.distractor_strategies.base_strategy import (
    DistractorStrategy,
)
from edcraft_engine.question_generator.models import (
    OutputType,
    QuestionSpec,
    TargetElement,
    TargetModifier,
)
from edcraft_engine.question_generator.query_generator.query_generator import (
    QueryGenerator,
)

# =========================
# Query Executor Abstraction
# =========================


class QueryExecutor:
    """Executes queries using a query generator."""

    def __init__(self, query_generator_cls: type[QueryGenerator] = QueryGenerator):
        self.query_generator_cls = query_generator_cls

    def execute(
        self,
        exec_ctx: ExecutionContext,
        target: list[TargetElement],
        output_type: OutputType,
    ) -> list[Any]:
        generator = self.query_generator_cls(exec_ctx)
        query = generator.generate_query(target, output_type)
        return list(query.execute())


# =========================
# Internal Data Structure
# =========================


@dataclass(frozen=True)
class QueryVariation:
    target: list[TargetElement]
    output_type: OutputType


# =========================
# Strategy Implementation
# =========================


class QueryVariationStrategy(DistractorStrategy):
    """
    Generates distractors by modifying the query specification:
    - Output type variation
    - Target path variation
    - Modifier variation
    """

    priority: float = 0.9

    def __init__(self, query_executor: QueryExecutor | None = None):
        self.query_executor = query_executor or QueryExecutor()

    @override
    def generate(
        self,
        correct_options: list[Any],
        exec_ctx: ExecutionContext,
        question_spec: QuestionSpec,
        num_distractors: int,
    ) -> list[Any]:
        if not correct_options or num_distractors <= 0:
            return []

        variations = self._build_variations(question_spec)

        candidates: list[Any] = []

        for variation in variations:
            if len(candidates) >= num_distractors:
                break

            try:
                results = self.query_executor.execute(
                    exec_ctx,
                    variation.target,
                    variation.output_type,
                )
            except Exception:
                continue  # safe fallback

            for item in results:
                extracted = self._extract_candidates(correct_options[0], item)

                for candidate in extracted:
                    validated = self._validate_and_format(correct_options[0], candidate)

                    if validated is not None:
                        candidates.append(validated)

        return self._deduplicate(correct_options, candidates)[:num_distractors]

    # =========================
    # Variation Builders
    # =========================

    def _build_variations(self, spec: QuestionSpec) -> list[QueryVariation]:
        return (
            self._output_type_variations(spec)
            + self._target_variations(spec)
            + self._modifier_variations(spec)
        )

    def _output_type_variations(self, spec: QuestionSpec) -> list[QueryVariation]:
        variations: list[QueryVariation] = []

        if spec.output_type in ("first", "last"):
            variations.append(
                QueryVariation(
                    target=spec.target,
                    output_type="list",
                )
            )

        return variations

    def _target_variations(self, spec: QuestionSpec) -> list[QueryVariation]:
        target = spec.target
        variations: list[QueryVariation] = []

        if len(target) <= 1:
            return variations

        # Remove one layer at a time
        for i in range(len(target)):
            modified = target[:i] + target[i + 1 :]
            if modified:
                variations.append(
                    QueryVariation(target=modified, output_type=spec.output_type)
                )

        # Only final element
        variations.append(
            QueryVariation(
                target=[target[-1]],
                output_type=spec.output_type,
            )
        )

        return variations

    def _modifier_variations(self, spec: QuestionSpec) -> list[QueryVariation]:
        variations: list[QueryVariation] = []

        modifier_map: dict[str, list[TargetModifier | None]] = {
            "branch_true": ["branch_false", None],
            "branch_false": ["branch_true", None],
            "loop_iterations": [None],
            "branch": ["branch_true", "branch_false"],
            "loop": ["loop_iterations"],
        }

        for i, element in enumerate(spec.target):
            candidates: list[TargetModifier | None] = []

            if element.modifier and element.modifier in modifier_map:
                candidates = modifier_map[element.modifier]
            elif element.modifier is None and element.type in modifier_map:
                candidates = modifier_map[element.type]

            for new_modifier in candidates:
                modified_target = self._copy_target(spec.target)
                modified_target[i].modifier = new_modifier

                variations.append(
                    QueryVariation(
                        target=modified_target,
                        output_type=spec.output_type,
                    )
                )

        return variations

    # =========================
    # Helpers
    # =========================

    def _copy_target(self, target: list[TargetElement]) -> list[TargetElement]:
        return [element.model_copy(deep=True) for element in target]

    def _format_results(self, ref: Any, results: Iterable[Any]) -> list[Any]:
        formatted: list[Any] = []

        for item in results:
            validated = self._validate_and_format(ref, item)
            if validated is not None:
                formatted.append(validated)

        return formatted

    def _extract_candidates(self, ref: Any, value: Any) -> list[Any]:
        """Extract candidate values from query output."""

        if self._is_internal_object(value):
            return []

        # Scalar expected → flatten
        if not isinstance(ref, list):
            if isinstance(value, list):
                return list(value)
            return [value]

        # List expected
        return [value] if not isinstance(value, list) else value

    def _validate_and_format(self, ref: Any, value: Any) -> Any | None:
        """
        Validate and normalize value to match ref format.
        """

        if self._is_internal_object(value):
            return None

        # Scalar
        if not isinstance(ref, list):
            if isinstance(value, list):
                if len(value) != 1:
                    return None
                value = value[0]

            return value if isinstance(value, type(ref)) else None

        # List
        if not isinstance(value, list):
            value = [value]

        if not ref or not value:
            return None

        # Enforce same length
        if len(ref) != len(value):
            return None

        ref_elem = ref[0]

        for v in value:
            if not isinstance(v, type(ref_elem)):
                return None

        return value

    def _is_internal_object(self, value: Any) -> bool:
        """Reject engine-specific objects."""
        return hasattr(value, "__dict__") and not isinstance(
            value, (int, float, str, list, dict, tuple, bool)
        )

    def _deduplicate(
        self, correct_options: list[Any], distractors: list[Any]
    ) -> list[Any]:
        seen = {str(opt) for opt in correct_options}
        unique: list[Any] = []

        for d in distractors:
            key = str(d)
            if key not in seen:
                seen.add(key)
                unique.append(d)

        return unique
