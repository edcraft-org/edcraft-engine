from typing import Any

import pytest

from edcraft_engine.question_generator.models import (
    ExecutionSpec,
    GenerationOptions,
    QuestionSpec,
)
from edcraft_engine.question_generator.question_generator import QuestionGenerator
from tests.test_cases import cases


@pytest.fixture(scope="module")
def generator() -> QuestionGenerator:
    return QuestionGenerator()


@pytest.mark.parametrize(
    "case",
    cases,
)
def test_generate_question(generator: QuestionGenerator, case: dict[str, Any]) -> None:
    question_spec = QuestionSpec(**case["question_spec"])
    execution_spec = ExecutionSpec(**case["execution_spec"])
    generation_options = GenerationOptions(**case["generation_options"])

    result = generator.generate_question(
        code=case["code"],
        question_spec=question_spec,
        execution_spec=execution_spec,
        generation_options=generation_options,
    )

    assert (
        result.answer == case["answer"]
    ), f"Expected answer {case['answer']}, got {result.answer}"
