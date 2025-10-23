import ast

from src.core.static_analyser.models import (
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
            lineno=0, scope=self.root_scope, parent=None, children=[]
        )

        self.current_scope = self.root_scope
        self.current_element = self.root_element

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
        function_element = Function(
            lineno=node.lineno,
            scope=self.current_scope,
            parent=self.current_element,
            children=[],
            name=node.name,
            parameters=parameters,
            is_definition=True,
        )
        self._enter_code_block(function_element)

        self.generic_visit(node)
        self._leave_code_block()
        self._leave_scope()

    def visit_Call(self, node: ast.Call) -> None:
        """Track function calls and add to current container."""
        func_name = self._get_func_name(node.func)

        # Record function information
        Function(
            lineno=node.lineno,
            scope=self.current_scope,
            parent=self.current_element,
            children=[],
            name=func_name,
            parameters=[],
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
        loop_element = Loop(
            lineno=node.lineno,
            scope=self.current_scope,
            parent=self.current_element,
            children=[],
            type="for",
        )
        self._enter_code_block(loop_element)

        # Record variables assigned in the for loop target
        variables = self._extract_names(node.target)
        for var in variables:
            self.current_scope.variables.add(var)

        self.generic_visit(node)
        self._leave_code_block()

    def visit_While(self, node: ast.While) -> None:
        loop_element = Loop(
            lineno=node.lineno,
            scope=self.current_scope,
            parent=self.current_element,
            children=[],
            type="while",
        )
        self._enter_code_block(loop_element)

        self.generic_visit(node)
        self._leave_code_block()

    def visit_If(self, node: ast.If) -> None:
        branch_element = Branch(
            lineno=node.lineno,
            scope=self.current_scope,
            parent=self.current_element,
            children=[],
            condition=ast.unparse(node.test),
        )
        self._enter_code_block(branch_element)

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
