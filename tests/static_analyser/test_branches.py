import pytest

from tests.static_analyser.conftest import analyse


@pytest.mark.parametrize(
    "code, expected_conditions",
    [
        (  # simple if statement
            """
            if x > 0:
                y = 1
            """,
            ["x > 0"],
        ),
        (  # if-else statement
            """
            if x > 0:
                y = 1
            else:
                y = -1
            """,
            ["x > 0"],
        ),
        (  # nested if statements
            """
            if x > 0:
                if y > 0:
                    z = 1
            """,
            ["x > 0", "y > 0"],
        ),
        (  # if-elif-else statement
            """
            if x > 0:
                y = 1
            elif x < 0:
                y = -1
            else:
                y = 0
            """,
            ["x > 0", "x < 0"],
        ),
        (  # multiple independent if statements
            """
            if x > 0:
                y = 1
            if y > 0:
                z = 1
            """,
            ["x > 0", "y > 0"],
        ),
    ],
)
def test_branches(code: str, expected_conditions: list[str]) -> None:
    result = analyse(code)

    assert len(result.branches) == len(expected_conditions)
    conditions = [b.condition for b in result.branches]

    assert conditions == expected_conditions
