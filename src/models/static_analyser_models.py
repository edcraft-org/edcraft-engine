from dataclasses import dataclass, field


@dataclass
class Scope:
    parent: "Scope | None" = None
    variables: set[str] = field(default_factory=set[str])
    children: list["Scope"] = field(default_factory=list["Scope"])

    def __post_init__(self) -> None:
        if self.parent is not None:
            self.parent.children.append(self)

    @property
    def visible_variables(self) -> set[str]:
        variables = set(self.variables)
        parent = self.parent
        while parent is not None:
            variables.update(parent.variables)
            parent = parent.parent
        return variables


@dataclass
class CodeElement:
    id: int
    type: str
    lineno: int
    scope: Scope
    parent: "CodeElement | None"
    children: list["CodeElement"]

    def __post_init__(self) -> None:
        if self.parent is not None:
            self.parent.children.append(self)

    @property
    def functions(self) -> list["Function"]:
        funcs: list[Function] = []
        for child in self.children or []:
            if isinstance(child, Function):
                funcs.append(child)
            funcs.extend(child.functions)
        return funcs

    @property
    def loops(self) -> list["Loop"]:
        loops: list[Loop] = []
        for child in self.children or []:
            if isinstance(child, Loop):
                loops.append(child)
            loops.extend(child.loops)
        return loops

    @property
    def branches(self) -> list["Branch"]:
        branches: list[Branch] = []
        for child in self.children or []:
            if isinstance(child, Branch):
                branches.append(child)
            branches.extend(child.branches)
        return branches

    @property
    def variables(self) -> set[str]:
        return self.scope.variables


@dataclass
class Function(CodeElement):
    name: str
    parameters: list[str]
    is_definition: bool


@dataclass
class Loop(CodeElement):
    loop_type: str
    condition: str

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.loop_type not in {"for", "while"}:
            raise ValueError("Loop type must be either 'for' or 'while'")


@dataclass
class Branch(CodeElement):
    condition: str


@dataclass
class CodeAnalysis:
    root_scope: Scope
    root_element: CodeElement
    functions: list[Function]
    loops: list[Loop]
    branches: list[Branch]

    @property
    def variables(self) -> set[str]:
        stack = [self.root_scope]
        variables: set[str] = set()
        while stack:
            scope = stack.pop()
            variables.update(scope.variables)
            stack.extend(scope.children)
        return variables
