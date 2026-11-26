"""Lexical + syntactic analysis (Lark, LALR(1), basic lexer) and the parse tree -> AST conversion."""
import os
from lark import Lark, Token, Tree
from lark.exceptions import UnexpectedCharacters, UnexpectedToken, UnexpectedEOF

from . import ast_nodes as A
from .errors import LexicalError, SyntaxErr

_GRAMMAR_PATH = os.path.join(os.path.dirname(__file__), "grammar.lark")

_PARSER = Lark.open(_GRAMMAR_PATH, parser="lalr", lexer="basic", propagate_positions=True)

# Lark's internal token names -> readable names for error messages
FRIENDLY = {
    "SEMICOLON": "';'", "LBRACE": "'{'", "RBRACE": "'}'", "LPAR": "'('", "RPAR": "')'",
    "LSQB": "'['", "RSQB": "']'", "COMMA": "','", "EQUAL": "'='", "PLUS": "'+'", "MINUS": "'-'",
    "STAR": "'*'", "SLASH": "'/'", "$END": "file end",
    "NOTE": "note name (e.g., C4, F#3, Bb2)", "NAME": "identifier", "NUMBER": "number",
    "STRING": "string (\"...\")", "INSTRUMENT": "instrument (sine/square/saw/triangle/pluck)",
    "DRUM": "drum sound (kick/snare/hat/clap)", "QUALITY": "chord type (major/minor/dim/aug/maj7/min7/dom7)",
    "DURATION": "duration (whole/half/quarter/eighth/sixteenth)", "MODIFIER": "modifier (dotted/triplet)",
}


def _friendly(name: str) -> str:
    return FRIENDLY.get(name, f"'{name.lower()}'")


# lexical precheck
def lexical_precheck(text: str) -> None:
    """Search for unterminated strings and unterminated block comments, with precise positions.
    (Lark would only give a general error for these.)"""
    i, line, col, n = 0, 1, 1, len(text)

    def adv(k=1):
        nonlocal i, line, col
        for _ in range(k):
            if i < n and text[i] == "\n":
                line, col = line + 1, 1
            else:
                col += 1
            i += 1

    while i < n:
        c = text[i]
        if c == '"':
            sl, sc = line, col
            adv()
            while i < n and text[i] not in '"\n':
                adv()
            if i >= n or text[i] == "\n":
                raise LexicalError("unterminated string: missing closing quote", sl, sc)
            adv()
        elif text.startswith("//", i):
            while i < n and text[i] != "\n":
                adv()
        elif text.startswith("/*", i):
            sl, sc = line, col
            end = text.find("*/", i + 2)
            if end == -1:
                raise LexicalError("unterminated comment: missing closing '*/'", sl, sc)
            adv(end + 2 - i)
        else:
            adv()


# parse tree -> AST
def _pos(x):
    if isinstance(x, Token):
        return {"line": x.line, "col": x.column}
    m = x.meta
    return {"line": getattr(m, "line", 0), "col": getattr(m, "column", 0)}


class Builder:
    def build(self, x):
        return getattr(self, x.data)(x)

    # --- top level
    def start(self, t):
        return self.build(t.children[0])

    def song(self, t):
        title = t.children[0].value[1:-1]
        return A.Song(title, [self.build(c) for c in t.children[1:]], **_pos(t))

    def tempo_stmt(self, t):
        return A.Tempo(self.build(t.children[0]), **_pos(t))

    def volume_stmt(self, t):
        return A.MasterVolume(self.build(t.children[0]), **_pos(t))

    def let_stmt(self, t):
        name = t.children[0]
        return A.Let(name.value, self.build(t.children[1]), **_pos(name))

    def pattern_def(self, t):
        name = t.children[0]
        return A.PatternDef(name.value, self.block(t.children[1]), **_pos(name))

    def track_def(self, t):
        name, instr = t.children[0], t.children[1]
        vol, body = None, None
        for c in t.children[2:]:
            if c.data == "track_vol":
                vol = self.build(c.children[0])
            else:
                body = self.block(c)
        return A.TrackDef(name.value, instr.value, vol, body, **_pos(name))

    def export_stmt(self, t):
        return A.Export(t.children[0].value[1:-1], **_pos(t))

    def block(self, t):
        return [self.build(c) for c in t.children]

    # --- statements
    def note_stmt(self, t):
        note = self._note(t.children[0])
        dur = self.duration(t.children[1])
        vel = self.build(t.children[2].children[0]) if len(t.children) > 2 else None
        return A.NoteStmt(note, dur, vel, **_pos(t))

    def rest_stmt(self, t):
        return A.RestStmt(self.duration(t.children[0]), **_pos(t))

    def chord_stmt(self, t):
        spec = self.build(t.children[0])
        dur = self.duration(t.children[1])
        vel = self.build(t.children[2].children[0]) if len(t.children) > 2 else None
        return A.ChordStmt(spec, dur, vel, **_pos(t))

    def named_chord(self, t):
        return A.NamedChord(self._note(t.children[0]), t.children[1].value, **_pos(t))

    def chord_notes(self, t):
        return A.ChordNotes([self._note(c) for c in t.children], **_pos(t))

    def duration(self, t):
        mod = t.children[1].value if len(t.children) > 1 else None
        return A.Duration(t.children[0].value, mod, **_pos(t))

    def drums_stmt(self, t):
        return A.DrumsStmt([self.drum_line(c) for c in t.children], **_pos(t))

    def drum_line(self, t):
        return A.DrumLine(t.children[0].value, t.children[1].value[1:-1], **_pos(t))

    def play_stmt(self, t):
        name = t.children[0]
        times = self.build(t.children[1]) if len(t.children) > 1 else None
        return A.PlayStmt(name.value, times, **_pos(t))

    def repeat_stmt(self, t):
        return A.RepeatStmt(self.build(t.children[0]), self.block(t.children[1]), **_pos(t))

    def transpose_stmt(self, t):
        return A.TransposeStmt(self.build(t.children[0]), **_pos(t))

    # expressions
    def number(self, t):
        return A.Num(float(t.children[0].value), **_pos(t))

    def var(self, t):
        return A.Var(t.children[0].value, **_pos(t))

    def add(self, t):
        return A.BinOp("+", self.build(t.children[0]), self.build(t.children[1]), **_pos(t))

    def sub(self, t):
        return A.BinOp("-", self.build(t.children[0]), self.build(t.children[1]), **_pos(t))

    def mul(self, t):
        return A.BinOp("*", self.build(t.children[0]), self.build(t.children[1]), **_pos(t))

    def div(self, t):
        return A.BinOp("/", self.build(t.children[0]), self.build(t.children[1]), **_pos(t))

    def neg(self, t):
        return A.Neg(self.build(t.children[0]), **_pos(t))

    @staticmethod
    def _note(tok):
        return A.NoteLit(tok.value, **_pos(tok))


# public entry point
def _end_position(text):
    lines = text.split("\n")
    return len(lines), len(lines[-1]) + 1


def parse(text: str) -> A.Song:
    lexical_precheck(text)
    try:
        tree = _PARSER.parse(text)
    except UnexpectedCharacters as e:
        ch = text[e.pos_in_stream]
        hint = ""
        if ch.isupper():
            hint = " (note: A–G letters, optional #/b, then octave number)"
        raise LexicalError(f"unknown character {ch!r}{hint}", e.line, e.column)
    except UnexpectedToken as e:
        tok = e.token
        expected = sorted({_friendly(a) for a in (e.accepts or e.expected)})
        exp = ", ".join(expected[:7]) + (" …" if len(expected) > 7 else "")
        if tok.type == "$END":
            line, col = _end_position(text)
            raise SyntaxErr(f"unexpected file end; expected: {exp}", line, col)
        raise SyntaxErr(f"unexpected {tok.value!r}; expected: {exp}", tok.line, tok.column)
    except UnexpectedEOF:
        line, col = _end_position(text)
        raise SyntaxErr("unexpected file end", line, col)
    return Builder().build(tree)
