import pytest

from edcraft_engine.question_generator.models import QuestionType
from edcraft_engine.question_generator.text_generator import TextGenerator


@pytest.mark.parametrize(
    ("qtype", "expected"),
    [
        ("mcq", "Choose the correct option."),
        ("mrq", "Select all that apply."),
        ("other", "Provide the answer."),
    ],
)
def test_question_type(
    text_generator: TextGenerator,
    qtype: QuestionType,
    expected: str,
) -> None:
    assert text_generator._build_question_type(qtype) == expected
