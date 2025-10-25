import ast

from src.models.static_analyser_models import (
    Branch,
    CodeAnalysis,
    CodeElement,
    Function,
    Loop,
    Scope,
)


class StaticAnalyser(ast.NodeVisitor):
    """Extracts static information from Python source code."""

    def __init__(self) -> None:
        self.root_scope = Scope()
        self.root_element = CodeElement(
            id=0,
            type="module",
            lineno=0,
            scope=self.root_scope,
            parent=None,
            children=[],
        )

        self.current_scope = self.root_scope
        self.current_element = self.root_element

        self.functions: list[Function] = []
        self.loops: list[Loop] = []
        self.branches: list[Branch] = []

    def analyse(self, source_code: str) -> CodeAnalysis:
        """Analyse the given source code and return the code analysis."""
        try:
            tree = ast.parse(source_code)
            self.visit(tree)
        except SyntaxError as e:
            raise ValueError("Invalid Python source code") from e

        return CodeAnalysis(
            root_scope=self.root_scope,
            root_element=self.root_element,
            functions=self.functions,
            loops=self.loops,
            branches=self.branches,
        )

    def _enter_scope(self) -> None:
        new_scope = Scope(parent=self.current_scope)
        self.current_scope = new_scope

    def _leave_scope(self) -> None:
        if self.current_scope.parent is not None:
            self.current_scope = self.current_scope.parent

    def _enter_code_block(self, new_element: CodeElement) -> None:
        self.current_element = new_element

    def _leave_code_block(self) -> None:
        if self.current_element.parent is not None:
            self.current_element = self.current_element.parent

    def _record_function(
        self, func_name: str, lineno: int, is_definition: bool
    ) -> Function:
        func = Function(
            id=len(self.functions),
            type="function",
            lineno=lineno,
            scope=self.current_scope,
            parent=self.current_element,
            children=[],
            name=func_name,
            parameters=[],
            is_definition=is_definition,
        )
        self.functions.append(func)
        return func

    def _record_loop(self, loop_type: str, lineno: int) -> Loop:
        loop = Loop(
            id=len(self.loops),
            type="loop",
            lineno=lineno,
            scope=self.current_scope,
            parent=self.current_element,
            children=[],
            loop_type=loop_type,
        )
        self.loops.append(loop)
        return loop

    def _record_branch(self, condition: str, lineno: int) -> Branch:
        branch = Branch(
            id=len(self.branches),
            type="branch",
            lineno=lineno,
            scope=self.current_scope,
            parent=self.current_element,
            children=[],
            condition=condition,
        )
        self.branches.append(branch)
        return branch

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._enter_scope()
        self.generic_visit(node)
        self._leave_scope()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._enter_scope()

        # Add function parameters to the current scope
        parameters = [arg.arg for arg in node.args.args]
        for arg in parameters:
            self.current_scope.variables.add(arg)

        # Record function information
        func = self._record_function(
            func_name=node.name, lineno=node.lineno, is_definition=True
        )
        self._enter_code_block(func)

        self.generic_visit(node)
        self._leave_code_block()
        self._leave_scope()

    def visit_Call(self, node: ast.Call) -> None:
        """Track function calls and add to current container."""
        func_name = self._get_func_name(node.func)

        # Record function information
        self._record_function(
            func_name=func_name,
            lineno=node.lineno,
            is_definition=False,
        )
        self.generic_visit(node)

    def _get_func_name(self, node: ast.expr) -> str:
        """Extract function name from call node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        return "<unknown>"

    def visit_For(self, node: ast.For) -> None:
        loop = self._record_loop("for", node.lineno)
        self._enter_code_block(loop)

        # Record variables assigned in the for loop target
        variables = self._extract_names(node.target)
        for var in variables:
            self.current_scope.variables.add(var)

        self.generic_visit(node)
        self._leave_code_block()

    def visit_While(self, node: ast.While) -> None:
        loop = self._record_loop("while", node.lineno)
        self._enter_code_block(loop)

        self.generic_visit(node)
        self._leave_code_block()

    def visit_If(self, node: ast.If) -> None:
        branch = self._record_branch(ast.unparse(node.test), node.lineno)
        self._enter_code_block(branch)

        self.generic_visit(node)
        self._leave_code_block()

    def visit_Assign(self, node: ast.Assign) -> None:
        # Record assigned variable names in the current scope
        for target in node.targets:
            names = self._extract_names(target)
            for name in names:
                self.current_scope.variables.add(name)
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        # Record assigned variable name in the current scope
        names = self._extract_names(node.target)
        for name in names:
            self.current_scope.variables.add(name)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        # Record assigned variable name in the current scope
        names = self._extract_names(node.target)
        for name in names:
            self.current_scope.variables.add(name)
        self.generic_visit(node)

    def _extract_names(self, node: ast.expr) -> list[str]:
        """Extract variable names from assignment target."""
        names: list[str] = []
        if isinstance(node, ast.Name):
            names.append(node.id)
        elif isinstance(node, ast.Tuple | ast.List):
            for elt in node.elts:
                names.extend(self._extract_names(elt))
        elif isinstance(node, ast.Starred):
            names.extend(self._extract_names(node.value))
        elif isinstance(node, ast.Attribute):
            # For attribute assignments like obj.attr, track the base object
            base = self._get_base_name(node)
            if base:
                names.append(base)
        elif isinstance(node, ast.Subscript):
            # For subscript assignments like arr[i], track the array
            base = self._get_base_name(node)
            if base:
                names.append(base)
        return names

    def _get_base_name(self, node: ast.expr) -> str | None:
        """Get the base variable name from attribute/subscript access."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return self._get_base_name(node.value)
        elif isinstance(node, ast.Subscript):
            return self._get_base_name(node.value)
        return None
