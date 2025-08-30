from dataclasses import dataclass
from typing import Any


class StatementExecution:
    """Base class for recording statement execution."""

    def __init__(self, execution_id: str, line_number: int, stmt_type: str):
        self.execution_id = execution_id
        self.line_number = line_number
        self.stmt_type = stmt_type

    def __repr__(self) -> str:
        attrs: dict[str, Any] = {
            "id": self.execution_id,
            "line": self.line_number,
            "type": self.stmt_type,
        }
        attrs_str = " ".join(f"{k}={v}" for k, v in attrs.items())
        return f"<{self.__class__.__name__} {attrs_str}>"


class LoopIteration(StatementExecution):
    """Records loop iteration execution."""

    def __init__(self, execution_id: str, line_number: int, loop_type: str):
        super().__init__(execution_id, line_number, "loop")
        self.loop_type = loop_type

    def __repr__(self) -> str:
        attrs: dict[str, Any] = {
            "id": self.execution_id,
            "line": self.line_number,
            "type": self.stmt_type,
            "loop_type": self.loop_type,
        }
        attrs_str = " ".join(f"{k}={v}" for k, v in attrs.items())
        return f"<{self.__class__.__name__} {attrs_str}>"


class FunctionCall(StatementExecution):
    """Records function call execution."""

    def __init__(
        self,
        execution_id: str,
        line_number: int,
        function_name: str,
        func_call_exec_ctx_id: str,
    ):
        super().__init__(execution_id, line_number, "function")
        self.function_name = function_name
        self.func_def_line_num: int | None = None
        self.arguments: dict[str, Any] = {}
        self.return_value: Any = None
        self.func_call_exec_ctx_id = func_call_exec_ctx_id

    def add_arg(self, name: str, value: Any) -> None:
        self.arguments[name] = value

    def set_func_def_line_num(self, line_num: int) -> None:
        self.func_def_line_num = line_num

    def set_return_value(self, return_value: Any) -> None:
        self.return_value = return_value

    def __repr__(self) -> str:
        attrs: dict[str, Any] = {
            "id": self.execution_id,
            "line": self.line_number,
            "type": self.stmt_type,
            "function_name": self.function_name,
            "args": self.arguments,
            "return_value": self.return_value,
        }
        attrs_str = " ".join(f"{k}={v}" for k, v in attrs.items())
        return f"<{self.__class__.__name__} {attrs_str}>"


class BranchExecution(StatementExecution):
    """Records if/else execution."""

    def __init__(self, execution_id: str, line_number: int, condition: bool):
        super().__init__(execution_id, line_number, "branch")
        self.condition = condition

    def __repr__(self) -> str:
        attrs: dict[str, Any] = {
            "id": self.execution_id,
            "line": self.line_number,
            "type": self.stmt_type,
            "condition": self.condition,
        }
        attrs_str = " ".join(f"{k}={v}" for k, v in attrs.items())
        return f"<{self.__class__.__name__} {attrs_str}>"


@dataclass
class VariableSnapshot:
    """Records a variable's value at a specific point in execution."""

    name: str
    value: Any
    access_path: str
    line_number: int
    scope_id: str
    execution_id: str


class Scope:
    """Represents a variable namespace."""

    def __init__(self, scope_type: str, scope_id: str, parent: "Scope | None" = None):
        self.scope_type = scope_type  # 'global', 'function', 'class'
        self.scope_id = scope_id
        self.parent = parent
        self.children: list[Scope] = []

        if parent:
            parent.children.append(self)


class ExecutionContext:
    """Manages overall program execution state."""

    def __init__(self) -> None:
        self.execution_trace: list[StatementExecution] = []
        self.variables: list[VariableSnapshot] = []

        self.execution_stack: list[StatementExecution] = []
        self.scope_stack: list[Scope] = []

        self._execution_counter: int = 0
        self._scope_counter = 0

        self.global_scope = Scope("global", "global_0")
        self.scope_stack.append(self.global_scope)

    @property
    def current_execution(self) -> StatementExecution | None:
        return self.execution_stack[-1] if self.execution_stack else None

    @property
    def current_scope(self) -> Scope:
        return self.scope_stack[-1]

    def generate_execution_id(self) -> str:
        self._execution_counter += 1
        return f"exec_{self._execution_counter}"

    def generate_scope_id(self) -> str:
        self._scope_counter += 1
        return f"scope_{self._scope_counter}"

    def push_scope(self, scope: Scope) -> None:
        self.scope_stack.append(scope)

    def pop_scope(self) -> Scope:
        return self.scope_stack.pop()

    def push_execution(self, execution: StatementExecution) -> None:
        self.execution_trace.append(execution)
        self.execution_stack.append(execution)

    def pop_execution(self) -> None:
        self.execution_stack.pop()

    def pop_until_function(self) -> None:
        while self.execution_stack:
            top = self.execution_stack[-1]
            if isinstance(top, FunctionCall):
                break
            self.execution_stack.pop()
            self.pop_scope()

    def record_loop_iteration(self, line_number: int, loop_type: str) -> None:
        execution_id = self.generate_execution_id()
        loop_execution = LoopIteration(execution_id, line_number, loop_type)
        self.push_execution(loop_execution)

    def record_function_call(self, line_number: int, function_name: str) -> None:
        execution_id = self.generate_execution_id()
        func_call_exec_ctx_id = (
            self.current_execution.execution_id if self.current_execution else "global"
        )
        function_execution = FunctionCall(
            execution_id, line_number, function_name, func_call_exec_ctx_id
        )
        self.push_execution(function_execution)
        self.push_scope(Scope("function", self.generate_scope_id(), self.current_scope))

    def record_branch_execution(self, line_number: int, condition: bool) -> None:
        execution_id = self.generate_execution_id()
        branch_execution = BranchExecution(execution_id, line_number, condition)
        self.push_execution(branch_execution)

    def record_variable(
        self, name: str, value: Any, access_path: str, line_number: int
    ) -> None:
        execution_id = (
            self.current_execution.execution_id if self.current_execution else "global"
        )
        scope_id = self.current_scope.scope_id
        snapshot = VariableSnapshot(
            name=name,
            value=value,
            access_path=access_path,
            line_number=line_number,
            scope_id=scope_id,
            execution_id=execution_id,
        )
        self.variables.append(snapshot)
