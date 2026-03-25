from collections.abc import Callable
from typing import Any

from query_engine import Query, QueryEngine
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
                    query = query.where(field="name", op="==", value=target.name)

            if target.line_number is not None:
                is_def_line = target.type == "function" and any(
                    getattr(item, "func_def_line_num", None) == target.line_number
                    for item in self.exec_ctx_items
                )
                field = "func_def_line_num" if is_def_line else "line_number"
                query = query.where(
                    field=field, op="==", value=target.line_number
                )

            if target.modifier is not None:
                if target.modifier in ("arguments", "return_value"):
                    query = query.select(target.modifier)
                elif target.modifier in ("branch_true", "branch_false"):
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
                and (target.name is None or right_name == target.name)
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
            group_fields = [
                f"{alias}.execution_id" for alias in range(self.join_idx)
            ]
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
            pass

        elif output_type == "first":
            last = target[-1] if target else None
            is_variable_join = (
                self.join_idx > 0 and last is not None and last.type == "variable"
            )
            query = self._apply_group_by(query)

            if is_variable_join:
                join_idx = self.join_idx
                parent_idx = join_idx - 1

                def first_variable(items: list[Any]) -> Any:
                    # execution_id of the parent context (e.g. loop iteration) marks
                    # the boundary between "assigned before" and "assigned inside".
                    parent = items[0].get(f"{parent_idx}") if items else None
                    parent_start = parent.execution_id if parent is not None else 0

                    def var_key(x: Any) -> Any:
                        item = x.get(f"{join_idx}")
                        return getattr(item, "var_id", 0)

                    # Prefer the most recent assignment made before the current context.
                    outside = [
                        x
                        for x in items
                        if x.get(f"{join_idx}") is not None
                        and x.get(f"{join_idx}").execution_id < parent_start
                    ]
                    if outside:
                        return max(outside, key=var_key)

                    # No prior assignment — fall back to the earliest assignment inside.
                    inside = [x for x in items if x.get(f"{join_idx}") is not None]
                    return (
                        min(inside, key=var_key)
                        if inside
                        else (items[0] if items else None)
                    )

                query = query.agg(first_item=first_variable).select("first_item")
            else:
                is_variable_target = last is not None and last.type == "variable"
                key = self._make_key(is_variable_target)
                query = query.agg(
                    first_item=lambda items: min(items, key=key)
                ).select("first_item")

        elif output_type == "last":
            last = target[-1] if target else None
            is_variable_target = last is not None and last.type == "variable"
            query = self._apply_group_by(query)
            key = self._make_key(is_variable_target)
            query = query.agg(last_item=lambda items: max(items, key=key)).select(
                "last_item"
            )

        return query

    def _apply_modifier(self, query: Query, target: list[TargetElement]) -> Query:
        """Applies the last target's modifier as a field selection (for chained targets)."""
        if self.join_idx == 0:
            return query

        last = target[-1] if target else None
        if last is not None and last.modifier in ("arguments", "return_value"):
            prefix = f"{self.join_idx}."
            query = query.select(f"{prefix}{last.modifier}")
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
                query = query.select(f"{prefix}value")
            else:
                query = query.select(f"{prefix}name", f"{prefix}value")
        elif last is not None and last.modifier == "arguments":
            query = query.map(
                lambda args: (
                    next(iter(args.values()))
                    if isinstance(args, dict) and len(args) == 1
                    else args
                )
            )
        return query
