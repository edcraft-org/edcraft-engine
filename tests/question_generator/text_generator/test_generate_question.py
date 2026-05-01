from edcraft_engine.question_generator.text_generator import TextGenerator
from tests.question_generator.conftest import make_spec, make_target


def test_generate_question_basic(
    text_generator: TextGenerator,
) -> None:
    target = make_target(type="function", name="foo")
    spec = make_spec([target])

    result = text_generator.generate_question(spec)

    assert "function `foo()`" in result
    assert result.endswith("Choose the correct option.")


def test_generate_question_with_input(
    text_generator: TextGenerator,
) -> None:
    target = make_target(type="variable", name="x")
    spec = make_spec([target], output_type="first")

    result = text_generator.generate_question(spec, input_data={"x": 10})

    assert "Given input:" in result
    assert "x = 10" in result


def test_generate_question_no_context(
    text_generator: TextGenerator,
) -> None:
    target = make_target(type="variable", name="x")
    spec = make_spec([target])

    result = text_generator.generate_question(spec)

    assert result.startswith("During execution")
