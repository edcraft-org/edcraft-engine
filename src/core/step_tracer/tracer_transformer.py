import ast


class TracerTransformer(ast.NodeTransformer):
    """AST transformer that injects execution tracking code."""

    execution_context_name = "_step_tracer_execution_context"

    ### Loop Tracking Code

    def visit_For(self, node: ast.For) -> list[ast.stmt]:
        """Transform for loops to track iterations."""
        self.generic_visit(node)
        loop_start, loop_end, iteration_start = self._create_loop_tracking_calls(
            node.lineno, "for"
        )
        node.body.insert(0, iteration_start)
        return [loop_start, node, loop_end]

    def visit_While(self, node: ast.While) -> list[ast.stmt]:
        """Transform while loops to track iterations."""
        self.generic_visit(node)
        loop_start, loop_end, iteration_start = self._create_loop_tracking_calls(
            node.lineno, "while"
        )
        node.body.insert(0, iteration_start)
        return [loop_start, node, loop_end]

    def _create_loop_tracking_calls(
        self, lineno: int, loop_type: str
    ) -> tuple[ast.stmt, ast.stmt, ast.stmt]:
        loop_start = ast.parse(
            f"{self.execution_context_name}.start_loop_execution({lineno}, {loop_type!r})"
        ).body[0]
        loop_end = self._create_pop_exec_call()
        iteration_start = ast.parse(
            f"{self.execution_context_name}.current_execution.start_iteration()"
        ).body[0]
        return loop_start, loop_end, iteration_start

    ### Function Tracking Code

    def visit_FunctionDef(self, node: ast.FunctionDef) -> list[ast.stmt]:
        """Transform function definitions to track execution."""
        self.generic_visit(node)

        start_function_stmt = self._create_start_function_call(node.lineno, node.name)
        new_body: list[ast.stmt] = [start_function_stmt]

        for arg in node.args.args:
            arg_tracking_call = self._create_add_arg_call(arg.arg)
            new_body.append(arg_tracking_call)
        new_body.extend(node.body)

        if not self._func_has_terminal_return(node.body):
            pop_call = self._create_pop_exec_call()
            new_body.append(pop_call)

        node.body = new_body
        return [node]

    # TODO: AsyncFunctionDef

    def visit_Return(self, node: ast.Return) -> list[ast.stmt]:
        temp_var_name = "_step_tracer_return_val"
        pop_until_func = self._create_pop_until_function_call()
        pop_func_call = self._create_pop_exec_call()

        if node.value is None:
            return [pop_until_func, pop_func_call, node]
        else:
            assign_node = ast.Assign(
                targets=[ast.Name(id=temp_var_name, ctx=ast.Store())], value=node.value
            )
            return_tracking_call = self._create_return_tracking_call(
                ast.Name(id=temp_var_name, ctx=ast.Load())
            )
            return_node = ast.Return(value=ast.Name(id=temp_var_name, ctx=ast.Load()))
            return [
                pop_until_func,
                assign_node,
                return_tracking_call,
                pop_func_call,
                return_node,
            ]

    def _create_start_function_call(self, lineno: int, function_name: str) -> ast.stmt:
        """Create a call to start a function execution context."""
        return ast.parse(
            f"{self.execution_context_name}.start_function_execution({lineno}, {function_name!r})"
        ).body[0]

    def _create_add_arg_call(self, arg: str) -> ast.stmt:
        """Create a call to add an argument to the current function execution context."""
        return ast.parse(
            f"{self.execution_context_name}.current_execution.add_arg({arg!r}, _step_tracer_utils.safe_deepcopy({arg}))"
        ).body[0]

    def _create_return_tracking_call(self, return_value: ast.expr) -> ast.stmt:
        """Create a call to track a function's return value."""
        return ast.Expr(
            ast.Call(
                func=ast.Attribute(
                    value=ast.Attribute(
                        value=ast.Name(id=self.execution_context_name, ctx=ast.Load()),
                        attr="current_execution",
                        ctx=ast.Load(),
                    ),
                    attr="add_return_value",
                    ctx=ast.Load(),
                ),
                args=[return_value],
                keywords=[],
            )
        )

    def _func_has_terminal_return(self, body: list[ast.stmt]) -> bool:
        """Check if the function body ends with a guaranteed return."""
        if not body:
            return False
        last_stmt = body[-1]
        return isinstance(last_stmt, ast.Return)

    def _create_pop_until_function_call(self) -> ast.Expr:
        return ast.Expr(
            ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id=self.execution_context_name, ctx=ast.Load()),
                    attr="pop_until_function",
                    ctx=ast.Load(),
                ),
                args=[],
                keywords=[],
            )
        )

    ### Variable Tracking Code

    def visit_Assign(self, node: ast.Assign) -> list[ast.stmt]:
        """Transform assignments to track variable changes."""
        self.generic_visit(node)

        statements: list[ast.stmt] = [node]

        for target in node.targets:
            variables = self._extract_variable_names(target)
            self._add_variable_tracking_calls(statements, variables, node.lineno)

        return statements

    def visit_AugAssign(self, node: ast.AugAssign) -> list[ast.stmt]:
        """Transform augmented assignments to track variable changes."""
        self.generic_visit(node)

        statements: list[ast.stmt] = [node]
        variables = self._extract_variable_names(node.target)
        self._add_variable_tracking_calls(statements, variables, node.lineno)

        return statements

    def visit_AnnAssign(self, node: ast.AnnAssign) -> list[ast.stmt]:
        """Transform annotated assignments to track variable changes."""
        self.generic_visit(node)

        if node.value is None:
            return [node]

        statements: list[ast.stmt] = [node]
        variables = self._extract_variable_names(node.target)
        self._add_variable_tracking_calls(statements, variables, node.lineno)

        return statements

    def _add_variable_tracking_calls(
        self, statements: list[ast.stmt], variables: list[tuple[str, str]], lineno: int
    ) -> None:
        for var_name, access_path in variables:
            track_call = self._create_variable_tracking_call(
                var_name, access_path, lineno
            )
            statements.append(track_call)

    def _extract_variable_names(self, target: ast.expr) -> list[tuple[str, str]]:
        """
        Extract all variable names from an assignment target.

        Returns a list of (var_name, access_path) tuples.
        """
        variables: list[tuple[str, str]] = []

        if isinstance(target, ast.Name):
            variables.append((target.id, target.id))
        elif isinstance(target, (ast.Tuple | ast.List)):
            for elt in target.elts:
                variables.extend(self._extract_variable_names(elt))
        elif isinstance(target, ast.Starred) and isinstance(target.value, ast.Name):
            variables.append((target.value.id, target.value.id))
        elif isinstance(target, (ast.Attribute | ast.Subscript)):
            base = self._get_base_name(target)
            if base:
                variables.append(base)

        return variables

    def _get_base_name(self, node: ast.expr) -> tuple[str, str] | None:
        """Extract the base name and access path."""
        if isinstance(node, ast.Name):
            return node.id, node.id
        elif isinstance(node, ast.Attribute):
            base = self._get_base_name(node.value)
            if base:
                base_name, access_path = base
                return base_name, f"{access_path}.{node.attr}"
        elif isinstance(node, ast.Subscript):
            base = self._get_base_name(node.value)
            if base:
                base_name, access_path = base
                index = ast.unparse(node.slice)
                return base_name, f"{access_path}[{index}]"
        return None

    def _create_variable_tracking_call(
        self, var_name: str, access_path: str, line_no: int
    ) -> ast.stmt:
        return ast.parse(
            f"{self.execution_context_name}.record_variable({var_name!r}, _step_tracer_utils.safe_deepcopy({access_path}), {access_path!r}, {line_no})"
        ).body[0]

    ### Variable tracking: handles method calls and mutatable objects passed to functions

    def visit_Expr(self, node: ast.Expr) -> list[ast.stmt]:
        self.generic_visit(node)

        if isinstance(node.value, ast.Call):
            call_node = node.value
            if isinstance(call_node.func, ast.Attribute):
                obj_name = self._get_base_name(call_node.func)
                if obj_name:
                    var_tracking_call = self._create_variable_tracking_call(
                        obj_name[0], obj_name[0], node.lineno
                    )
                    return [node, var_tracking_call]

        return [node]

    # ### Conditional Tracking Code

    def visit_If(self, node: ast.If) -> list[ast.stmt]:
        self.generic_visit(node)

        temp_test_condition = ast.Assign(
            targets=[ast.Name(id="_step_tracer_temp", ctx=ast.Store())], value=node.test
        )

        conditional_start = self._create_conditional_execution_call(
            node.lineno, ast.Name(id="_step_tracer_temp", ctx=ast.Load())
        )
        conditional_end = self._create_pop_exec_call()

        new_if = ast.If(
            test=ast.Name(id="_step_tracer_temp", ctx=ast.Load()),
            body=node.body,
            orelse=node.orelse,
        )

        return [temp_test_condition, conditional_start, new_if, conditional_end]

    def _create_conditional_execution_call(
        self, line_number: int, condition: ast.expr
    ) -> ast.stmt:
        """Create a call to track an if else branch."""
        return ast.Expr(
            ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id=self.execution_context_name, ctx=ast.Load()),
                    attr="start_conditional_execution",
                    ctx=ast.Load(),
                ),
                args=[ast.Constant(value=line_number), condition],
                keywords=[],
            )
        )

    ### General

    def _create_pop_exec_call(self) -> ast.stmt:
        """Create a call to pop the current execution context."""
        return ast.parse("_step_tracer_execution_context.pop_execution()").body[0]
