import pytest

from tests.static_analyser.conftest import analyse


@pytest.mark.parametrize(
    "code, expected_vars",
    [
        ("x = 1", {"x"}),  # simple assignment
        ("x = 1\ny = 2", {"x", "y"}),  # multiple assignments
        ("x, y = 1, 2", {"x", "y"}),  # unpacking assignment
        ("[a, b] = [1, 2]", {"a", "b"}),  # list unpacking
        ("(a, (b, c)) = (1, (2, 3))", {"a", "b", "c"}),  # nested unpacking
        ("x += 1", {"x"}),  # augmented assignment
        ("x: int = 1", {"x"}),  # annotated assignment
        ("obj.attr = 1", {"obj"}),  # attribute assignment
        ("arr[0] = 1", {"arr"}),  # subscript assignment
        ("*a, b = [1, 2, 3]", {"a", "b"}),  # starred unpacking
        ("for i in range(5): pass", {"i"}),  # loop variable
        ("x = 1\ndef foo():\n y = 2", {"x", "y"}),  # variable in nested scope
        ("def foo(a, b): c = a + b", {"a", "b", "c"}),  # function parameters and local variable
    ],
)
def test_variable_extraction(code: str, expected_vars: set[str]) -> None:
    result = analyse(code)

    assert result.variables == expected_vars
