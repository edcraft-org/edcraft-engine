from edcraft_engine.question_generator.text_generator import TextGenerator


def test_input_data_formatting(text_generator: TextGenerator) -> None:
    data = {"x": 10, "name": "alice"}

    result = text_generator._build_input_data_phrase(data)

    assert "x = 10" in result
    assert 'name = "alice"' in result


def test_input_data_empty(text_generator: TextGenerator) -> None:
    assert text_generator._build_input_data_phrase({}) == ""
