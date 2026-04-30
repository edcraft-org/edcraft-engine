import pytest

from tests.static_analyser.conftest import analyse


@pytest.mark.parametrize(
    "code, expected",
    [
        (  # Empty input should produce no analysis artifacts
            "",
            {
                "functions": [],
                "loops": [],
                "branches": [],
                "variables": set(),
            },
        ),
        (  # Code with only assignments
            """
            x = 1
            y = x + 2
            """,
            {
                "functions": [],
                "loops": [],
                "branches": [],
                "variables": {"x", "y"},
            },
        ),
    ],
)
def test_basic_analysis(code: str, expected: dict) -> None:
    result = analyse(code)

    assert result.functions == expected["functions"]
    assert result.loops == expected["loops"]
    assert result.branches == expected["branches"]
    assert result.variables == expected["variables"]


def test_nested_structure() -> None:
    result = analyse("""
        x = 0

        def foo(a):
            for i in range(5):
                if i % 2 == 0:
                    while x < 10:
                        x += 1
    """)

    # Functions
    assert [f.name for f in result.functions if f.is_definition] == ["foo"]

    # Loops
    loop_types = [loop.loop_type for loop in result.loops]
    assert loop_types == ["for", "while"]

    conditions = [loop.condition for loop in result.loops]
    assert conditions == ["i in range(5)", "x < 10"]

    # Branches
    branch_conditions = [b.condition for b in result.branches]
    assert branch_conditions == ["i % 2 == 0"]

    # Variables across scopes
    assert result.variables == {"x", "a", "i"}


def test_invalid_syntax() -> None:
    with pytest.raises(ValueError):
        analyse("def broken(:")
