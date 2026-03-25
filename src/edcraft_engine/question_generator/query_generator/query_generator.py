from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

from query_engine import Query, QueryEngine
from query_engine.pipeline_steps import JoinResult
from step_tracer import ExecutionContext

from edcraft_engine.question_generator.models import OutputType, TargetElement


class QueryGenerator:
    def __init__(self, exec_ctx: ExecutionContext) -> None:
        self.query_engine = QueryEngine(exec_ctx)
        self.exec_ctx_items = exec_ctx.execution_trace + exec_ctx.variables
        self.join_idx = 0

    def generate_query(
        self, target: list[TargetElement], output_type: OutputType
    ) -> Query:
        """Generates a query based on the provided question request."""

        query = self.query_engine.create_query()

        # Select target
        for target_element in target:
            query = self._get_target(query, target_element)

        # Apply output type
        query = self._apply_output_type(query, output_type, target)

        query = self._apply_modifier(query, target)
        query = self._clean_output(query, target, output_type)

        return query

    def _get_target(self, query: Query, target: TargetElement) -> Query:
        if self.join_idx == 0:
            query = query.where(field="stmt_type", op="==", value=target.type)

            if target.name is not None:
                if target.type == "branch":
                    query = query.where(
                        field="condition_str", op="==", value=target.name
                    )
                elif target.type == "function":
                    query = query.where(
                        field="func_full_name", op="==", value=target.name
                    )
                else:
                    names = [n.strip() for n in target.name.split(",")]
                    query = query.where(field="name", op="in", value=names)

            if target.line_number is not None:
                is_def_line = target.type == "function" and any(
                    getattr(item, "func_def_line_num", None) == target.line_number
                    for item in self.exec_ctx_items
                )
                field = "func_def_line_num" if is_def_line else "line_number"
                query = query.where(field=field, op="==", value=target.line_number)

            if target.modifier is not None:
                if target.modifier in ("branch_true", "branch_false"):
                    condition_value = target.modifier == "branch_true"
                    query = query.where(
                        field="condition_result",
                        op="==",
                        value=condition_value,
                    )
                elif target.modifier == "loop_iterations":
                    query = query.left_join(
                        other_items=self.exec_ctx_items,
                        conditions=lambda left, right: (
                            left.stmt_type == "loop"
                            and right.stmt_type == "loop_iteration"
                            and right.loop_execution_id == left.execution_id
                        ),
                        left_alias=f"{self.join_idx}",
                        right_alias=f"{self.join_idx+1}",
                    )
                    self.join_idx += 1

            return query

        join_idx = self.join_idx
        target_names = (
            [n.strip() for n in target.name.split(",")]
            if target.name is not None
            else None
        )

        def join_condition(left: Any, right: Any) -> bool:
            left_exec = left.get(f"{join_idx}") if join_idx > 0 else left
            if left_exec is None:
                return False

            right_name = None
            if target.type == "function" and hasattr(right, "func_full_name"):
                right_name = right.func_full_name
            elif target.type == "branch" and hasattr(right, "condition_str"):
                right_name = right.condition_str
            elif hasattr(right, "name"):
                right_name = right.name

            scope_check = True
            if target.type == "variable":
                time_range_check = right.execution_id <= left_exec.end_execution_id
                scope_check = right.scope_id == left_exec.scope_id
            else:
                time_range_check = (
                    left_exec.execution_id <= right.execution_id
                    and right.execution_id <= left_exec.end_execution_id
                )

            branch_modifier_check = True
            if target.type == "branch" and hasattr(right, "condition_result"):
                if target.modifier == "branch_true":
                    branch_modifier_check = right.condition_result
                elif target.modifier == "branch_false":
                    branch_modifier_check = not right.condition_result

            return (
                right.stmt_type == target.type
                and (target_names is None or right_name in target_names)
                and (
                    target.line_number is None
                    or right.line_number == target.line_number
                )
                and time_range_check
                and (target.type != "variable" or scope_check)
                and (
                    target.modifier != "loop_iterations"
                    or (
                        right.stmt_type == "loop_iteration"
                        and right.loop_execution_id == left_exec.execution_id
                    )
                )
                and branch_modifier_check
            )

        query = query.left_join(
            other_items=self.exec_ctx_items,
            conditions=join_condition,
            left_alias=f"{self.join_idx}",
            right_alias=f"{self.join_idx+1}",
        )
        self.join_idx += 1
        return query

    def _apply_group_by(self, query: Query) -> Query:
        if self.join_idx > 0:
            group_fields = [f"{alias}.execution_id" for alias in range(self.join_idx)]
            query = query.group_by(*group_fields)
        return query

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

    def _apply_output_type(
        self, query: Query, output_type: str, target: list[TargetElement] | None = None
    ) -> Query:
        if output_type == "count":
            query = self._apply_group_by(query)
            query = query.agg(
                count=lambda items: len([item for item in items if item is not None])
            ).select("count")

        elif output_type == "list":
            last = target[-1] if target else None
            is_variable_join = (
                self.join_idx > 0
                and last is not None
                and last.type == "variable"
            )
            if is_variable_join:
                join_idx = self.join_idx
                query = self._apply_group_by(query)

                def pick_first_list(
                    candidates: list[Any], parent: Any, var_key: Callable
                ) -> Any:
                    parent_start = parent.execution_id if parent is not None else 0
                    outside = [
                        x for x in candidates
                        if x.get(f"{join_idx}").execution_id < parent_start
                    ]
                    if outside:
                        return max(outside, key=var_key)
                    return min(candidates, key=var_key) if candidates else None

                query = query.agg(
                    list_item=self._make_variable_aggregator(join_idx, last, pick_first_list)
                ).select("list_item")
            elif (
                self.join_idx == 0
                and last is not None
                and last.type == "variable"
                and last.name is not None
                and "," in last.name
            ):
                names = [n.strip() for n in last.name.split(",")]
                query = query.agg(
                    grouped=lambda items: {
                        name: [x.value for x in items if x.name == name]
                        for name in names
                    }
                ).select("grouped")

        elif output_type == "first":
            last = target[-1] if target else None
            is_variable_join = (
                self.join_idx > 0 and last is not None and last.type == "variable"
            )
            query = self._apply_group_by(query)

            if is_variable_join:
                join_idx = self.join_idx

                def pick_first(
                    candidates: list[Any], parent: Any, var_key: Callable
                ) -> Any:
                    parent_start = parent.execution_id if parent is not None else 0
                    outside = [
                        x
                        for x in candidates
                        if x.get(f"{join_idx}").execution_id < parent_start
                    ]
                    if outside:
                        return max(outside, key=var_key)
                    return min(candidates, key=var_key) if candidates else None

                query = query.agg(
                    first_item=self._make_variable_aggregator(
                        join_idx, last, pick_first
                    )
                ).select("first_item")
            else:
                is_variable_target = last is not None and last.type == "variable"
                key = self._make_key(is_variable_target)
                query = query.agg(first_item=lambda items: min(items, key=key)).select(
                    "first_item"
                )

        elif output_type == "last":
            last = target[-1] if target else None
            is_variable_join = (
                self.join_idx > 0 and last is not None and last.type == "variable"
            )
            query = self._apply_group_by(query)

            if is_variable_join:
                join_idx = self.join_idx

                def pick_last(
                    candidates: list[Any], parent: Any, var_key: Callable
                ) -> Any:
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

                query = query.agg(
                    last_item=self._make_variable_aggregator(join_idx, last, pick_last)
                ).select("last_item")
            else:
                is_variable_target = last is not None and last.type == "variable"
                key = self._make_key(is_variable_target)
                query = query.agg(last_item=lambda items: max(items, key=key)).select(
                    "last_item"
                )

        return query

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
        last = target[-1] if target else None
        if last is None or last.modifier not in ("arguments", "return_value"):
            return query

        if self.join_idx == 0:
            query = query.select(last.modifier)
            if last.modifier == "arguments" and last.argument_keys:
                query = self._apply_argument_keys(query, last.argument_keys)
        else:
            prefix = f"{self.join_idx}."
            query = query.select(f"{prefix}{last.modifier}")
            if last.modifier == "arguments" and last.argument_keys:
                query = self._apply_argument_keys(query, last.argument_keys)
        return query

    def _clean_output(
        self, query: Query, target: list[TargetElement], output_type: OutputType
    ) -> Query:
        if output_type == "count":
            return query

        prefix = f"{self.join_idx}." if self.join_idx > 0 else ""
        last = target[-1] if target else None
        if last is not None and last.type == "variable":
            if last.name is not None:
                if not (output_type == "list" and self.join_idx == 0 and "," in last.name):
                    query = query.select(f"{prefix}value")
            else:
                query = query.select(f"{prefix}name", f"{prefix}value")
        elif last is not None and last.modifier == "arguments":
            if not last.argument_keys:
                query = query.map(
                    lambda args: (
                        next(iter(args.values()))
                        if isinstance(args, dict) and len(args) == 1
                        else args
                    )
                )
        return query
