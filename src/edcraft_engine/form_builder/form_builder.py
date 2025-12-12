from edcraft_engine.form_builder.models import (
    BranchElement,
    CodeInfo,
    CodeTree,
    FormElement,
    FormOption,
    FormSchema,
    FunctionElement,
    LoopElement,
)
from edcraft_engine.static_analyser.models import CodeAnalysis, CodeElement


class FormBuilder:
    def __init__(self, code_analysis: CodeAnalysis) -> None:
        self.code_analysis = code_analysis

    def build_form_schema(self) -> FormSchema:
        code_info = self._build_code_info()
        form_elements = self._build_form_elements()
        return FormSchema(code_info=code_info, form_elements=form_elements)

    def _build_code_info(self) -> CodeInfo:
        code_tree = self._build_code_tree(self.code_analysis.root_element)

        functions: list[FunctionElement] = []
        for func in self.code_analysis.functions:
            functions.append(
                FunctionElement(
                    name=func.name,
                    type="function",
                    line_number=func.lineno,
                    parameters=func.parameters,
                    is_definition=func.is_definition,
                )
            )

        loops: list[LoopElement] = []
        for loop in self.code_analysis.loops:
            loops.append(
                LoopElement(
                    type="loop",
                    line_number=loop.lineno,
                    loop_type=loop.loop_type,
                    condition=loop.condition,
                )
            )

        branches: list[BranchElement] = []
        for branch in self.code_analysis.branches:
            branches.append(
                BranchElement(
                    type="branch",
                    line_number=branch.lineno,
                    condition=branch.condition,
                )
            )

        variables: list[str] = list(self.code_analysis.variables)

        return CodeInfo(
            code_tree=code_tree,
            functions=functions,
            loops=loops,
            branches=branches,
            variables=variables,
        )

    def _build_code_tree(self, node: CodeElement) -> CodeTree:
        return CodeTree(
            id=node.id,
            type=node.type,
            variables=(
                list(node.scope.variables)
                if node != self.code_analysis.root_element
                else list(self.code_analysis.variables)
            ),
            function_indices=[func.id for func in node.functions],
            loop_indices=[loop.id for loop in node.loops],
            branch_indices=[branch.id for branch in node.branches],
            children=[self._build_code_tree(child) for child in node.children or []],
        )

    def _build_form_elements(self) -> list[FormElement]:
        elements: list[FormElement] = []

        target_selector = self._build_target_selector()
        elements.append(target_selector)

        output_type_selector = self._build_output_type_selector()
        elements.append(output_type_selector)

        question_type_selector = self._build_question_type_selector()
        elements.append(question_type_selector)

        return elements

    def _build_target_selector(self) -> FormElement:
        options: list[FormOption] = []

        function_option = FormOption(
            id="function",
            label="Function",
            value="function",
            description="Select function from the code.",
        )
        options.append(function_option)

        loop_option = FormOption(
            id="loop",
            label="Loop",
            value="loop",
            description="Select loop from the code.",
        )
        options.append(loop_option)

        branch_option = FormOption(
            id="branch",
            label="Branch",
            value="branch",
            description="Select branch from the code.",
        )
        options.append(branch_option)

        variable_option = FormOption(
            id="variable",
            label="Variable",
            value="variable",
            description="Select variable from the code.",
        )
        options.append(variable_option)

        target_element = FormElement(
            element_type="target_selector",
            label="Target Element",
            description="Select the type of code element you want to target.",
            options=options,
            is_required=False,
        )

        return target_element

    def _build_output_type_selector(self) -> FormElement:
        options: list[FormOption] = []

        list_option = FormOption(
            id="list",
            label="List",
            value="list",
            description="Return a list of all matching elements.",
        )
        options.append(list_option)

        count_option = FormOption(
            id="count",
            label="Count",
            value="count",
            description="Return the count of matching elements.",
        )
        options.append(count_option)

        first_option = FormOption(
            id="first",
            label="First",
            value="first",
            description="Return the first matching element.",
        )
        options.append(first_option)

        last_option = FormOption(
            id="last",
            label="Last",
            value="last",
            description="Return the last matching element.",
        )
        options.append(last_option)

        output_type_element = FormElement(
            element_type="output_type_selector",
            label="Output Type",
            description="Select the type of output you want.",
            options=options,
            is_required=True,
        )

        return output_type_element

    def _build_question_type_selector(self) -> FormElement:
        options: list[FormOption] = []

        mcq_option = FormOption(
            id="mcq",
            label="Multiple Choice Question",
            value="mcq",
            description="Select this for multiple choice questions.",
        )
        options.append(mcq_option)

        mrq_option = FormOption(
            id="mrq",
            label="Multiple Response Question",
            value="mrq",
            description="Select this for multiple response questions.",
        )
        options.append(mrq_option)

        short_answer_option = FormOption(
            id="short_answer",
            label="Short Answer",
            value="short_answer",
            description="Select this for short answer questions.",
        )
        options.append(short_answer_option)

        question_type_element = FormElement(
            element_type="question_type_selector",
            label="Question Type",
            description="Select the type of question you want to create.",
            options=options,
            is_required=True,
        )
        return question_type_element
