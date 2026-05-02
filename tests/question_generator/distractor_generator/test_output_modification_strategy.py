from unittest.mock import Mock

import pytest

from edcraft_engine.question_generator.distractor_generator.distractor_strategies.output_modification_strategy import (
    OutputModificationStrategy,
)


@pytest.fixture
def strategy() -> OutputModificationStrategy:
    return OutputModificationStrategy()


def test_numeric_variations_basic(strategy: OutputModificationStrategy) -> None:
    result = strategy.generate(
        correct_options=[10],
        exec_ctx=Mock(),
        question_spec=Mock(),
        num_distractors=4,
    )

    assert all(isinstance(x, int) for x in result)
    assert 10 not in result
    assert len(result) == 4


def test_numeric_preserves_sign(strategy: OutputModificationStrategy) -> None:
    result = strategy.generate(
        correct_options=[-5],
        exec_ctx=Mock(),
        question_spec=Mock(),
        num_distractors=3,
    )

    assert all(x < 0 for x in result)


def test_list_variations_permutation(strategy: OutputModificationStrategy) -> None:
    correct = [1, 2, 3]
    result = strategy.generate(
        correct_options=[correct],
        exec_ctx=Mock(),
        question_spec=Mock(),
        num_distractors=2,
    )

    for r in result:
        assert sorted(r) == sorted(correct)
        assert r != correct


def test_dict_variations_modify_values(strategy: OutputModificationStrategy) -> None:
    correct = {"a": 5}
    result = strategy.generate(
        correct_options=[correct],
        exec_ctx=Mock(),
        question_spec=Mock(),
        num_distractors=2,
    )

    assert all(isinstance(x, dict) for x in result)
    assert all(x["a"] != 5 for x in result)
