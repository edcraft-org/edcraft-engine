from typing import Any
from unittest.mock import Mock

from step_tracer import ExecutionContext

from edcraft_engine.question_generator.distractor_generator.distractor_strategies.query_variation_strategy import (
    QueryExecutor,
    QueryVariationStrategy,
)
from edcraft_engine.question_generator.models import OutputType, TargetElement


class DummyExecutor(QueryExecutor):
    def __init__(self, outputs_map: dict[tuple, list[Any]]) -> None:
        self.outputs_map = outputs_map

    def execute(
        self,
        exec_ctx: ExecutionContext,
        target: list[TargetElement],
        output_type: OutputType,
    ) -> list[Any]:
        key = (tuple(str(t) for t in target), output_type)
        return self.outputs_map.get(key, [])


def test_generates_distractors_from_variations() -> None:
    executor = DummyExecutor(
        outputs_map={
            (("t1",), "list"): [2, 3],
        }
    )

    strategy = QueryVariationStrategy(query_executor=executor)

    mock_target = [Mock(__str__=lambda self: "t1")]

    result = strategy.generate(
        correct_options=[1],
        exec_ctx=Mock(),
        question_spec=Mock(target=mock_target, output_type="first"),
        num_distractors=2,
    )

    assert len(result) <= 2
    assert 1 not in result


def test_format_scalar_to_list() -> None:
    strategy = QueryVariationStrategy(query_executor=Mock())

    result = strategy._validate_and_format([1], 2)
    assert result == [2]


def test_format_list_to_scalar() -> None:
    strategy = QueryVariationStrategy(query_executor=Mock())

    result = strategy._validate_and_format(1, [2])
    assert result == 2


def test_extract_flattens_list_for_scalar() -> None:
    strategy = QueryVariationStrategy(query_executor=Mock())

    result = strategy._extract_candidates(1, [2, 3])
    assert result == [2, 3]


def test_validate_rejects_wrong_length_list() -> None:
    strategy = QueryVariationStrategy(query_executor=Mock())

    result = strategy._validate_and_format([1], [2, 3])
    assert result is None


def test_validate_rejects_wrong_type() -> None:
    strategy = QueryVariationStrategy(query_executor=Mock())

    result = strategy._validate_and_format(1, "2")
    assert result is None


class DummyInternal:
    pass


def test_reject_internal_object() -> None:
    strategy = QueryVariationStrategy(query_executor=Mock())

    result = strategy._validate_and_format(1, DummyInternal())
    assert result is None


def test_scalar_passthrough() -> None:
    strategy = QueryVariationStrategy(query_executor=Mock())

    result = strategy._validate_and_format(1, 2)
    assert result == 2
