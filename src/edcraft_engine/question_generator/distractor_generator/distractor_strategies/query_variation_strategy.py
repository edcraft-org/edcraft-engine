import copy
from typing import Any, cast, override

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


class QueryVariationStrategy(DistractorStrategy):
    """Generates distractors by varying the original question's query."""

    @override
    def generate(
        self,
        correct_options: list[Any],
        exec_ctx: ExecutionContext,
        question_spec: QuestionSpec,
        num_distractors: int,
    ) -> list[Any]:
        distractors: list[Any] = []

        # Vary output type
        distractors.extend(
            self._generate_output_type_variations(
                exec_ctx, question_spec.target, question_spec.output_type
            )
        )

        # Vary target path (remove context layers)
        distractors.extend(
            self._generate_target_path_variations(
                correct_options,
                exec_ctx,
                question_spec.target,
                question_spec.output_type,
                num_distractors,
            )
        )

        # Vary modifiers
        distractors.extend(
            self._generate_modifier_variations(
                correct_options,
                exec_ctx,
                question_spec.target,
                question_spec.output_type,
                num_distractors,
            )
        )

        # Match answer format
        formatted_distractors: list[Any] = []
        for dist in distractors:
            dist = self._match_answer_format(correct_options[0], dist)
            if dist is not None:
                formatted_distractors.append(dist)
        distractors = formatted_distractors

        # Deduplicate distractors
        distractors = self._deduplicate_distractors(correct_options, distractors)

        return distractors[:num_distractors]

    def _generate_output_type_variations(
        self,
        exec_ctx: ExecutionContext,
        target: list[TargetElement],
        output_type: OutputType,
    ) -> list[Any]:
        """Generate distractors by varying the output type."""
        if output_type not in ("first", "last"):
            return []

        try:
            modified_query_result = self._run_modified_query(
                target, output_type, exec_ctx, modified_output_type="list"
            )
            return modified_query_result
        except Exception:
            return []

    def _generate_target_path_variations(
        self,
        correct_answers: list[Any],
        exec_ctx: ExecutionContext,
        target: list[TargetElement],
        output_type: OutputType,
        num_distractors: int,
    ) -> list[Any]:
        """Generate distractors by varying the target path (removing context layers)."""
        distractors: list[Any] = []

        if len(target) <= 1:
            # No context to remove
            return distractors

        for i in range(len(target) - 1):
            modified_target = target[:i] + target[i + 1 :]
            self._run_and_clean_modified_query(
                correct_answers[0],
                distractors,
                target,
                output_type,
                exec_ctx,
                modified_target,
                num_distractors,
            )
            if len(distractors) >= num_distractors:
                break

        # Only include final target element
        modified_target = [target[-1]]
        self._run_and_clean_modified_query(
            correct_answers[0],
            distractors,
            target,
            output_type,
            exec_ctx,
            modified_target,
            num_distractors,
        )

        return distractors

    def _generate_modifier_variations(
        self,
        correct_answers: list[Any],
        exec_ctx: ExecutionContext,
        target: list[TargetElement],
        output_type: OutputType,
        num_distractors: int,
    ) -> list[Any]:
        """Generate distractors by varying modifiers"""
        distractors: list[Any] = []

        modifier_variations: dict[str, list[TargetModifier | None]] = {
            "branch_true": ["branch_false", None],
            "branch_false": ["branch_true", None],
            "loop_iterations": [None],
            "branch": ["branch_true", "branch_false"],
            "loop": ["loop_iterations"],
        }

        for i, target_element in enumerate(target):
            if (
                target_element.modifier is not None
                and target_element.modifier in modifier_variations
            ):
                for new_modifier in modifier_variations[target_element.modifier]:
                    modified_target = copy.deepcopy(target)
                    modified_target[i].modifier = new_modifier
                    self._run_and_clean_modified_query(
                        correct_answers[0],
                        distractors,
                        target,
                        output_type,
                        exec_ctx,
                        modified_target,
                        num_distractors,
                    )
                    if len(distractors) >= num_distractors:
                        break
            if (
                target_element.modifier is None
                and target_element.type in modifier_variations
            ):
                for new_modifier in modifier_variations[target_element.type]:
                    modified_target = copy.deepcopy(target)
                    modified_target[i].modifier = new_modifier
                    self._run_and_clean_modified_query(
                        correct_answers[0],
                        distractors,
                        target,
                        output_type,
                        exec_ctx,
                        modified_target,
                        num_distractors,
                    )
                    if len(distractors) >= num_distractors:
                        break
            if len(distractors) >= num_distractors:
                break
        return distractors

    def _run_and_clean_modified_query(
        self,
        correct_answer: Any,
        distractors: list[Any],
        target: list[TargetElement],
        output_type: OutputType,
        exec_ctx: ExecutionContext,
        modified_target: list[TargetElement],
        num_distractors: int,
    ) -> None:
        try:
            modified_query_result = self._run_modified_query(
                target, output_type, exec_ctx, modified_target_path=modified_target
            )
            for item in modified_query_result:
                modified_item = self._match_answer_format(correct_answer, item)
                distractors.append(modified_item)
                if len(distractors) >= num_distractors:
                    break
        except Exception:
            pass

    def _run_modified_query(
        self,
        target: list[TargetElement],
        output_type: OutputType,
        exec_ctx: ExecutionContext,
        modified_output_type: OutputType | None = None,
        modified_target_path: list[TargetElement] | None = None,
    ) -> list[Any]:
        # Use modified values if provided, otherwise use original
        final_output_type = (
            modified_output_type if modified_output_type else output_type
        )
        final_target = modified_target_path if modified_target_path else target

        query_generator = QueryGenerator(exec_ctx)
        query = query_generator.generate_query(final_target, final_output_type)
        result = query.execute()
        return result

    def _match_answer_format(self, ref_answer: Any, distractor: Any) -> Any:
        """Ensure distractors match the format of the correct answer."""
        if isinstance(ref_answer, type(distractor)) and not isinstance(
            ref_answer, list
        ):
            return distractor

        if isinstance(ref_answer, list) and not isinstance(distractor, list):
            return [distractor]

        if not isinstance(ref_answer, list) and isinstance(distractor, list):
            return self._match_answer_format(ref_answer, distractor[0])

        if isinstance(ref_answer, list) and isinstance(distractor, list):
            distractor = cast(list[Any], distractor)
            ref_answer = cast(list[Any], ref_answer)

            if len(ref_answer) == 0 or len(distractor) == 0:
                return None

            if isinstance(ref_answer[0], list) and not isinstance(distractor[0], list):
                return [self._match_answer_format(ref_answer[0], distractor)]

            return [
                self._match_answer_format(ref_answer[0], distractor[i])
                for i in range(len(distractor))
            ]

        return None

    def _deduplicate_distractors(
        self, correct_options: list[Any], distractors: list[Any]
    ) -> list[Any]:
        """Remove duplicates and the correct answer from distractors."""
        unique_distractors: list[Any] = []
        seen: set[str] = set()
        for ans in correct_options:
            seen.add(str(ans))

        for dist in distractors:
            dist_key = str(dist)
            if dist_key not in seen:
                seen.add(dist_key)
                unique_distractors.append(dist)

        return unique_distractors
