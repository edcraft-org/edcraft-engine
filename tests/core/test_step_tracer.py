from src.core.step_tracer.step_tracer import StepTracer
from src.models.tracer_models import LoopExecution


class TestStepTracer:
    """Test the step tracer functionality."""

    def test_simple_variable_assignment(self) -> None:
        """Test simple variable assignment tracking."""
        # Given
        source_code = "x = 1"

        # When
        step_tracer = StepTracer()
        transformed_code = step_tracer.transform_code(source_code)
        execution_context = step_tracer.execute_transformed_code(transformed_code)

        # Then
        assert "x" in execution_context.variable_snapshots
        assert len(execution_context.variable_snapshots["x"]) == 1
        assert execution_context.variable_snapshots["x"][0].value == 1

    def test_execute_for_loop_code(self) -> None:
        """Test executing for loop code with tracking."""
        # Given
        source_code = """
for i in range(3):
    x = i * 2
"""

        # When
        step_tracer = StepTracer()
        transformed_code = step_tracer.transform_code(source_code)
        execution_context = step_tracer.execute_transformed_code(transformed_code)

        # Then
        loop_executions = [
            ex
            for ex in execution_context.execution_trace
            if isinstance(ex, LoopExecution)
        ]
        assert len(loop_executions) == 1

        loop_exec = loop_executions[0]
        assert len(loop_exec.iterations) == 3
        assert loop_exec.loop_type == "for"

    def test_execute_while_loop_code(self) -> None:
        """Test executing while loop code with tracking."""
        # Given
        source_code = """
sum = 0
num = 5
while num > 0:
    sum += num
    num -= 1
"""

        # When
        step_tracer = StepTracer()
        transformed_code = step_tracer.transform_code(source_code)
        execution_context = step_tracer.execute_transformed_code(transformed_code)

        # Then
        loop_executions = [
            ex
            for ex in execution_context.execution_trace
            if isinstance(ex, LoopExecution)
        ]
        assert len(loop_executions) == 1

        loop_exec = loop_executions[0]
        assert len(loop_exec.iterations) == 5
        assert loop_exec.loop_type == "while"
