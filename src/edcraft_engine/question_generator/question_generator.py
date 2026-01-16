import random
from typing import Any

from edcraft_engine.question_generator.distractor_generator.distractor_generator import (
    DistractorGenerator,
)
from edcraft_engine.question_generator.models import (
    ExecutionSpec,
    GenerationOptions,
    Question,
    QuestionSpec,
)
from edcraft_engine.question_generator.query_generator.query_generator import (
    QueryGenerator,
)
from edcraft_engine.question_generator.text_generator.text_generator import (
    TextGenerator,
)
from edcraft_engine.step_tracer.step_tracer import StepTracer


class QuestionGenerator:
    def __init__(self) -> None:
        self.step_tracer = StepTracer()
        self.text_generator = TextGenerator()
        self.distractor_generator = DistractorGenerator()

    def generate_question(
        self,
        code: str,
        question_spec: QuestionSpec,
        execution_spec: ExecutionSpec,
        generation_options: GenerationOptions,
    ) -> Question:
        """Generates a question based on the provided parameters."""
        # Generate question text
        text = self.text_generator.generate_question(question_spec, execution_spec.input_data)

        # Generate execution context
        code_with_input = self._inject_input_data(code, execution_spec)
        transformed_code = self.step_tracer.transform_code(code_with_input)
        exec_ctx = self.step_tracer.execute_transformed_code(transformed_code)

        # Generate Answer
        query = QueryGenerator(exec_ctx).generate_query(question_spec.target, question_spec.output_type)
        query_results = query.execute()
        answer = f"{query_results}"

        # Generate Distractors
        options = None
        correct_indices = None

        if question_spec.question_type in ("mcq", "mrq"):
            correct_options = (
                query_results if question_spec.question_type == "mrq" else [query_results]
            )

            distractors = self.distractor_generator.generate_distractors(
                correct_options,
                exec_ctx,
                question_spec,
                generation_options.num_distractors,
            )
            options, correct_indices = self._shuffle_options(
                correct_options + distractors, len(correct_options)
            )

        return Question(
            text=text,
            answer=answer,
            options=options,
            correct_indices=correct_indices,
            question_type=question_spec.question_type,
        )

    def generate_template_preview(
        self,
        question_spec: QuestionSpec,
        generation_options: GenerationOptions,
    ) -> Question:
        """Generate a template preview without executing code.

        Args:
            question_spec: Specification of what to ask
            generation_options: Generation parameters

        Returns:
            Question object with template text and placeholders
        """
        # Generate template question text (without input data)
        text = self.text_generator.generate_question(
            question_spec,
            input_data=None,
        )

        # Provide placeholder values
        answer = "<placeholder_answer>"
        options = None
        correct_indices = None

        if question_spec.question_type in ("mcq", "mrq"):
            num_options = generation_options.num_distractors + 1
            options = [f"<option_{i+1}>" for i in range(num_options)]
            correct_indices = [0]

        return Question(
            text=text,
            answer=answer,
            options=options,
            correct_indices=correct_indices,
            question_type=question_spec.question_type,
        )

    def _inject_input_data(
        self, code: str, execution_spec: ExecutionSpec
    ) -> str:
        """Injects input data into the code for tracing."""
        return f"{code}\n\n# Execute the function\n{execution_spec.entry_function}(**{execution_spec.input_data})"
    def _shuffle_options(
        self, options: list[Any], num_correct: int
    ) -> tuple[list[Any], list[int]]:
        """
        Shuffle options while tracking where correct answers end up.

        Args:
            options: List where first num_correct items are correct answers
            num_correct: Number of correct answers at the start of the list

        Returns:
            Tuple of (shuffled_options, correct_indices)
        """
        indexed_options = [(i, option) for i, option in enumerate(options)]

        random.shuffle(indexed_options)

        shuffled_options = [option for _, option in indexed_options]
        correct_indices = [
            new_idx
            for new_idx, (old_idx, _) in enumerate(indexed_options)
            if old_idx < num_correct
        ]

        return shuffled_options, correct_indices
