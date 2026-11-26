"""The complete processing chain in one place: source -> AST -> semantics -> event list -> WAV."""
from .parser import parse
from .semantic import analyze
from .compiler import compile_score


def build_score(source: str):
    """Build a score from the source code; returns an error if the source is invalid."""
    ast = parse(source)
    analysis = analyze(ast)
    return ast, compile_score(analysis)
