import codecs

from fastapi import APIRouter

from src.core.form_builder.form_builder import FormBuilder
from src.core.form_builder.models import FormSchema
from src.core.static_analyser.static_analyser import StaticAnalyser

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
