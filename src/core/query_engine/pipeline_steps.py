import operator
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, cast, override

from src.core.query_engine.query_engine_exception import (
    InvalidOperatorError,
    QueryEngineError,
)
from src.core.query_engine.utils import get_field_value
from src.models.tracer_models import (
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
    group_fields: dict[str, str]
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
                key = tuple(
                    get_field_value(item, field) for field in self.group_fields.values()
                )
                grouped_items[key].append(item)
        else:
            grouped_items = {(): items}

        aggregated_result: list[dict[str, Any]] = []
        for key, group in grouped_items.items():
            agg_result = {
                field: value
                for field, value in zip(self.group_fields.keys(), key, strict=True)
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
class JoinResult:
    """Contains the result of multiple join operations."""

    alias_to_items: dict[str, Any] = field(default_factory=dict[str, Any])

    def get(self, alias: str) -> Any:
        """Get items for a specific alias."""
        return self.alias_to_items.get(alias)

    def add_alias(self, alias: str, items: Any) -> None:
        """Add items for a specific alias."""
        if alias in self.alias_to_items:
            raise QueryEngineError(f"Alias '{alias}' is already used.")
        self.alias_to_items[alias] = items


@dataclass
class JoinStep(PipelineStepBase):
    other_items: list[Any]
    conditions: Callable[[Any, Any], bool]
    left_alias: str
    right_alias: str

    def __post_init__(self) -> None:
        """Validate join step parameters."""
        if self.left_alias == self.right_alias:
            raise QueryEngineError("Left and right aliases must be different.")

    def _create_joined_result(self, left_item: Any, right_item: Any) -> JoinResult:
        alias_to_items: dict[str, Any] = {}

        if isinstance(left_item, JoinResult):
            alias_to_items.update(left_item.alias_to_items)
        else:
            alias_to_items[self.left_alias] = left_item

        if self.right_alias in alias_to_items:
            raise QueryEngineError(f"Alias '{self.right_alias}' is already used.")
        alias_to_items[self.right_alias] = right_item

        return JoinResult(alias_to_items=alias_to_items)


@dataclass
class InnerJoinStep(JoinStep):
    """Return only matching items from both sides."""

    @override
    def apply(self, items: list[Any]) -> list[Any]:
        results: list[JoinResult] = []

        for left_item in items:
            for right_item in self.other_items:
                if self.conditions(left_item, right_item):
                    results.append(self._create_joined_result(left_item, right_item))
        return results


@dataclass
class LeftJoinStep(JoinStep):
    """Return all left items, with matching right items or None."""

    @override
    def apply(self, items: list[Any]) -> list[Any]:
        results: list[JoinResult] = []

        for left_item in items:
            matched = False
            for right_item in self.other_items:
                if self.conditions(left_item, right_item):
                    results.append(self._create_joined_result(left_item, right_item))
                    matched = True
            if not matched:
                results.append(self._create_joined_result(left_item, None))
        return results


@dataclass
class RightJoinStep(JoinStep):
    """Return all right items, with matching left items or None."""

    @override
    def apply(self, items: list[Any]) -> list[Any]:
        results: list[JoinResult] = []

        for right_item in self.other_items:
            matched = False
            for left_item in items:
                if self.conditions(left_item, right_item):
                    results.append(self._create_joined_result(left_item, right_item))
                    matched = True
            if not matched:
                results.append(self._create_joined_result(None, right_item))
        return results


@dataclass
class FullOuterJoinStep(JoinStep):
    """Return all items from both sides, with None for non-matches."""

    @override
    def apply(self, items: list[Any]) -> list[Any]:
        results: list[JoinResult] = []
        matched_right_indices: set[int] = set()

        for left_item in items:
            matched = False
            for right_index, right_item in enumerate(self.other_items):
                if self.conditions(left_item, right_item):
                    results.append(self._create_joined_result(left_item, right_item))
                    matched = True
                    matched_right_indices.add(right_index)
            if not matched:
                results.append(self._create_joined_result(left_item, None))

        for idx, right_item in enumerate(self.other_items):
            if idx not in matched_right_indices:
                results.append(self._create_joined_result(None, right_item))

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
    | JoinStep
)
