"""EdCraft Engine - Algorithmic Question Generation Engine."""

from importlib.metadata import version

__version__ = version("edcraft-engine")

# Core Components
from edcraft_engine.question_generator.distractor_generator.distractor_generator import (
    DistractorGenerator,
)
from edcraft_engine.question_generator.query_generator.query_generator import (
    QueryGenerator,
)
from edcraft_engine.question_generator.question_generator import QuestionGenerator
from edcraft_engine.question_generator.text_generator.text_generator import (
    TextGenerator,
)
from edcraft_engine.static_analyser.static_analyser import StaticAnalyser

__all__ = [
    "__version__",
    "StaticAnalyser",
    "DistractorGenerator",
    "QueryGenerator",
    "QuestionGenerator",
    "TextGenerator",
    # Models must use full paths
]
