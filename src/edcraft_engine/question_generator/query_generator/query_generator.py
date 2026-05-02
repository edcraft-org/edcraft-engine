from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

from query_engine import Query, QueryEngine
from query_engine.pipeline_steps import JoinResult
from step_tracer import ExecutionContext
from step_tracer.models import (
    BranchExecution,
    FunctionCall,
    LoopIteration,
    StatementExecution,
    VariableSnapshot,
)

from edcraft_engine.question_generator.models import OutputType, TargetElement

_Item = StatementExecution | VariableSnapshot


class _TargetType:
    BRANCH = "branch"
    FUNCTION = "function"
    VARIABLE = "variable"
    LOOP = "loop"
    LOOP_ITERATION = "loop_iteration"


class _Modifier:
    BRANCH_TRUE = "branch_true"
    BRANCH_FALSE = "branch_false"
    LOOP_ITERATIONS = "loop_iterations"
    ARGUMENTS = "arguments"
    RETURN_VALUE = "return_value"


class QueryGenerator:
    def __init__(self, exec_ctx: ExecutionContext) -> None:
        self.query_engine = QueryEngine(exec_ctx)
        self.exec_ctx_items = exec_ctx.execution_trace + exec_ctx.variables
        self.join_idx = 0
        self._first_target_done = False

    def generate_query(
        self, target: list[TargetElement], output_type: OutputType
    ) -> Query:
        """Generates a query based on the provided question request."""
        self._first_target_done = False
        self.join_idx = 0

        query = self.query_engine.create_query()

        for target_element in target:
            query = self._get_target(query, target_element)

        query = self._apply_output_type(query, output_type, target)
        query = self._apply_modifier(query, target)
        query = self._clean_output(query, target, output_type)

        return query

    @staticmethod
    def _last_target(target: list[TargetElement]) -> TargetElement | None:
        return target[-1] if target else None

    def _is_variable_join(self, last: TargetElement | None) -> bool:
        return (
            self.join_idx > 0 and last is not None and last.type == _TargetType.VARIABLE
        )

    def _get_target(self, query: Query, target: TargetElement) -> Query:
        if not self._first_target_done:
            self._first_target_done = True
            return self._get_target_first(query, target)
        return self._get_target_join(query, target)

    def _get_target_first(self, query: Query, target: TargetElement) -> Query:
        query = query.where(field="stmt_type", op="==", value=target.type)

        if target.name is not None:
            query = self._apply_name_filter(query, target)

        if target.line_number is not None:
            is_def_line = target.type == _TargetType.FUNCTION and any(
                getattr(item, "func_def_line_num", None) == target.line_number
                for item in self.exec_ctx_items
            )
            field = "func_def_line_num" if is_def_line else "line_number"
            query = query.where(field=field, op="==", value=target.line_number)

        if target.modifier is not None:
            if target.modifier in (_Modifier.BRANCH_TRUE, _Modifier.BRANCH_FALSE):
                condition_value = target.modifier == _Modifier.BRANCH_TRUE
                query = query.where(
                    field="condition_result",
                    op="==",
                    value=condition_value,
                )
            elif target.modifier == _Modifier.LOOP_ITERATIONS:
                query = query.left_join(
                    other_items=self.exec_ctx_items,
                    conditions=lambda left, right: (
                        left.stmt_type == _TargetType.LOOP
                        and right.stmt_type == _TargetType.LOOP_ITERATION
                        and right.loop_execution_id == left.execution_id
                    ),
                    left_alias=f"{self.join_idx}",
                    right_alias=f"{self.join_idx+1}",
                )
                self.join_idx += 1

        return query

    def _apply_name_filter(self, query: Query, target: TargetElement) -> Query:
        if target.name is None:
            return query
        if target.type == _TargetType.BRANCH:
            return query.where(field="condition_str", op="==", value=target.name)
        if target.type == _TargetType.FUNCTION:
            return query.where(field="func_full_name", op="==", value=target.name)
        names = [n.strip() for n in target.name.split(",")]
        return query.where(field="name", op="in", value=names)

    def _get_target_join(self, query: Query, target: TargetElement) -> Query:
        join_idx = self.join_idx
        target_names = (
            [n.strip() for n in target.name.split(",")]
            if target.name is not None
            else None
        )

        def join_condition(left: _Item | JoinResult, right: _Item) -> bool:
            raw = left.get(f"{join_idx}") if isinstance(left, JoinResult) else left
            if raw is None or not isinstance(raw, StatementExecution):
                return False
            left_exec = raw
            return (
                self._check_stmt_type(right, target)
                and self._check_name_match(right, target, target_names)
                and self._check_line_number(right, target)
                and self._check_time_range(left_exec, right, target)
                and self._check_scope(left_exec, right, target)
                and self._check_loop_iterations(left_exec, right, target)
                and self._check_branch_modifier(right, target)
            )

        query = query.left_join(
            other_items=self.exec_ctx_items,
            conditions=join_condition,
            left_alias=f"{self.join_idx}",
            right_alias=f"{self.join_idx+1}",
        )
        self.join_idx += 1
        return query

    @staticmethod
    def _check_stmt_type(right: _Item, target: TargetElement) -> bool:
        return right.stmt_type == target.type

    @staticmethod
    def _check_name_match(
        right: _Item, target: TargetElement, target_names: list[str] | None
    ) -> bool:
        if target_names is None:
            return True
        if target.type == _TargetType.FUNCTION and isinstance(right, FunctionCall):
            return right.func_full_name in target_names
        if target.type == _TargetType.BRANCH and isinstance(right, BranchExecution):
            return right.condition_str in target_names
        if isinstance(right, VariableSnapshot | FunctionCall):
            return right.name in target_names
        return False

    @staticmethod
    def _check_line_number(right: _Item, target: TargetElement) -> bool:
        if target.line_number is None:
            return True
        if target.type == _TargetType.FUNCTION:
            return (
                getattr(right, "func_def_line_num", None) == target.line_number
                or right.line_number == target.line_number
            )
        return right.line_number == target.line_number

    @staticmethod
    def _check_time_range(
        left_exec: StatementExecution, right: _Item, target: TargetElement
    ) -> bool:
        left_end_exec_id = left_exec.end_execution_id
        if left_end_exec_id is None:
            left_end_exec_id = right.execution_id
        if target.type == _TargetType.VARIABLE:
            return right.execution_id <= left_end_exec_id
        return (
            left_exec.execution_id <= right.execution_id
            and right.execution_id <= left_end_exec_id
        )

    @staticmethod
    def _check_scope(
        left_exec: StatementExecution, right: _Item, target: TargetElement
    ) -> bool:
        if target.type != _TargetType.VARIABLE:
            return True
        if isinstance(left_exec, FunctionCall):
            return right.scope_id == left_exec.func_scope_id
        return right.scope_id == left_exec.scope_id

    @staticmethod
    def _check_loop_iterations(
        left_exec: StatementExecution, right: _Item, target: TargetElement
    ) -> bool:
        if target.modifier != _Modifier.LOOP_ITERATIONS:
            return True
        return (
            isinstance(right, LoopIteration)
            and right.loop_execution_id == left_exec.execution_id
        )

    @staticmethod
    def _check_branch_modifier(right: _Item, target: TargetElement) -> bool:
        if not isinstance(right, BranchExecution):
            return True
        if target.modifier == _Modifier.BRANCH_TRUE:
            return right.condition_result
        if target.modifier == _Modifier.BRANCH_FALSE:
            return not right.condition_result
        return True

    def _apply_group_by(self, query: Query) -> Query:
        if self.join_idx > 0:
            group_fields = [f"{alias}.execution_id" for alias in range(self.join_idx)]
            query = query.group_by(*group_fields)
        return query

    def _apply_output_type(
        self, query: Query, output_type: str, target: list[TargetElement] | None = None
    ) -> Query:
        if output_type == "count":
            return self._apply_count_output(query)
        if output_type == "list":
            return self._apply_list_output(query, target or [])
        if output_type == "first":
            return self._apply_first_output(query, target or [])
        if output_type == "last":
            return self._apply_last_output(query, target or [])
        return query

    def _apply_count_output(self, query: Query) -> Query:
        query = self._apply_group_by(query)
        last_alias = f"{self.join_idx}"
        return query.agg(
            count=lambda items: len(
                [
                    item
                    for item in items
                    if item is not None
                    and (
                        not isinstance(item, JoinResult)
                        or item.get(last_alias) is not None
                    )
                ]
            )
        ).select("count")

    def _apply_list_output(self, query: Query, target: list[TargetElement]) -> Query:
        last = self._last_target(target)
        if self._is_variable_join(last):
            join_idx = self.join_idx
            query = self._apply_group_by(query)
            return query.agg(
                list_item=self._make_all_values_aggregator(join_idx, last)
            ).select("list_item")
        if (
            self.join_idx == 0
            and last is not None
            and last.type == _TargetType.VARIABLE
            and last.name is not None
            and "," in last.name
        ):
            names = [n.strip() for n in last.name.split(",")]
            return query.agg(
                grouped=lambda items: {
                    name: [x.value for x in items if x.name == name] for name in names
                }
            ).select("grouped")
        return query

    def _apply_first_output(self, query: Query, target: list[TargetElement]) -> Query:
        last = self._last_target(target)
        query = self._apply_group_by(query)
        if self._is_variable_join(last):
            join_idx = self.join_idx
            picker = self._make_picker(join_idx, before_parent=True)
            return query.agg(
                first_item=self._make_variable_aggregator(join_idx, last, picker)
            ).select("first_item")
        is_variable_target = last is not None and last.type == _TargetType.VARIABLE
        key = self._make_key(is_variable_target)
        last_alias = f"{self.join_idx}"
        return query.agg(
            first_item=lambda items: min(
                (
                    x
                    for x in items
                    if not isinstance(x, JoinResult) or x.get(last_alias) is not None
                ),
                key=key,
                default=None,
            )
        ).select("first_item")

    def _apply_last_output(self, query: Query, target: list[TargetElement]) -> Query:
        last = self._last_target(target)
        query = self._apply_group_by(query)
        if self._is_variable_join(last):
            join_idx = self.join_idx
            picker = self._make_picker(join_idx, before_parent=False)
            return query.agg(
                last_item=self._make_variable_aggregator(join_idx, last, picker)
            ).select("last_item")
        is_variable_target = last is not None and last.type == _TargetType.VARIABLE
        key = self._make_key(is_variable_target)
        last_alias = f"{self.join_idx}"
        return query.agg(
            last_item=lambda items: max(
                (
                    x
                    for x in items
                    if not isinstance(x, JoinResult) or x.get(last_alias) is not None
                ),
                key=key,
                default=None,
            )
        ).select("last_item")

    def _make_key(
        self, is_variable_target: bool
    ) -> Callable[[Any], int | tuple[int, int]]:
        join_idx = self.join_idx
        if join_idx > 0:
            if is_variable_target:

                def key(x: Any) -> int | tuple[int, int]:
                    item = x.get(f"{join_idx}")
                    return -1 if item is None else getattr(item, "var_id", 0)

            else:

                def key(x: Any) -> int | tuple[int, int]:
                    item = x.get(f"{join_idx}")
                    if item is None:
                        return (-1, -1)
                    return (item.execution_id, getattr(item, "var_id", 0))

        else:
            if is_variable_target:

                def key(x: Any) -> int | tuple[int, int]:
                    return getattr(x, "var_id", 0)

            else:

                def key(x: Any) -> int | tuple[int, int]:
                    return (x.execution_id, getattr(x, "var_id", 0))

        return key

    @staticmethod
    def _make_picker(
        join_idx: int, *, before_parent: bool
    ) -> Callable[[list[Any], Any, Callable], Any]:
        """Returns a picker that selects the best candidate relative to the parent scope.

        before_parent=True (first/list): prefer candidates starting before the parent,
        fall back to the earliest overall.
        before_parent=False (last): prefer candidates inside the parent's range,
        fall back to the latest overall.
        """
        if before_parent:

            def picker(candidates: list[Any], parent: Any, var_key: Callable) -> Any:
                parent_start = parent.execution_id if parent is not None else 0
                outside = [
                    x
                    for x in candidates
                    if x.get(f"{join_idx}").execution_id < parent_start
                ]
                if outside:
                    return max(outside, key=var_key)
                return min(candidates, key=var_key) if candidates else None

        else:

            def picker(candidates: list[Any], parent: Any, var_key: Callable) -> Any:
                parent_end = (
                    parent.end_execution_id if parent is not None else float("inf")
                )
                inside = [
                    x
                    for x in candidates
                    if x.get(f"{join_idx}").execution_id <= parent_end
                ]
                if inside:
                    return max(inside, key=var_key)
                return max(candidates, key=var_key) if candidates else None

        return picker

    def _make_all_values_aggregator(
        self,
        join_idx: int,
        last: TargetElement | None,
    ) -> Callable[[list[Any]], Any]:
        def aggregator(items: list[Any]) -> Any:
            candidates = sorted(
                (x for x in items if x.get(f"{join_idx}") is not None),
                key=lambda x: x.get(f"{join_idx}").var_id,
            )
            return [x.get(f"{join_idx}").value for x in candidates]

        return aggregator

    def _make_variable_aggregator(
        self,
        join_idx: int,
        last: TargetElement | None,
        pick_for_name: Callable[[list[Any], Any, Callable], Any],
    ) -> Callable[[list[Any]], Any]:
        parent_idx = join_idx - 1
        var_names = (
            [n.strip() for n in last.name.split(",")]
            if last is not None and last.name is not None and "," in last.name
            else None
        )

        def aggregator(items: list[Any]) -> Any:
            parent = items[0].get(f"{parent_idx}") if items else None

            def var_key(x: Any) -> Any:
                return getattr(x.get(f"{join_idx}"), "var_id", 0)

            def pick(name: str | None) -> Any:
                candidates = (
                    [
                        x
                        for x in items
                        if x.get(f"{join_idx}") is not None
                        and x.get(f"{join_idx}").name == name
                    ]
                    if name is not None
                    else [x for x in items if x.get(f"{join_idx}") is not None]
                )
                return pick_for_name(candidates, parent, var_key)

            if var_names is not None:
                values = tuple(
                    r.get(f"{join_idx}").value if r is not None else None
                    for r in (pick(name) for name in var_names)
                )
                base = items[0] if items else JoinResult()
                result = JoinResult()
                for alias, val in base.alias_to_items.items():
                    if alias != f"{join_idx}":
                        result.add_alias(alias, val)
                result.add_alias(f"{join_idx}", SimpleNamespace(value=values))
                return result

            best = pick(None)
            return best if best is not None else (items[0] if items else None)

        return aggregator

    def _apply_argument_keys(self, query: Query, keys: list[str]) -> Query:
        """Filters an arguments dict down to specific keys."""
        if len(keys) == 1:
            k = keys[0]
            return query.map(
                lambda args: args.get(k) if isinstance(args, dict) else args
            )
        return query.map(
            lambda args: (
                {k: args[k] for k in keys if k in args}
                if isinstance(args, dict)
                else args
            )
        )

    def _apply_modifier(self, query: Query, target: list[TargetElement]) -> Query:
        """Applies the last target's modifier as a field selection after aggregation."""
        last = self._last_target(target)
        if last is None or last.modifier not in (
            _Modifier.ARGUMENTS,
            _Modifier.RETURN_VALUE,
        ):
            return query

        if self.join_idx == 0:
            query = query.select(last.modifier)
            if last.modifier == _Modifier.ARGUMENTS and last.argument_keys:
                query = self._apply_argument_keys(query, last.argument_keys)
        else:
            prefix = f"{self.join_idx}."
            query = query.select(f"{prefix}{last.modifier}")
            if last.modifier == _Modifier.ARGUMENTS and last.argument_keys:
                query = self._apply_argument_keys(query, last.argument_keys)
        return query

    def _clean_output(
        self, query: Query, target: list[TargetElement], output_type: OutputType
    ) -> Query:
        if output_type == "count":
            return query

        prefix = f"{self.join_idx}." if self.join_idx > 0 else ""
        last = self._last_target(target)
        if last is not None and last.type == _TargetType.VARIABLE:
            if last.name is not None:
                if not (
                    output_type == "list" and self.join_idx == 0 and "," in last.name
                ) and not (output_type == "list" and self._is_variable_join(last)):
                    query = query.select(f"{prefix}value")
            else:
                query = query.select(f"{prefix}name", f"{prefix}value")
        elif last is not None and last.modifier == _Modifier.ARGUMENTS:
            if not last.argument_keys:
                query = query.map(
                    lambda args: (
                        next(iter(args.values()))
                        if isinstance(args, dict) and len(args) == 1
                        else args
                    )
                )
        return query
