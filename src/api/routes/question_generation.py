import codecs

from fastapi import APIRouter

from src.core.form_builder.form_builder import FormBuilder
from src.core.form_builder.static_analyser import StaticAnalyser
from src.models.form_models import FormSchema
from src.models.api_models import GenerateQuestionRequest, GenerateQuestionResponse
from src.core.step_tracer.step_tracer import StepTracer

router = APIRouter(prefix="/question-generation")


@router.post("/analyse-code", response_model=FormSchema)
async def analyse_code(code: str) -> FormSchema:
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
    step_tracer = StepTracer()
    transformed_code = step_tracer.transform_code(request.code)
    step_tracer.execute_transformed_code(transformed_code)

    # Generate Question
    question = "<Question Text Generation: Work in Progress>"

    # Generate Answer
    answer = "<Answer Generation: Work in Progress>"

    return GenerateQuestionResponse(question=question, answer=answer)
