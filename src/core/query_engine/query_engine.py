import operator
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, cast

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


class PipelineStepBase(ABC):
    @abstractmethod
    def apply(self, items: list[Any]) -> list[Any]:
        """Apply this pipeline step to the items."""
        pass


@dataclass
class WhereStep(PipelineStepBase):
    conditions: list[QueryCondition]

    def apply(self, items: list[Any]) -> list[Any]:
        return [
            item
            for item in items
            if any(cond.evaluate(item) for cond in self.conditions)
        ]


@dataclass
class SelectStep(PipelineStepBase):
    fields: list[str]

    def apply(self, items: list[Any]) -> list[Any]:
        if len(self.fields) == 1:
            result = [get_field_value(item, self.fields[0]) for item in items]
        else:
            result = [
                {field: get_field_value(item, field) for field in self.fields}
                for item in items
            ]
        return result


@dataclass
class MapStep(PipelineStepBase):
    func: Callable[[Any], Any]

    def apply(self, items: list[Any]) -> list[Any]:
        return [self.func(item) for item in items]


@dataclass
class ReduceStep(PipelineStepBase):
    def apply(self, items: list[Any]) -> list[Any]:
        reduced_result: list[Any] = []
        for item in items:
            if isinstance(item, list):
                reduced_result.extend(cast(list[Any], item))
            else:
                reduced_result.append(item)
        return reduced_result


@dataclass
class DistinctStep(PipelineStepBase):
    def apply(self, items: list[Any]) -> list[Any]:
        seen: set[Any] = set()
        distinct_result: list[Any] = []
        for item in items:
            try:
                if item not in seen:
                    seen.add(item)
                    distinct_result.append(item)
            except TypeError:
                # Handle unhashable types
                if item not in distinct_result:
                    distinct_result.append(item)
        return distinct_result


@dataclass
class OrderByStep(PipelineStepBase):
    field: str
    is_ascending: bool = True

    def apply(self, items: list[Any]) -> list[Any]:
        return sorted(
            items,
            key=lambda item: get_field_value(item, self.field),
            reverse=not self.is_ascending,
        )


@dataclass
class GroupByStep(PipelineStepBase):
    group_fields: list[str]
    aggregations: dict[str, Callable[[list[Any]], Any]]

    def apply(self, items: list[Any]) -> list[Any]:
        if not self.aggregations:
            raise QueryEngineError(
                "At least one aggregation function must be specified for group_by."
            )

        if self.group_fields:
            grouped_items: dict[tuple[Any, ...], list[Any]] = defaultdict(list)
            for item in items:
                key = tuple(get_field_value(item, field) for field in self.group_fields)
                grouped_items[key].append(item)
        else:
            grouped_items = {(): items}

        aggregated_result: list[dict[str, Any]] = []
        for key, group in grouped_items.items():
            agg_result = {
                field: value
                for field, value in zip(self.group_fields, key, strict=True)
            }
            for agg_name, agg_func in self.aggregations.items():
                agg_result[agg_name] = agg_func(group)
            aggregated_result.append(agg_result)
        return aggregated_result


@dataclass
class OffsetStep(PipelineStepBase):
    offset: int

    def apply(self, items: list[Any]) -> list[Any]:
        return items[self.offset :]


@dataclass
class LimitStep(PipelineStepBase):
    limit: int

    def apply(self, items: list[Any]) -> list[Any]:
        return items[: self.limit]


PipelineStep = (
    WhereStep
    | SelectStep
    | MapStep
    | ReduceStep
    | DistinctStep
    | OrderByStep
    | GroupByStep
    | OffsetStep
    | LimitStep
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

    def reduce(self) -> "Query":
        """Reduce results by one dimension."""
        self.pipeline.append(ReduceStep())
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

    def offset(self, offset: int) -> "Query":
        """Skip a number of results."""
        if offset < 0:
            raise QueryEngineError("Offset must be non-negative.")
        self.pipeline.append(OffsetStep(offset=offset))
        return self

    def limit(self, limit: int) -> "Query":
        """Limit the number of results."""
        if limit <= 0:
            raise QueryEngineError("Limit must be positive.")
        self.pipeline.append(LimitStep(limit=limit))
        return self

    def _apply_pipeline(
        self, items: list[StatementExecution | VariableSnapshot]
    ) -> list[Any]:
        result: list[Any] = items
        for step in self.pipeline:
            result = step.apply(result)
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
