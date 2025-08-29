from collections import defaultdict
from dataclasses import dataclass
from typing import Any


@dataclass
class VariableSnapshot:
    """Records a variable's value at a specific point in execution."""

    name: str
    value: Any
    access_path: str
    line_number: int
    execution_id: str


class StatementExecution:
    """Base class for recording statement execution."""

    def __init__(self, execution_id: str, line_number: int, stmt_type: str):
        self.execution_id = execution_id
        self.line_number = line_number
        self.stmt_type = stmt_type


class LoopExecution(StatementExecution):
    """Records loop execution."""

    def __init__(self, execution_id: str, line_number: int, loop_type: str):
        super().__init__(execution_id, line_number, "loop")
        self.loop_type = loop_type
        self.iterations: list[IterationRecord] = []

    def start_iteration(self) -> None:
        iteration_num = len(self.iterations)
        iteration = IterationRecord(iteration_num, self.execution_id)
        self.iterations.append(iteration)

    def add_variable_snapshot(self, snapshot: VariableSnapshot) -> None:
        self.iterations[-1].add_variable_snapshot(snapshot)


class IterationRecord:
    """Records data for a single loop iteration."""

    def __init__(self, iteration_num: int, loop_execution_id: str):
        self.iteration_num = iteration_num
        self.loop_execution_id = loop_execution_id
        self.variable_snapshots: dict[str, list[VariableSnapshot]] = defaultdict(list)

    def add_variable_snapshot(self, snapshot: VariableSnapshot) -> None:
        self.variable_snapshots[snapshot.name].append(snapshot)


class FunctionExecution(StatementExecution):
    """Records function call execution."""

    def __init__(self, execution_id: str, line_number: int, function_name: str):
        super().__init__(execution_id, line_number, "function")
        self.function_name = function_name
        self.parameters: dict[str, Any] = {}
        self.return_value: Any = None
        self.variable_snapshots: dict[str, list[VariableSnapshot]] = defaultdict(list)

    def add_variable_snapshot(self, snapshot: VariableSnapshot) -> None:
        self.variable_snapshots[snapshot.name].append(snapshot)

    def add_arg(self, name: str, value: Any) -> None:
        self.parameters[name] = value

    def add_return_value(self, return_value: Any) -> None:
        self.return_value = return_value


class ConditionalExecution(StatementExecution):
    """Records if/elif/else execution."""

    def __init__(self, execution_id: str, line_number: int, condition: bool):
        super().__init__(execution_id, line_number, "conditional")
        self.branches: list[Branch] = []
        self.condition = condition
        self.variable_snapshots: dict[str, list[VariableSnapshot]] = defaultdict(list)

    def add_branch(self, line_number: int) -> None:
        branch = Branch(self.execution_id, line_number)
        self.branches.append(branch)

    def set_branch_taken(self) -> None:
        self.branches[-1].condition_value = True

    def add_variable_snapshot(self, snapshot: VariableSnapshot) -> None:
        self.variable_snapshots[snapshot.name].append(snapshot)


class Branch:
    """Records if/elif/else branch execution information."""

    def __init__(self, conditional_execution_id: str, line_number: int):
        self.conditional_execution_id = conditional_execution_id
        self.line_number = line_number
        self.condition_value = False


class ExecutionContext:
    """Manages overall program execution state."""

    def __init__(self) -> None:
        self.execution_trace: list[StatementExecution] = []
        self.execution_stack: list[StatementExecution] = []
        self.variable_snapshots: dict[str, list[VariableSnapshot]] = defaultdict(list)
        self._execution_counter: int = 0

    @property
    def current_execution(self) -> StatementExecution | None:
        return self.execution_stack[-1] if self.execution_stack else None

    def generate_execution_id(self) -> str:
        self._execution_counter += 1
        return f"exec_{self._execution_counter}"

    def push_execution(self, execution: StatementExecution) -> None:
        self.execution_trace.append(execution)
        self.execution_stack.append(execution)

    def pop_execution(self) -> None:
        self.execution_stack.pop()

    def pop_until_function(self) -> None:
        while self.execution_stack:
            top = self.execution_stack[-1]
            if isinstance(top, FunctionExecution):
                break
            self.execution_stack.pop()

    def start_loop_execution(self, line_number: int, loop_type: str) -> None:
        execution_id = self.generate_execution_id()
        loop_execution = LoopExecution(execution_id, line_number, loop_type)
        self.push_execution(loop_execution)

    def start_function_execution(self, line_number: int, function_name: str) -> None:
        execution_id = self.generate_execution_id()
        function_execution = FunctionExecution(execution_id, line_number, function_name)
        self.push_execution(function_execution)

    def start_conditional_execution(self, line_number: int, condition: bool) -> None:
        execution_id = self.generate_execution_id()
        conditional_execution = ConditionalExecution(
            execution_id, line_number, condition
        )
        self.push_execution(conditional_execution)

    def record_variable(
        self, name: str, value: Any, access_path: str, line_number: int
    ) -> None:
        execution_id = (
            self.current_execution.execution_id if self.current_execution else "global"
        )
        snapshot = VariableSnapshot(name, value, access_path, line_number, execution_id)

        if self.current_execution and isinstance(
            self.current_execution, (LoopExecution | FunctionExecution)
        ):
            self.current_execution.add_variable_snapshot(snapshot)
        else:
            self.variable_snapshots[snapshot.name].append(snapshot)
