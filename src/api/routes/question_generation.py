import codecs

from fastapi import APIRouter

from src.core.form_builder.form_builder import FormBuilder
from src.core.form_builder.static_analyser import StaticAnalyser
from src.core.question_generator.distractor_generator import DistractorGenerator
from src.core.question_generator.query_generator import QueryGenerator
from src.core.question_generator.text_generator import TextGenerator
from src.core.step_tracer.step_tracer import StepTracer
from src.models.api_models import (
    AnalyseCodeRequest,
    GenerateQuestionRequest,
    GenerateQuestionResponse,
)
from src.models.form_models import FormSchema

router = APIRouter(prefix="/question-generation")


@router.post("/analyse-code", response_model=FormSchema)
async def analyse_code(request: AnalyseCodeRequest) -> FormSchema:
    code = request.code
    code = codecs.decode(code, "unicode_escape")
    """
    Analyse the provided code and generate a form schema based on the analysis.

    Args:
        code (str): The code to be analysed.

    Returns:
        FormSchema: The generated form schema.
    """
    analyser = StaticAnalyser()
    code_analysis = analyser.analyse(code)

    form_builder = FormBuilder(code_analysis)
    form_schema = form_builder.build_form_schema()

    return form_schema


@router.post("/generate-question", response_model=GenerateQuestionResponse)
async def generate_question(
    request: GenerateQuestionRequest,
) -> GenerateQuestionResponse:
    """
    Generate a question based on the provided request.

    Args:
        request (GenerateQuestionRequest):
        The request containing the code and target information.

    Returns:
        Generated question and answer.
    """
    # Execute code with step tracing to gather execution data
    request.code = codecs.decode(request.code, "unicode_escape")
    code_to_execute = f"{request.code}\n\n# Execute the function\n{request.algorithm_input.entry_function}(**{request.algorithm_input.test_data})"

    step_tracer = StepTracer()
    transformed_code = step_tracer.transform_code(code_to_execute)
    exec_ctx = step_tracer.execute_transformed_code(transformed_code)

    # Generate Question
    text_generator = TextGenerator()
    question = text_generator.generate_question(request)

    # Generate Answer
    query = QueryGenerator(exec_ctx).generate_query(request)
    query_results = query.execute()
    answer = f"{query_results}"

    # Generate Distractors and include in response if needed (e.g., for MCQ/MRQ)
    if request.question_type in ("mcq", "mrq"):
        distractor_generator = DistractorGenerator(exec_ctx, request)
        options, correct_indices = distractor_generator.create_options(
            answers=query_results
        )
        return GenerateQuestionResponse(
            question=question,
            answer=answer,
            options=options,
            correct_indices=correct_indices,
        )

    return GenerateQuestionResponse(question=question, answer=answer)
