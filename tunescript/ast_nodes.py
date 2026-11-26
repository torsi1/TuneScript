"""Abstract syntax tree (AST) nodes. Every node stores the source line and column."""
from dataclasses import dataclass, field, fields, is_dataclass
from typing import List, Optional, Union

PITCH_CLASS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
SHARP_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


@dataclass
class Node:
    line: int = field(default=0, kw_only=True)
    col: int = field(default=0, kw_only=True)


# expressions
@dataclass
class Num(Node):
    value: float


@dataclass
class Var(Node):
    name: str


@dataclass
class BinOp(Node):
    op: str            # + - * /
    left: "Expr"
    right: "Expr"


@dataclass
class Neg(Node):
    operand: "Expr"


Expr = Union[Num, Var, BinOp, Neg]


# notes, duration
@dataclass
class NoteLit(Node):
    text: str          # e.g., C#4

    @property
    def midi(self) -> int:
        pc = PITCH_CLASS[self.text[0]]
        octave = int(self.text[-1])
        mod = self.text[1] if len(self.text) == 3 else ""
        pc += 1 if mod == "#" else -1 if mod == "b" else 0
        return 12 * (octave + 1) + pc


@dataclass
class Duration(Node):
    name: str                      # whole/half/quarter/eighth/sixteenth
    modifier: Optional[str] = None  # dotted / triplet


@dataclass
class NamedChord(Node):
    root: NoteLit
    quality: str


@dataclass
class ChordNotes(Node):
    notes: List[NoteLit]


# statements (in blocks)
@dataclass
class NoteStmt(Node):
    note: NoteLit
    duration: Duration
    velocity: Optional[Expr] = None


@dataclass
class RestStmt(Node):
    duration: Duration


@dataclass
class ChordStmt(Node):
    spec: Union[NamedChord, ChordNotes]
    duration: Duration
    velocity: Optional[Expr] = None


@dataclass
class DrumLine(Node):
    drum: str
    steps: str


@dataclass
class DrumsStmt(Node):
    lines: List[DrumLine]


@dataclass
class PlayStmt(Node):
    name: str
    times: Optional[Expr] = None


@dataclass
class RepeatStmt(Node):
    count: Expr
    body: List["Stmt"]


@dataclass
class TransposeStmt(Node):
    amount: Expr


Stmt = Union[NoteStmt, RestStmt, ChordStmt, DrumsStmt, PlayStmt, RepeatStmt, TransposeStmt]


# top-level elements
@dataclass
class Tempo(Node):
    value: Expr


@dataclass
class MasterVolume(Node):
    value: Expr


@dataclass
class Let(Node):
    name: str
    value: Expr


@dataclass
class PatternDef(Node):
    name: str
    body: List[Stmt]


@dataclass
class TrackDef(Node):
    name: str
    instrument: str
    volume: Optional[Expr]
    body: List[Stmt]


@dataclass
class Export(Node):
    path: str


@dataclass
class Song(Node):
    title: str
    items: list


def children(node):
    """Return the children of an AST node (for generic traversal: printing, Graphviz)."""
    for f in fields(node):
        if f.name in ("line", "col"):
            continue
        v = getattr(node, f.name)
        if isinstance(v, list):
            for x in v:
                if is_dataclass(x):
                    yield f.name, x
        elif is_dataclass(v):
            yield f.name, v
