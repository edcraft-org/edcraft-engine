import pytest

from edcraft_engine.question_generator.text_generator import TextGenerator
from tests.question_generator.conftest import make_target


def test_context_empty(text_generator: TextGenerator) -> None:
    result = text_generator._build_context([])
    assert result == "During execution"


@pytest.mark.parametrize(
    "target, expected",
    [
        (
            {"type": "function", "name": "foo"},
            "For each `foo()` call",
        ),
        (
            {"type": "loop", "modifier": "loop_iterations"},
            "For each loop iteration",
        ),
        (
            {"type": "loop", "line_number": 10},
            "In the loop at line 10",
        ),
        (
            {
                "type": "branch",
                "name": "x > 10",
                "line_number": 5,
                "modifier": "branch_true",
            },
            "In each `x > 10` branch (line 5), when the condition is true",
        ),
    ],
)
def test_context_single(
    text_generator: TextGenerator,
    target: dict,
    expected: str,
) -> None:
    result = text_generator._build_context([make_target(**target)])
    assert result.startswith(expected)


@pytest.mark.parametrize(
    "targets, expected",
    [
        (
            [
                {"type": "function", "name": "foo"},
                {"type": "loop", "modifier": "loop_iterations"},
            ],
            "For each `foo()` call, for each loop iteration",
        ),
        (
            [
                {"type": "function", "name": "foo"},
                {
                    "type": "branch",
                    "name": "x > 10",
                    "line_number": 5,
                    "modifier": "branch_true",
                },
            ],
            "For each `foo()` call, in each `x > 10` branch (line 5), when the condition is true",
        ),
    ],
)
def test_context_multiple(
    text_generator: TextGenerator,
    targets: list,
    expected: str,
) -> None:
    result = text_generator._build_context([make_target(**t) for t in targets])
    assert result.startswith(expected)
