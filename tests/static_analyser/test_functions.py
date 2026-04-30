import pytest

from tests.static_analyser.conftest import analyse


@pytest.mark.parametrize(
    "code, expected",
    [
        (  # Simple function definition with parameters
            """
            def foo(a, b):
                return a + b
            """,
            [{"name": "foo", "is_definition": True, "parameters": ["a", "b"]}],
        ),
        (  # Function definition followed by a call to that function
            """
            def foo():
                pass

            foo()
            """,
            [
                {"name": "foo", "is_definition": True},
                {"name": "foo", "is_definition": False},
            ],
        ),
        (  # Method call on an object
            """
            obj.method()
            """,
            [{"name": "obj.method", "is_definition": False}],
        ),
        (  # Multiple function calls in a row
            """
            foo()
            bar()
            baz()
            """,
            [
                {"name": "foo"},
                {"name": "bar"},
                {"name": "baz"},
            ],
        ),
        (  # Nested function calls
            """
            x = foo(bar())
            """,
            [
                {"name": "foo", "is_definition": False},
                {"name": "bar", "is_definition": False},
            ],
        ),
        (  # Nested function definitions
            """
            def outer():
                def inner():
                    pass
                inner()
            """,
            [
                {"name": "outer", "is_definition": True},
                {"name": "inner", "is_definition": True},
                {"name": "inner", "is_definition": False},
            ],
        ),
        (  # Recursive function call
            """
            def foo(y):
                if y <= 0:
                    return 0
                return foo(y - 1) + 1
            """,
            [
                {"name": "foo", "is_definition": True, "parameters": ["y"]},
                {"name": "foo", "is_definition": False},
            ],
        ),
    ],
)
def test_functions(code: str, expected: list[dict]) -> None:
    result = analyse(code)

    assert len(result.functions) == len(expected)

    actual = []
    for f in result.functions:
        entry = {
            "name": f.name,
            "is_definition": f.is_definition,
        }
        if hasattr(f, "parameters"):
            entry["parameters"] = f.parameters
        actual.append(entry)

    for exp in expected:
        assert any(all(item.get(k) == v for k, v in exp.items()) for item in actual)
