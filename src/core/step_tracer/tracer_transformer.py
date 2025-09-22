import ast


class TracerTransformer(ast.NodeTransformer):
    """AST transformer that injects execution tracking code."""

    def __init__(self) -> None:
        super().__init__()
        self.exec_ctx_name = "_step_tracer_exec_ctx"

    ### Loop Tracking Code

    def visit_For(self, node: ast.For) -> list[ast.stmt]:
        """Transform for loops to track iterations."""
        self.generic_visit(node)
        loop_start, loop_end, iteration_start, iteration_end = (
            self._create_loop_tracking_calls(node.lineno, "for")
        )
        node.body.insert(0, iteration_start)
        node.body.append(iteration_end)
        return [loop_start, node, loop_end]

    def visit_While(self, node: ast.While) -> list[ast.stmt]:
        """Transform while loops to track iterations."""
        self.generic_visit(node)
        loop_start, loop_end, iteration_start, iteration_end = (
            self._create_loop_tracking_calls(node.lineno, "while")
        )
        node.body.insert(0, iteration_start)
        node.body.append(iteration_end)
        return [loop_start, node, loop_end]

    def _create_loop_tracking_calls(
        self, lineno: int, loop_type: str
    ) -> tuple[ast.stmt, ast.stmt, ast.stmt, ast.stmt]:
        loop_start = ast.parse(
            f"{self.exec_ctx_name}.record_loop_execution({lineno}, {loop_type!r})"
        ).body[0]
        loop_end = self._create_pop_exec_call()
        iteration_start = ast.parse(
            f"{self.exec_ctx_name}.record_loop_iteration()"
        ).body[0]
        iteration_end = self._create_pop_exec_call()
        return loop_start, loop_end, iteration_start, iteration_end

    ### Function Tracking Code

    def visit_Expr(self, node: ast.Expr) -> list[ast.stmt]:
        self.generic_visit(node)

        if isinstance(node.value, ast.Call):
            expanded_nodes: list[ast.stmt] = list(self.expand_call(node.value))

            # variable tracking: handles method calls with mutatable objects
            if isinstance(node.value.func, ast.Attribute):
                obj_name = self._get_base_name(node.value.func)
                if obj_name:
                    var_tracking_call = self._create_variable_tracking_call(
                        obj_name[0], obj_name[0], node.lineno
                    )
                    expanded_nodes.append(var_tracking_call)

            return expanded_nodes

        return [node]

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        """Transform function definitions to track execution."""
        self.generic_visit(node)

        reset_args_call = self._create_reset_args_call()
        set_func_def_line_num_call = self._create_set_func_def_line_num_call(
            node.lineno
        )
        new_body: list[ast.stmt] = [reset_args_call, set_func_def_line_num_call]

        for arg in node.args.args:
            arg_value_expr = ast.Name(id=arg.arg, ctx=ast.Load())
            arg_tracking_call = self._create_add_arg_call(arg.arg, arg_value_expr)
            new_body.append(arg_tracking_call)

            var_tracking_call = self._create_variable_tracking_call(
                arg.arg, arg.arg, node.lineno
            )
            new_body.append(var_tracking_call)

        new_body.extend(node.body)
        node.body = new_body

        return node

    def expand_call(
        self, node: ast.Call
    ) -> tuple[
        ast.Expr, *tuple[ast.Expr, ...], ast.Assign, ast.Expr, ast.Expr, ast.Expr
    ]:
        """Transform function calls to track execution."""
        self.generic_visit(node)

        # Record function call
        func_name = self._get_func_name(node.func)
        func_full_name = self._get_func_full_name(node.func)
        record_func_node = self._create_record_func_call(
            node, func_name, func_full_name
        )

        # Record arguments
        arg_stmts: list[ast.Expr] = []

        for idx, arg in enumerate(node.args):
            arg_stmts.append(self._create_add_arg_call(f"_arg{idx}", arg))

        for kw in node.keywords:
            if kw.arg:
                arg_stmts.append(self._create_add_arg_call(kw.arg, kw.value))

        # Record return value
        tmp_ret_var = "_step_tracer_tmp_ret"
        assign_node = ast.Assign(
            targets=[ast.Name(id=tmp_ret_var, ctx=ast.Store())],
            value=node,
        )
        record_ret_node = self._create_record_func_return_call(
            ast.Name(id=tmp_ret_var, ctx=ast.Load())
        )

        new_node = ast.Expr(ast.Name(id=tmp_ret_var, ctx=ast.Load()))
        pop_node = self._create_pop_exec_call()

        return (
            record_func_node,
            *arg_stmts,
            assign_node,
            record_ret_node,
            pop_node,
            new_node,
        )

    def _create_record_func_call(
        self, node: ast.Call, func_name: str, func_full_name: str
    ) -> ast.Expr:
        """Create a call to track a function call."""
        return ast.Expr(
            ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id=self.exec_ctx_name, ctx=ast.Load()),
                    attr="record_function_call",
                    ctx=ast.Load(),
                ),
                args=[
                    ast.Constant(value=node.lineno),
                    ast.Constant(value=func_name),
                    ast.Constant(value=func_full_name),
                ],
                keywords=[],
            )
        )

    def _create_add_arg_call(self, name: str, arg_value: ast.expr) -> ast.Expr:
        return ast.Expr(
            value=ast.Call(
                func=ast.Attribute(
                    value=ast.Attribute(
                        value=ast.Name(id=self.exec_ctx_name, ctx=ast.Load()),
                        attr="current_execution",
                        ctx=ast.Load(),
                    ),
                    attr="add_arg",
                    ctx=ast.Load(),
                ),
                args=[
                    ast.Constant(value=name),
                    ast.Call(
                        func=ast.Attribute(
                            value=ast.Name(id="_step_tracer_utils", ctx=ast.Load()),
                            attr="safe_deepcopy",
                            ctx=ast.Load(),
                        ),
                        args=[arg_value],
                        keywords=[],
                    ),
                ],
                keywords=[],
            )
        )

    def _create_record_func_return_call(self, return_value: ast.expr) -> ast.Expr:
        return ast.Expr(
            value=ast.Call(
                func=ast.Attribute(
                    value=ast.Attribute(
                        value=ast.Name(id=self.exec_ctx_name, ctx=ast.Load()),
                        attr="current_execution",
                        ctx=ast.Load(),
                    ),
                    attr="set_return_value",
                    ctx=ast.Load(),
                ),
                args=[
                    ast.Call(
                        func=ast.Attribute(
                            value=ast.Name(id="_step_tracer_utils", ctx=ast.Load()),
                            attr="safe_deepcopy",
                            ctx=ast.Load(),
                        ),
                        args=[return_value],
                        keywords=[],
                    ),
                ],
                keywords=[],
            )
        )

    def _create_set_func_def_line_num_call(self, line_num: int) -> ast.Expr:
        return ast.Expr(
            value=ast.Call(
                func=ast.Attribute(
                    value=ast.Attribute(
                        value=ast.Name(id=self.exec_ctx_name, ctx=ast.Load()),
                        attr="current_execution",
                        ctx=ast.Load(),
                    ),
                    attr="set_func_def_line_num",
                    ctx=ast.Load(),
                ),
                args=[ast.Constant(value=line_num)],
                keywords=[],
            )
        )

    # TODO: Refactor to reduce redundancy
    def _create_reset_args_call(self) -> ast.Expr:
        return ast.Expr(
            value=ast.Call(
                func=ast.Attribute(
                    value=ast.Attribute(
                        value=ast.Name(id=self.exec_ctx_name, ctx=ast.Load()),
                        attr="current_execution",
                        ctx=ast.Load(),
                    ),
                    attr="reset_args",
                    ctx=ast.Load(),
                ),
                args=[],
                keywords=[],
            )
        )

    def _get_func_name(self, func: ast.expr) -> str:
        if isinstance(func, ast.Name):
            return func.id
        elif isinstance(func, ast.Attribute):
            return func.attr
        else:
            return "<lambda_or_unknown>"

    def _get_func_full_name(self, func: ast.expr) -> str:
        if isinstance(func, ast.Name):
            return func.id
        elif isinstance(func, ast.Attribute):
            value_name = self._get_func_full_name(func.value)
            return f"{value_name}.{func.attr}"
        else:
            return "<lambda_or_unknown>"

    ### Variable Tracking Code

    def visit_Assign(self, node: ast.Assign) -> list[ast.stmt]:
        """Transform assignments to track variable changes."""
        self.generic_visit(node)

        statements: list[ast.stmt] = [node]

        if isinstance(node.value, ast.Call):
            expanded_nodes = self.expand_call(node.value)
            node.value = expanded_nodes[-1].value
            statements = list(expanded_nodes)
            statements[-1] = node

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
            f"{self.exec_ctx_name}.record_variable({var_name!r}, _step_tracer_utils.safe_deepcopy({var_name}), {access_path!r}, {line_no})"
        ).body[0]

    # ### Conditional Tracking Code

    def visit_If(self, node: ast.If) -> list[ast.stmt]:
        self.generic_visit(node)

        temp_test_cond = ast.Assign(
            targets=[ast.Name(id="_step_tracer_temp", ctx=ast.Store())], value=node.test
        )

        record_branch_exec = self._create_record_branch_execution_call(
            node.lineno,
            node.test,
            ast.Name(id="_step_tracer_temp", ctx=ast.Load()),
        )
        branch_end = self._create_pop_exec_call()

        new_if = ast.If(
            test=ast.Name(id="_step_tracer_temp", ctx=ast.Load()),
            body=node.body,
            orelse=node.orelse,
        )

        return [temp_test_cond, record_branch_exec, new_if, branch_end]

    def _create_record_branch_execution_call(
        self, line_number: int, cond: ast.expr, temp_cond: ast.expr
    ) -> ast.stmt:
        """Create a call to track an if else branch."""
        return ast.Expr(
            ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id=self.exec_ctx_name, ctx=ast.Load()),
                    attr="record_branch_execution",
                    ctx=ast.Load(),
                ),
                args=[
                    ast.Constant(value=line_number),
                    ast.Constant(value=ast.unparse(cond)),
                    temp_cond,
                ],
                keywords=[],
            )
        )

    ### General

    def _create_pop_exec_call(self) -> ast.Expr:
        """Create a call to pop the current execution context."""
        return ast.Expr(
            value=ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id=self.exec_ctx_name, ctx=ast.Load()),
                    attr="pop_execution",
                    ctx=ast.Load(),
                ),
                args=[],
                keywords=[],
            )
        )
