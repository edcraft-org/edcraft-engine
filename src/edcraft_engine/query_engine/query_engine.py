from collections.abc import Callable
from typing import Any

from edcraft_engine.query_engine.pipeline_steps import (
    DistinctStep,
    FullOuterJoinStep,
    GroupByStep,
    InnerJoinStep,
    LeftJoinStep,
    LimitStep,
    MapStep,
    OffsetStep,
    OrderByStep,
    PipelineStep,
    QueryCondition,
    ReduceStep,
    RightJoinStep,
    SelectStep,
    WhereStep,
)
from edcraft_engine.query_engine.query_engine_exception import (
    QueryEngineError,
)
from edcraft_engine.step_tracer.models import (
    ExecutionContext,
    StatementExecution,
    VariableSnapshot,
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

    def group_by(self, *fields: str, **kwargs: str) -> "Query":
        if not fields and not kwargs:
            raise QueryEngineError("At least one field must be specified for group_by.")

        group_fields: dict[str, str] = kwargs
        for field in fields:
            group_fields[field] = field

        self.pipeline.append(GroupByStep(group_fields=group_fields, aggregations={}))
        return self

    def agg(self, **aggregations: Callable[[list[Any]], Any]) -> "Query":
        if not self.pipeline or not isinstance(self.pipeline[-1], GroupByStep):
            self.pipeline.append(GroupByStep(dict(), aggregations=aggregations))
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

    def inner_join(
        self,
        other_items: list[Any],
        conditions: Callable[[Any, Any], bool],
        left_alias: str,
        right_alias: str,
    ) -> "Query":
        """Perform an inner join with another set of items."""
        self.pipeline.append(
            InnerJoinStep(
                other_items=other_items,
                conditions=conditions,
                left_alias=left_alias,
                right_alias=right_alias,
            )
        )
        return self

    def left_join(
        self,
        other_items: list[Any],
        conditions: Callable[[Any, Any], bool],
        left_alias: str,
        right_alias: str,
    ) -> "Query":
        """Perform a left join with another set of items."""
        self.pipeline.append(
            LeftJoinStep(
                other_items=other_items,
                conditions=conditions,
                left_alias=left_alias,
                right_alias=right_alias,
            )
        )
        return self

    def right_join(
        self,
        other_items: list[Any],
        conditions: Callable[[Any, Any], bool],
        left_alias: str,
        right_alias: str,
    ) -> "Query":
        """Perform a right join with another set of items."""
        self.pipeline.append(
            RightJoinStep(
                other_items=other_items,
                conditions=conditions,
                left_alias=left_alias,
                right_alias=right_alias,
            )
        )
        return self

    def full_outer_join(
        self,
        other_items: list[Any],
        conditions: Callable[[Any, Any], bool],
        left_alias: str,
        right_alias: str,
    ) -> "Query":
        """Perform a full outer join with another set of items."""
        self.pipeline.append(
            FullOuterJoinStep(
                other_items=other_items,
                conditions=conditions,
                left_alias=left_alias,
                right_alias=right_alias,
            )
        )
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
