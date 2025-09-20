import operator
from collections.abc import Callable
from typing import Any

from src.core.query_engine.query_engine_exception import (
    InvalidOperatorError,
    QueryEngineError,
)
from src.core.query_engine.utils import get_field_value
from src.models.tracer_models import (
    ExecutionContext,
    StatementExecution,
    VariableSnapshot,
)


class QueryCondition:
    """Represents a single WHERE query condition."""

    def __init__(self, field: str, op: str, value: Any):
        self.field = field
        self.op = op
        self.value = value

        self.op_map: dict[str, Callable[[Any, Any], bool]] = {
            "==": operator.eq,
            "!=": operator.ne,
            "<": operator.lt,
            "<=": operator.le,
            ">": operator.gt,
            ">=": operator.ge,
            "in": lambda x, y: x in y,
            "not_in": lambda x, y: x not in y,
        }

    def evaluate(self, obj: StatementExecution | VariableSnapshot) -> bool:
        """Evaluate condition against an object."""
        try:
            field_value = get_field_value(obj, self.field)

            op_func = self.op_map.get(self.op)
            if not op_func:
                raise InvalidOperatorError(self.op)

            return op_func(field_value, self.value)
        except (TypeError, KeyError):
            return False


class Query:
    """Base class for all queries."""

    def __init__(self, execution_context: ExecutionContext):
        self.execution_context = execution_context
        self.conditions: list[list[QueryCondition]] = []
        self.order_by_fields: list[tuple[str, bool]] = []  # (field, is_ascending)
        self.map_func: Callable[[Any], Any] | None = None
        self.flat_map_func: Callable[[Any], Any] | None = None
        self.selected_field: str | None = None
        self.apply_distinct = False

    def where(
        self,
        *conditions: tuple[str, str, Any],
        field: str | None = None,
        op: str = "==",
        value: Any = None,
        **kwargs: dict[str, Any],
    ) -> "Query":
        """Add a WHERE condition."""
        if field is not None:
            self.conditions.append([QueryCondition(field, op, value)])

        condition_list: list[QueryCondition] = []
        for field, op, value in conditions:
            condition_list.append(QueryCondition(field, op, value))
        if condition_list:
            self.conditions.append(condition_list)

        for key, val in kwargs.items():
            self.conditions.append([QueryCondition(key, "==", val)])

        return self

    def map(self, func: Callable[[Any], Any]) -> "Query":
        """Apply a transformation function to each result."""
        self.map_func = func
        return self

    def flat_map(self, func: Callable[[Any], list[Any]]) -> "Query":
        """Apply a function to each item and flatten the results."""
        self.flat_map_func = func
        return self

    def select(self, field: str) -> "Query":
        """Select specific field from results."""
        if self.selected_field is not None:
            raise QueryEngineError("'select' can only be applied once per query.")
        self.selected_field = field
        return self

    def distinct(self) -> "Query":
        """Remove duplicates from results."""
        self.apply_distinct = True
        return self

    def order_by(self, field: str, is_ascending: bool = True) -> "Query":
        """Sort results by a field."""
        self.order_by_fields.append((field, is_ascending))
        return self

    def _apply_filters(
        self, items: list[StatementExecution | VariableSnapshot]
    ) -> list[Any]:
        result = items

        # Apply WHERE
        for condition_list in self.conditions:
            result = [
                item
                for item in result
                if any(cond.evaluate(item) for cond in condition_list)
            ]

        # Apply ORDER BY
        if self.order_by_fields:
            for field, is_ascending in reversed(self.order_by_fields):
                result.sort(
                    key=lambda item: get_field_value(item, field),
                    reverse=not is_ascending,
                )

        # Apply SELECT
        if self.selected_field:
            result = [get_field_value(item, self.selected_field) for item in result]

        # Apply MAP
        if self.map_func:
            result = [self.map_func(item) for item in result]

        # Apply FLAT MAP
        if self.flat_map_func:
            flat_mapped_result: list[Any] = []
            for item in result:
                flat_mapped_result.extend(self.flat_map_func(item))
            result = flat_mapped_result

        # Apply DISTINCT
        if self.apply_distinct:
            result = list(set(result))

        return result

    def execute(self) -> list[Any]:
        """Execute the query and return results."""
        executions = self.execution_context.execution_trace
        variables = self.execution_context.variables
        return self._apply_filters(executions + variables)


class QueryEngine:
    """Query engine interface."""

    def __init__(self, execution_context: "ExecutionContext"):
        self.execution_context = execution_context

    def create_query(self) -> Query:
        """Create a new query instance."""
        return Query(self.execution_context)
