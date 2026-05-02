from typing import Any
from unittest.mock import Mock

from step_tracer import ExecutionContext

from edcraft_engine.question_generator.distractor_generator import DistractorGenerator
from edcraft_engine.question_generator.distractor_generator.distractor_strategies.base_strategy import (
    DistractorStrategy,
)
from edcraft_engine.question_generator.models import QuestionSpec


class DummyStrategy(DistractorStrategy):
    def __init__(self, outputs: list[Any]) -> None:
        self.outputs = outputs

    def generate(
        self,
        correct_options: list[Any],
        exec_ctx: ExecutionContext,
        question_spec: QuestionSpec,
        num_distractors: int,
    ) -> list[Any]:
        return self.outputs


def test_distractor_generator_basic_flow() -> None:
    strategy = DummyStrategy(outputs=[2, 3, 4])
    generator = DistractorGenerator(strategies=[strategy])

    result = generator.generate_distractors(
        correct_options=[1],
        exec_ctx=Mock(),
        question_spec=Mock(),
        num_distractors=2,
    )

    assert len(result) == 2
    assert set(result).issubset({2, 3, 4})


def test_distractor_generator_removes_duplicates_and_correct() -> None:
    strategy = DummyStrategy(outputs=[1, 2, 2, 3])
    generator = DistractorGenerator(strategies=[strategy])

    result = generator.generate_distractors(
        correct_options=[1],
        exec_ctx=Mock(),
        question_spec=Mock(),
        num_distractors=3,
    )

    assert 1 not in result
    assert len(result) == len(set(result))


def test_multiple_strategies_combined() -> None:
    s1 = DummyStrategy(outputs=[2])
    s2 = DummyStrategy(outputs=[3, 4])

    generator = DistractorGenerator(strategies=[s1, s2])

    result = generator.generate_distractors(
        correct_options=[1],
        exec_ctx=Mock(),
        question_spec=Mock(),
        num_distractors=3,
    )

    assert result == [2, 3, 4]
