from textwrap import dedent

from edcraft_engine.static_analyser.static_analyser import CodeAnalysis, StaticAnalyser


def analyse(code: str) -> CodeAnalysis:
    return StaticAnalyser().analyse(dedent(code))
