import pytest

from edcraft_engine.question_generator.text_generator import TextGenerator
from tests.question_generator.conftest import make_target


@pytest.mark.parametrize(
    ("output_type", "expected"),
    [
        ("count", "how many times was function `foo()` called"),
        ("first", "what is the first function `foo()` call"),
        ("last", "what is the last function `foo()` call"),
        ("list", "what are the function `foo()` calls"),
    ],
)
def test_function_target_basic(
    text_generator: "TextGenerator",
    output_type: str,
    expected: str,
) -> None:
    target = make_target(type="function", name="foo")

    result = text_generator._build_target(target, output_type)

    assert expected in result


@pytest.mark.parametrize(
    ("modifier", "output_type", "expected"),
    [
        ("arguments", "count", "unique sets of arguments"),
        ("arguments", "first", "arguments"),
        ("return_value", "count", "unique return values"),
        ("return_value", "first", "return value"),
    ],
)
def test_function_target_modifiers(
    text_generator: "TextGenerator",
    modifier: str,
    output_type: str,
    expected: str,
) -> None:
    target = make_target(type="function", name="foo", modifier=modifier)

    result = text_generator._build_target(target, output_type)

    assert expected in result


@pytest.mark.parametrize(
    ("output_type", "expected"),
    [
        ("count", "how many times does the loop"),
        ("first", "first execution of the loop"),
        ("last", "last execution of the loop"),
        ("list", "executions of the loop"),
    ],
)
def test_loop_target(
    text_generator: "TextGenerator",
    output_type: str,
    expected: str,
) -> None:
    target = make_target(type="loop", line_number=10)

    result = text_generator._build_target(target, output_type)

    assert expected in result


@pytest.mark.parametrize(
    ("modifier", "expected"),
    [
        ("branch_true", "when the condition is true"),
        ("branch_false", "when the condition is false"),
        (None, ""),
    ],
)
def test_branch_target(
    text_generator: "TextGenerator",
    modifier: str | None,
    expected: str,
) -> None:
    target = make_target(
        type="branch",
        name="if",
        line_number=5,
        modifier=modifier,
    )

    result = text_generator._build_target(target, "count")

    if expected:
        assert expected in result
    else:
        assert "when the condition" not in result


@pytest.mark.parametrize(
    ("output_type", "expected"),
    [
        ("count", "how many times was the variable"),
        ("first", "at the beginning"),
        ("last", "at the end"),
        ("list", "what are the values"),
    ],
)
def test_variable_target(
    text_generator: "TextGenerator",
    output_type: str,
    expected: str,
) -> None:
    target = make_target(type="variable", name="x")

    result = text_generator._build_target(target, output_type)

    assert expected in result
