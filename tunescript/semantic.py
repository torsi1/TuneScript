"""Semantic analysis: symbol table (constants, patterns, tracks), value ranges,
drum pattern validation, detection of circular pattern references. The result is an Analysis object."""
from dataclasses import dataclass, field
from typing import Dict, List

from . import ast_nodes as A
from .errors import SemanticError

TEMPO_RANGE = (20, 300)
PERCENT_RANGE = (0, 100)
REPEAT_RANGE = (1, 1000)
TRANSPOSE_RANGE = (-48, 48)
DRUM_CHARS = set("xX.")


@dataclass
class Analysis:
    song: A.Song
    tempo: float = 120.0
    master_volume: float = 100.0
    env: Dict[str, float] = field(default_factory=dict)
    patterns: Dict[str, A.PatternDef] = field(default_factory=dict)
    tracks: List[A.TrackDef] = field(default_factory=list)
    export: str = None
    warnings: List[str] = field(default_factory=list)


def eval_expr(e, env):
    """Constant expression evaluation (in the language, all variables are constants)."""
    if isinstance(e, A.Num):
        return e.value
    if isinstance(e, A.Var):
        if e.name not in env:
            raise SemanticError(f"the variable '{e.name}' is not declared", e.line, e.col)
        return env[e.name]
    if isinstance(e, A.Neg):
        return -eval_expr(e.operand, env)
    if isinstance(e, A.BinOp):
        a, b = eval_expr(e.left, env), eval_expr(e.right, env)
        if e.op == "+":
            return a + b
        if e.op == "-":
            return a - b
        if e.op == "*":
            return a * b
        if b == 0:
            raise SemanticError("division by zero", e.line, e.col)
        return a / b
    raise AssertionError(f"unknown expression: {e!r}")


def _in_range(value, lo, hi, what, node):
    if not (lo <= value <= hi):
        raise SemanticError(f"{what} value is {value:g}, but only {lo}–{hi} is allowed", node.line, node.col)


def _integer(value, what, node):
    if abs(value - round(value)) > 1e-9:
        raise SemanticError(f"{what} must be an integer (got: {value:g})", node.line, node.col)
    return int(round(value))


class Analyzer:
    def __init__(self, song: A.Song):
        self.a = Analysis(song)
        self.edges = {}      # pattern -> [(goal, row, col)]
        self.used = set()    # used patterns (from tracks or other patterns)
        self.seen_tempo = self.seen_volume = self.seen_export = False

    # public entry point
    def run(self) -> Analysis:
        a = self.a
        # 1. run: patterns's and tracks's names gathering (forward references allowed)
        pat_nodes, track_names = {}, {}
        for it in a.song.items:
            if isinstance(it, A.PatternDef):
                if it.name in pat_nodes:
                    prev = pat_nodes[it.name]
                    raise SemanticError(f"the pattern '{it.name}' is already defined ({prev.line}. line)", it.line, it.col)
                pat_nodes[it.name] = it
            elif isinstance(it, A.TrackDef):
                if it.name in track_names:
                    prev = track_names[it.name]
                    raise SemanticError(f"the track '{it.name}' is already defined ({prev.line}. line)", it.line, it.col)
                track_names[it.name] = it
        a.patterns = pat_nodes

        # 2. run: elements in the source order
        for it in a.song.items:
            self.item(it)

        if not a.tracks:
            raise SemanticError("at least one track is required", a.song.line, a.song.col)
        self.check_cycles()
        for name, p in pat_nodes.items():
            if name not in self.used:
                a.warnings.append(f"{p.line}. line: the pattern '{name}' is not used anywhere")
        return a

    # top-level elements
    def item(self, it):
        a = self.a
        if isinstance(it, A.Tempo):
            if self.seen_tempo:
                raise SemanticError("the tempo is specified multiple times", it.line, it.col)
            self.seen_tempo = True
            v = eval_expr(it.value, a.env)
            _in_range(v, *TEMPO_RANGE, "the tempo (BPM)", it.value)
            a.tempo = v
        elif isinstance(it, A.MasterVolume):
            if self.seen_volume:
                raise SemanticError("the master volume is specified multiple times", it.line, it.col)
            self.seen_volume = True
            v = eval_expr(it.value, a.env)
            _in_range(v, *PERCENT_RANGE, "the master volume", it.value)
            a.master_volume = v
        elif isinstance(it, A.Let):
            if it.name in a.env:
                raise SemanticError(f"the variable '{it.name}' is already declared", it.line, it.col)
            a.env[it.name] = eval_expr(it.value, a.env)
        elif isinstance(it, A.Export):
            if self.seen_export:
                raise SemanticError("the export is specified multiple times", it.line, it.col)
            self.seen_export = True
            if not it.path.lower().endswith(".wav"):
                raise SemanticError("the exported file extension can only be .wav", it.line, it.col)
            a.export = it.path
        elif isinstance(it, A.PatternDef):
            self.edges[it.name] = []
            self.block(it.body, it.name)
        elif isinstance(it, A.TrackDef):
            if it.volume is not None:
                v = eval_expr(it.volume, a.env)
                _in_range(v, *PERCENT_RANGE, "the track volume", it.volume)
            if not it.body:
                a.warnings.append(f"{it.line}. line: the track '{it.name}' is empty")
            a.tracks.append(it)
            self.block(it.body, None)

    # blocks and statements
    def block(self, stmts, owner):
        for s in stmts:
            self.stmt(s, owner)

    def velocity(self, vel):
        if vel is not None:
            _in_range(eval_expr(vel, self.a.env), *PERCENT_RANGE, "the velocity (vol)", vel)

    def stmt(self, s, owner):
        env = self.a.env
        if isinstance(s, A.NoteStmt):
            self.velocity(s.velocity)
        elif isinstance(s, A.ChordStmt):
            self.velocity(s.velocity)
        elif isinstance(s, A.RestStmt):
            pass
        elif isinstance(s, A.DrumsStmt):
            self.drums(s)
        elif isinstance(s, A.TransposeStmt):
            v = _integer(eval_expr(s.amount, env), "the transpose", s.amount)
            _in_range(v, *TRANSPOSE_RANGE, "the transpose", s.amount)
        elif isinstance(s, A.PlayStmt):
            if s.name not in self.a.patterns:
                raise SemanticError(f"the pattern '{s.name}' is not defined", s.line, s.col)
            if s.times is not None:
                n = _integer(eval_expr(s.times, env), "the repeat count (times)", s.times)
                _in_range(n, *REPEAT_RANGE, "the repeat count (times)", s.times)
            self.used.add(s.name)
            if owner is not None:
                self.edges[owner].append((s.name, s.line, s.col))
        elif isinstance(s, A.RepeatStmt):
            n = _integer(eval_expr(s.count, env), "the repeat count (repeat)", s.count)
            _in_range(n, *REPEAT_RANGE, "the repeat count (repeat)", s.count)
            self.block(s.body, owner)

    def drums(self, s):
        length = None
        for ln in s.lines:
            bad = sorted(set(ln.steps) - DRUM_CHARS)
            if bad:
                raise SemanticError(f"invalid character in the drum pattern: {bad[0]!r} (only x, X and . are allowed)", ln.line, ln.col)
            if not ln.steps:
                raise SemanticError("empty drum pattern", ln.line, ln.col)
            if length is None:
                length = len(ln.steps)
            elif len(ln.steps) != length:
                raise SemanticError(
                    f"the lengths of the drum patterns differ: {len(ln.steps)} steps, the first line has {length} steps", ln.line, ln.col)

    # circular reference checking
    def check_cycles(self):
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {n: WHITE for n in self.edges}
        stack = []

        def dfs(n):
            color[n] = GRAY
            stack.append(n)
            for target, line, col in self.edges[n]:
                if color[target] == GRAY:
                    cyc = stack[stack.index(target):] + [target]
                    raise SemanticError("circular pattern reference: " + " → ".join(cyc), line, col)
                if color[target] == WHITE:
                    dfs(target)
            stack.pop()
            color[n] = BLACK

        for n in list(self.edges):
            if color[n] == WHITE:
                dfs(n)


def analyze(song: A.Song) -> Analysis:
    return Analyzer(song).run()
