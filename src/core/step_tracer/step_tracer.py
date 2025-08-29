import ast
from typing import Any

from src.core.step_tracer.step_tracer_utils import StepTracerUtils
from src.core.step_tracer.tracer_transformer import TracerTransformer
from src.models.tracer_models import ExecutionContext


class StepTracer:
    def transform_code(self, source_code: str) -> str:
        """Transform source code to include execution tracking."""
        tree = ast.parse(source_code)
        transformer = TracerTransformer()
        new_tree = transformer.visit(tree)
        ast.fix_missing_locations(new_tree)
        return ast.unparse(new_tree)

    def execute_transformed_code(
        self, transformed_code: str, globals_dict: dict[str, Any] | None = None
    ) -> ExecutionContext:
        """Transform and execute code with tracing."""
        if globals_dict is None:
            globals_dict = {}

        execution_context = ExecutionContext()
        step_tracer_utils = StepTracerUtils()

        globals_dict.update(
            {
                "_step_tracer_execution_context": execution_context,
                "_step_tracer_utils": step_tracer_utils,
            }
        )

        exec(transformed_code, globals_dict)
        return execution_context
