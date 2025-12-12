"""EdCraft Engine - Algorithmic Question Generation Engine."""

from importlib.metadata import version

__version__ = version("edcraft-engine")

# Core Components
from edcraft_engine.form_builder.form_builder import FormBuilder
from edcraft_engine.form_builder.static_analyser import StaticAnalyser
from edcraft_engine.query_engine.query_engine import QueryEngine
from edcraft_engine.question_generator.distractor_generator import DistractorGenerator
from edcraft_engine.question_generator.query_generator import QueryGenerator
from edcraft_engine.question_generator.text_generator import TextGenerator
from edcraft_engine.step_tracer.step_tracer import StepTracer

__all__ = [
    "__version__",
    "FormBuilder",
    "StaticAnalyser",
    "DistractorGenerator",
    "QueryGenerator",
    "TextGenerator",
    "QueryEngine",
    "StepTracer",
    # Models must use full paths
]
