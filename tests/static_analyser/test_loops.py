import pytest

from tests.static_analyser.conftest import analyse


@pytest.mark.parametrize(
    "code, expected",
    [
        (  # Simple for loop over range
            """
            for i in range(10):
                pass
            """,
            [{"loop_type": "for", "condition": "i in range(10)"}],
        ),
        (  # Simple while loop with condition
            """
            while x < 5:
                x += 1
            """,
            [{"loop_type": "while", "condition": "x < 5"}],
        ),
        (  # Nested loops (for inside while)
            """
            while x < 5:
                for i in range(3):
                    pass
            """,
            [
                {"loop_type": "while", "condition": "x < 5"},
                {"loop_type": "for", "condition": "i in range(3)"},
            ],
        ),
        (  # Multiple independent loops
            """
            for i in range(2):
                pass

            while y > 0:
                y -= 1
            """,
            [
                {"loop_type": "for", "condition": "i in range(2)"},
                {"loop_type": "while", "condition": "y > 0"},
            ],
        ),
        (  # For loop with iterable variable
            """
            items = [1, 2, 3]
            for item in items:
                pass
            """,
            [{"loop_type": "for", "condition": "item in items"}],
        ),
        (  # No loops present
            """
            x = 1
            y = 2
            """,
            [],
        ),
    ],
)
def test_loops(code: str, expected: list[dict]) -> None:
    result = analyse(code)

    assert len(result.loops) == len(expected)

    actual = [
        {
            "loop_type": loop.loop_type,
            "condition": loop.condition,
        }
        for loop in result.loops
    ]

    for exp in expected:
        assert any(all(item.get(k) == v for k, v in exp.items()) for item in actual)
