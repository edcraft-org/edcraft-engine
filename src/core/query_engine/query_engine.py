import operator
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from src.core.query_engine.utils import get_field_value
from src.models.tracer_models import ExecutionContext


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

    def evaluate(self, obj: Any) -> bool:
        """Evaluate condition against an object."""
        try:
            field_value = get_field_value(obj, self.field)

            op_func = self.op_map.get(self.op)
            if not op_func:
                raise ValueError(f"Unsupported operator: {self.op}")

            return op_func(field_value, self.value)
        except (AttributeError, TypeError, KeyError):
            return False


class BaseQuery(ABC):
    """Base class for all queries."""

    def __init__(self, execution_context: ExecutionContext):
        self.execution_context = execution_context
        self.conditions: list[QueryCondition] = []
        self.selected_field: str | None = None
        self.apply_distinct = False

    def where(
        self,
        # field: str | None = None,
        field: str,
        op: str = "==",
        value: Any = None,
        # **kwargs: dict[str, Any],
    ) -> "BaseQuery":
        """Add a WHERE condition."""
        # if field is not None:
        self.conditions.append(QueryCondition(field, op, value))

        # for key, val in kwargs.items():
        #     self.conditions.append(QueryCondition(key, "==", val))

        return self

    def select(self, field: str) -> "BaseQuery":
        """Select specific field from results."""
        self.selected_field = field
        return self

    def distinct(self) -> "BaseQuery":
        """Remove duplicates from results."""
        self.apply_distinct = True
        return self

    def _apply_filters(self, items: list[Any]) -> list[Any]:
        result = items

        # Apply WHERE condition
        for condition in self.conditions:
            result = [item for item in result if condition.evaluate(item)]

        # Apply SELECT
        if self.selected_field:
            result = [  # type: ignore
                get_field_value(item, self.selected_field) for item in result
            ]

        # Apply DISTINCT
        if self.apply_distinct:
            result = list(set(result))

        return result  # type: ignore

    @abstractmethod
    def execute(self) -> list[Any]:
        """Execute the query and return results."""
        pass


class ExecutionQuery(BaseQuery):
    """Query for statement executions."""

    def __init__(self, execution_context: "ExecutionContext"):
        super().__init__(execution_context)

    def execute(self) -> list[Any]:
        """Execute the query and return results."""
        executions = self.execution_context.execution_trace
        filtered_data = self._apply_filters(executions)
        return filtered_data


class VariableQuery(BaseQuery):
    """Query for variable snapshots."""

    def __init__(self, execution_context: "ExecutionContext"):
        super().__init__(execution_context)

    def execute(self) -> list[Any]:
        """Execute the query and return results."""
        variables = self.execution_context.variables
        filtered_data = self._apply_filters(variables)
        return filtered_data


class QueryEngine:
    """Query engine interface."""

    def __init__(self, execution_context: "ExecutionContext"):
        self.execution_context = execution_context

    def query_executions(self) -> ExecutionQuery:
        """Create a query for statement executions."""
        return ExecutionQuery(self.execution_context)

    def query_variables(self) -> VariableQuery:
        """Create a query for variable snapshots."""
        return VariableQuery(self.execution_context)
