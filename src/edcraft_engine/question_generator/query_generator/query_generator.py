from typing import Any

from edcraft_engine.query_engine.query_engine import Query, QueryEngine
from edcraft_engine.question_generator.models import OutputType, TargetElement
from edcraft_engine.step_tracer.models import ExecutionContext


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
        query = self._apply_output_type(query, output_type)

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
                query = query.where(
                    field="line_number", op="==", value=target.line_number
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
            if hasattr(right, "name"):
                right_name = right.name
            elif target.type == "branch" and hasattr(right, "condition_str"):
                right_name = right.condition_str

            if target.type == "variable":
                time_range_check = right.execution_id <= left_exec.end_execution_id
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

    def _apply_output_type(self, query: Query, output_type: str) -> Query:
        if output_type == "count":
            if self.join_idx > 0:
                group_fields = [
                    f"{alias}.execution_id" for alias in range(self.join_idx)
                ]
                query = query.group_by(*group_fields)

            query = query.agg(
                count=lambda items: len([item for item in items if item is not None])
            ).select("count")

        elif output_type == "list":
            pass

        elif output_type == "first":
            if self.join_idx > 0:
                group_fields = [
                    f"{alias}.execution_id" for alias in range(self.join_idx)
                ]
                query = query.group_by(*group_fields)

                def key(x: Any) -> tuple[int, int]:
                    item = x.get(f"{self.join_idx}")
                    if item is None:
                        return (-1, -1)
                    var_id = getattr(item, "var_id", 0)
                    return (item.execution_id, var_id)

            else:

                def key(x: Any) -> tuple[int, int]:
                    var_id = getattr(x, "var_id", 0)
                    return (x.execution_id, var_id)

            query = query.agg(first_item=lambda items: min(items, key=key)).select(
                "first_item"
            )

        elif output_type == "last":
            if self.join_idx > 0:
                group_fields = [
                    f"{alias}.execution_id" for alias in range(self.join_idx)
                ]
                query = query.group_by(*group_fields)

                def key(x: Any) -> tuple[int, int]:
                    item = x.get(f"{self.join_idx}")
                    if item is None:
                        return (-1, -1)
                    var_id = getattr(item, "var_id", 0)
                    return (item.execution_id, var_id)

            else:

                def key(x: Any) -> tuple[int, int]:
                    var_id = getattr(x, "var_id", 0)
                    return (x.execution_id, var_id)

            query = query.agg(last_item=lambda items: max(items, key=key)).select(
                "last_item"
            )
        return query

    def _clean_output(
        self, query: Query, target: list[TargetElement], output_type: OutputType
    ) -> Query:
        if output_type == "count":
            return query

        prefix = f"{self.join_idx}." if self.join_idx > 0 else ""
        if len(target) > 0 and target[-1].type == "variable":
            if target[-1].name is not None:
                query = query.select(f"{prefix}value")
            else:
                query = query.select(f"{prefix}name", f"{prefix}value")
        return query
