import operator
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Self, TypeVar, cast, override

from src.core.query_engine.query_engine_exception import (
    InvalidOperatorError,
    QueryEngineError,
)
from src.core.query_engine.utils import get_field_value
from src.models.tracer_models import (
    ExecutionContext,
    LoopExecution,
    LoopIteration,
    StatementExecution,
    VariableSnapshot,
)

T = TypeVar("T", bound="BaseQuery")


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

    @override
    def apply(self, items: list[Any]) -> list[Any]:
        return [
            item
            for item in items
            if any(cond.evaluate(item) for cond in self.conditions)
        ]


@dataclass
class SelectStep(PipelineStepBase):
    fields: list[str]

    @override
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

    @override
    def apply(self, items: list[Any]) -> list[Any]:
        return [self.func(item) for item in items]


@dataclass
class ReduceStep(PipelineStepBase):
    @override
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
    @override
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

    @override
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

    @override
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

    @override
    def apply(self, items: list[Any]) -> list[Any]:
        return items[self.offset :]


@dataclass
class LimitStep(PipelineStepBase):
    limit: int

    @override
    def apply(self, items: list[Any]) -> list[Any]:
        return items[: self.limit]


@dataclass
class WithinBlockStep(PipelineStepBase):
    """Extract all statements and variables within a block's execution range."""

    execution_context: ExecutionContext

    @override
    def apply(self, items: list[Any]) -> list[Any]:
        if not items:
            return []

        results: list[Any] = []

        for item in items:
            if not hasattr(item, "scope_id") or not hasattr(item, "execution_id"):
                raise QueryEngineError(
                    "Item does not have scope_id or execution_id attributes."
                )

            scope_id = item.scope_id
            start_id = item.execution_id
            end_id = getattr(item, "end_execution_id", start_id)

            # Get statements within execution range
            for stmt in self.execution_context.execution_trace:
                if start_id <= stmt.execution_id <= end_id:
                    results.append(stmt)

            # Get variables within scope and execution range
            for var in self.execution_context.variables:
                if var.scope_id == scope_id and start_id <= var.execution_id <= end_id:
                    results.append(var)

        return results


@dataclass
class CollectionStep(PipelineStepBase):
    parent_pipeline: list["PipelineStep"]
    pipeline: list["PipelineStep"] = field(default_factory=list["PipelineStep"])

    @override
    def apply(self, items: list[Any]) -> list[Any]:
        results: list[list[Any]] = []
        for item in items:
            result = cast(list[Any], item) if isinstance(item, list) else [item]
            for step in self.pipeline:
                result = step.apply(result)
            results.append(result)
        return results


@dataclass
class ExitCollectionStep(PipelineStepBase):
    @override
    def apply(self, items: list[Any]) -> list[Any]:
        return items


@dataclass
class SelectLoopIteration(PipelineStepBase):
    loop_iterations: list[LoopIteration]

    @override
    def apply(self, items: list[Any]) -> list[Any]:
        results: list[Any] = []
        for item in items:
            if not isinstance(item, LoopExecution):
                raise QueryEngineError("Item is not a LoopExecution instance.")
            iterations = [
                iteration
                for iteration in self.loop_iterations
                if iteration.loop_execution_id == item.execution_id
            ]
            results.append(iterations)
        return results


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
    | WithinBlockStep
    | CollectionStep
    | ExitCollectionStep
    | SelectLoopIteration
)


class BaseQuery:
    """Base class for all queries."""

    def __init__(
        self,
        execution_context: ExecutionContext,
        pipeline: list["PipelineStep"] | None = None,
        parent_pipeline: list["PipelineStep"] | None = None,
        previous_pipeline: list["PipelineStep"] | None = None,
        items: list[Any] | None = None,
    ):
        self.execution_context = execution_context
        self.pipeline: list[PipelineStep] = pipeline if pipeline is not None else []
        self.parent_pipeline: list[PipelineStep] = (
            parent_pipeline if parent_pipeline is not None else self.pipeline
        )
        self.previous_pipeline: list[PipelineStep] | None = previous_pipeline
        self.items = (
            items
            if items is not None
            else execution_context.execution_trace + execution_context.variables
        )

    def execute(self) -> list[Any]:
        """Execute the query and return results."""
        result: list[Any] = self.items
        for step in self.parent_pipeline:
            result = step.apply(result)
        return result

    def where(
        self,
        *conditions: tuple[str, str, Any],
        field: str | None = None,
        op: str = "==",
        value: Any = None,
        **kwargs: Any,
    ) -> Self:
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

    def map(self, func: Callable[[Any], Any]) -> Self:
        """Apply a transformation function to each result."""
        self.pipeline.append(MapStep(func=func))
        return self

    def reduce(self) -> Self:
        """Reduce results by one dimension."""
        self.pipeline.append(ReduceStep())
        return self

    def select(self, *fields: str) -> Self:
        """Select specific fields from results."""
        if len(fields) == 0:
            raise QueryEngineError("At least one field must be specified for select.")
        self.pipeline.append(SelectStep(fields=list(fields)))
        return self

    def distinct(self) -> Self:
        """Remove duplicates from results."""
        self.pipeline.append(DistinctStep())
        return self

    def order_by(self, field: str, is_ascending: bool = True) -> Self:
        """Sort results by a field."""
        self.pipeline.append(OrderByStep(field=field, is_ascending=is_ascending))
        return self

    def group_by(self, *fields: str) -> Self:
        if not fields:
            raise QueryEngineError("At least one field must be specified for group_by.")
        self.pipeline.append(GroupByStep(group_fields=list(fields), aggregations={}))
        return self

    def agg(self, **aggregations: Callable[[list[Any]], Any]) -> Self:
        if not self.pipeline or not isinstance(self.pipeline[-1], GroupByStep):
            self.pipeline.append(GroupByStep([], aggregations=aggregations))
        else:
            group_step = self.pipeline[-1]
            group_step.aggregations.update(aggregations)
        return self

    def offset(self, offset: int) -> Self:
        """Skip a number of results."""
        if offset < 0:
            raise QueryEngineError("Offset must be non-negative.")
        self.pipeline.append(OffsetStep(offset=offset))
        return self

    def limit(self, limit: int) -> Self:
        """Limit the number of results."""
        if limit <= 0:
            raise QueryEngineError("Limit must be positive.")
        self.pipeline.append(LimitStep(limit=limit))
        return self

    def within_blocks(self) -> Self:
        """
        Extract all statements/variables from within the selected blocks and
        flattens them.
        """
        self.pipeline.append(WithinBlockStep(execution_context=self.execution_context))
        return self

    def to_collection(self) -> Self:
        """Start a sub-pipeline for each item in the current results."""
        collection_step = CollectionStep(parent_pipeline=self.pipeline)
        self.pipeline.append(collection_step)
        self.previous_pipeline = self.pipeline
        self.pipeline = collection_step.pipeline
        return self

    def exit_collection(self) -> Self:
        """Exit the current collection sub-pipeline."""
        if not self.previous_pipeline or not isinstance(
            self.previous_pipeline[-1], CollectionStep
        ):
            raise QueryEngineError("Not currently in a collection context.")
        self.pipeline = self.previous_pipeline
        self.previous_pipeline = self.previous_pipeline[-1].parent_pipeline
        self.pipeline.append(ExitCollectionStep())
        return self


class Query(BaseQuery):
    def clone_as(self, cls: type[T]) -> T:
        """Return a copy of self as an instance of `cls`."""
        return cls(
            execution_context=self.execution_context,
            pipeline=self.pipeline,
            parent_pipeline=self.parent_pipeline,
            previous_pipeline=self.previous_pipeline,
            items=self.items,
        )

    def count(self) -> Self:
        """Count the number of results."""
        self.agg(count=lambda items: len(items)).select("count")
        return self

    def variables(self, **kwargs: Any) -> "VariableSnapshotQuery":
        """Filter to only variable snapshots."""
        self.where(field="stmt_type", op="==", value="variable", **kwargs)
        return self.clone_as(VariableSnapshotQuery)

    def loops(self, **kwargs: Any) -> "LoopQuery":
        """Filter to only loop executions."""
        self.where(field="stmt_type", op="==", value="loop", **kwargs)
        return self.clone_as(LoopQuery)

    def loop_iterations(self, **kwargs: Any) -> "LoopIterationQuery":
        """Filter to only loop iterations."""
        self.where(field="stmt_type", op="==", value="loop_iteration", **kwargs)
        return self.clone_as(LoopIterationQuery)

    def functions(self, **kwargs: Any) -> "FunctionCallQuery":
        """Filter to only function executions."""
        self.where(field="stmt_type", op="==", value="function", **kwargs)
        return self.clone_as(FunctionCallQuery)

    def branches(self, **kwargs: Any) -> "BranchQuery":
        """Filter to only branch executions."""
        self.where(field="stmt_type", op="==", value="branch", **kwargs)
        return self.clone_as(BranchQuery)


class VariableSnapshotQuery(Query):
    """Query class specifically for variable snapshots."""

    def latest_snapshots(self) -> Query:
        """Get the latest snapshot for each variable name."""
        self.group_by("name").agg(
            latest=lambda group: max(group, key=lambda s: s.execution_id)
        ).map(lambda grp: grp["latest"])
        return self


class LoopQuery(Query):
    """Query class specifically for loop executions."""

    def iterations(self, **kwargs: Any) -> "Query":
        """Get all iterations of the selected loops."""
        loop_iterations = (
            Query(self.execution_context).loop_iterations(**kwargs).execute()
        )
        self.pipeline.append(SelectLoopIteration(loop_iterations=loop_iterations))
        return self


class LoopIterationQuery(Query):
    """Query class specifically for loop iteration executions."""

    pass


class FunctionCallQuery(Query):
    """Query class specifically for function executions."""

    pass


class BranchQuery(Query):
    """Query class specifically for branch executions."""

    pass


class QueryEngine:
    """Query engine interface."""

    def __init__(self, execution_context: "ExecutionContext"):
        self.execution_context = execution_context

    def create_query(self) -> Query:
        """Create a new query instance."""
        return Query(self.execution_context)
