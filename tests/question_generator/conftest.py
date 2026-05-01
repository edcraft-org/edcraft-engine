from typing import Any

import pytest

from edcraft_engine.question_generator.models import (
    OutputType,
    QuestionSpec,
    QuestionType,
    TargetElement,
)
from edcraft_engine.question_generator.text_generator import TextGenerator


@pytest.fixture
def text_generator() -> TextGenerator:
    return TextGenerator()


def make_target(**kwargs: Any) -> TargetElement:
    defaults: dict[str, Any] = {
        "type": "function",
        "id": [0],
        "name": "foo",
        "line_number": None,
        "modifier": None,
        "argument_keys": None,
    }
    defaults.update(kwargs)
    return TargetElement.model_validate(defaults)


def make_spec(
    target: list[TargetElement],
    output_type: OutputType = "count",
    question_type: QuestionType = "mcq",
) -> QuestionSpec:
    return QuestionSpec(
        target=target,
        output_type=output_type,
        question_type=question_type,
    )
