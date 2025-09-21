import operator
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal, cast

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


@dataclass
class WhereStep:
    conditions: list[QueryCondition]
    operation: Literal["where"] = "where"


@dataclass
class SelectStep:
    fields: list[str]
    operation: Literal["select"] = "select"


@dataclass
class MapStep:
    func: Callable[[Any], Any]
    operation: Literal["map"] = "map"


@dataclass
class FlatMapStep:
    func: Callable[[Any], list[Any]]
    operation: Literal["flat_map"] = "flat_map"


@dataclass
class DistinctStep:
    operation: Literal["distinct"] = "distinct"


@dataclass
class OrderByStep:
    field: str
    is_ascending: bool = True
    operation: Literal["order_by"] = "order_by"


@dataclass
class GroupByStep:
    group_fields: list[str]
    aggregations: dict[str, Callable[[list[Any]], Any]]
    operation: Literal["group_by"] = "group_by"


PipelineStep = (
    WhereStep
    | SelectStep
    | MapStep
    | FlatMapStep
    | DistinctStep
    | OrderByStep
    | GroupByStep
)


class Query:
    """Base class for all queries."""

    def __init__(self, execution_context: ExecutionContext):
        self.execution_context = execution_context
        self.pipeline: list[PipelineStep] = []

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
            self.pipeline.append(WhereStep([QueryCondition(field, op, value)]))

        condition_list: list[QueryCondition] = []
        for field, op, value in conditions:
            condition_list.append(QueryCondition(field, op, value))
        if condition_list:
            self.pipeline.append(WhereStep(condition_list))

        for key, val in kwargs.items():
            self.pipeline.append(WhereStep([QueryCondition(key, "==", val)]))

        return self

    def map(self, func: Callable[[Any], Any]) -> "Query":
        """Apply a transformation function to each result."""
        self.pipeline.append(MapStep(func=func))
        return self

    def flat_map(self, func: Callable[[Any], list[Any]]) -> "Query":
        """Apply a function to each item and flatten the results."""
        self.pipeline.append(FlatMapStep(func=func))
        return self

    def select(self, *fields: str) -> "Query":
        """Select specific fields from results."""
        if len(fields) == 0:
            raise QueryEngineError("At least one field must be specified for select.")
        self.pipeline.append(SelectStep(fields=list(fields)))
        return self

    def distinct(self) -> "Query":
        """Remove duplicates from results."""
        self.pipeline.append(DistinctStep())
        return self

    def order_by(self, field: str, is_ascending: bool = True) -> "Query":
        """Sort results by a field."""
        self.pipeline.append(OrderByStep(field=field, is_ascending=is_ascending))
        return self

    def group_by(self, *fields: str) -> "Query":
        if not fields:
            raise QueryEngineError("At least one field must be specified for group_by.")
        self.pipeline.append(GroupByStep(group_fields=list(fields), aggregations={}))
        return self

    def agg(self, **aggregations: Callable[[list[Any]], Any]) -> "Query":
        if not self.pipeline or not isinstance(self.pipeline[-1], GroupByStep):
            self.pipeline.append(GroupByStep([], aggregations=aggregations))
        else:
            group_step = self.pipeline[-1]
            group_step.aggregations.update(aggregations)
        return self

    def _apply_pipeline(
        self, items: list[StatementExecution | VariableSnapshot]
    ) -> list[Any]:
        result: list[Any] = items

        for step in self.pipeline:
            if isinstance(step, WhereStep):
                # Apply WHERE
                result = [
                    item
                    for item in result
                    if any(cond.evaluate(item) for cond in step.conditions)
                ]

            elif isinstance(step, SelectStep):
                # Apply SELECT
                if len(step.fields) == 1:
                    result = [get_field_value(item, step.fields[0]) for item in result]
                else:
                    result = [
                        {field: get_field_value(item, field) for field in step.fields}
                        for item in result
                    ]

            elif isinstance(step, MapStep):
                # Apply MAP
                result = [step.func(item) for item in result]

            elif isinstance(step, FlatMapStep):
                # Apply FLAT MAP
                flat_mapped_result: list[Any] = []
                for item in result:
                    flat_mapped_result.extend(step.func(item))
                result = flat_mapped_result

            elif isinstance(step, DistinctStep):
                # Apply DISTINCT
                seen: set[Any] = set()
                distinct_result: list[Any] = []
                for item in result:
                    try:
                        if item not in seen:
                            seen.add(item)
                            distinct_result.append(item)
                    except TypeError:
                        # Handle unhashable types
                        if item not in distinct_result:
                            distinct_result.append(item)
                result = distinct_result

            elif isinstance(step, OrderByStep):
                # Apply ORDER BY
                result.sort(
                    key=lambda item: get_field_value(
                        item, cast(OrderByStep, step).field
                    ),
                    reverse=not step.is_ascending,
                )

            else:
                # Apply GROUP BY
                if not step.aggregations:
                    raise QueryEngineError(
                        "At least one aggregation function must be specified for group_by."
                    )

                if step.group_fields:
                    grouped_items: dict[tuple[Any, ...], list[Any]] = defaultdict(list)
                    for item in result:
                        key = tuple(
                            get_field_value(item, field) for field in step.group_fields
                        )
                        grouped_items[key].append(item)
                else:
                    grouped_items = {(): result}

                aggregated_result: list[dict[str, Any]] = []
                for key, group in grouped_items.items():
                    agg_result = {
                        field: value
                        for field, value in zip(step.group_fields, key, strict=True)
                    }
                    for agg_name, agg_func in step.aggregations.items():
                        agg_result[agg_name] = agg_func(group)
                    aggregated_result.append(agg_result)
                result = aggregated_result

        return result

    def execute(self) -> list[Any]:
        """Execute the query and return results."""
        executions = self.execution_context.execution_trace
        variables = self.execution_context.variables
        return self._apply_pipeline(executions + variables)


class QueryEngine:
    """Query engine interface."""

    def __init__(self, execution_context: "ExecutionContext"):
        self.execution_context = execution_context

    def create_query(self) -> Query:
        """Create a new query instance."""
        return Query(self.execution_context)
