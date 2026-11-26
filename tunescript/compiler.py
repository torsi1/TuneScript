"""Compilation: walking the checked AST and converting it into timed audio events (Event).
The time is given in beats (Fraction), so the tests have exact expected results."""
from dataclasses import dataclass
from fractions import Fraction
from typing import List, Optional

from . import ast_nodes as A
from .errors import SemanticError
from .semantic import Analysis, eval_expr

DURATIONS = {"whole": Fraction(4), "half": Fraction(2), "quarter": Fraction(1),
             "eighth": Fraction(1, 2), "sixteenth": Fraction(1, 4)}
MODIFIERS = {"dotted": Fraction(3, 2), "triplet": Fraction(2, 3)}
CHORDS = {"major": (0, 4, 7), "minor": (0, 3, 7), "dim": (0, 3, 6), "aug": (0, 4, 8),
          "maj7": (0, 4, 7, 11), "min7": (0, 3, 7, 10), "dom7": (0, 4, 7, 10)}
STEP = Fraction(1, 4)          # the step of the piano: sixteenth note
MIDI_MIN, MIDI_MAX = 21, 108   # A0 .. C8 (piano range)
MAX_SECONDS = 600
MAX_EVENTS = 200_000


def midi_name(m: int) -> str:
    return f"{A.SHARP_NAMES[m % 12]}{m // 12 - 1}"


@dataclass
class Event:
    track: str
    instrument: str
    kind: str                  # "note" | "drum"
    start: Fraction            # in beats
    dur: Fraction
    midi: Optional[int]
    drum: Optional[str]
    amp: float                 # 0..1, vel * track * main volume 

    def label(self) -> str:
        what = midi_name(self.midi) if self.kind == "note" else self.drum
        return f"{self.track}:{what}@{self.start}+{self.dur}"


@dataclass
class Score:
    tempo: float
    master_volume: float
    events: List[Event]
    total_beats: Fraction
    export: Optional[str]
    warnings: List[str]

    @property
    def total_seconds(self) -> float:
        return float(self.total_beats) * 60.0 / self.tempo

    def beats_to_seconds(self, beats) -> float:
        return float(beats) * 60.0 / self.tempo


def duration_beats(d: A.Duration) -> Fraction:
    v = DURATIONS[d.name]
    if d.modifier:
        v *= MODIFIERS[d.modifier]
    return v


class _State:
    def __init__(self):
        self.cursor = Fraction(0)
        self.transpose = 0


class Compiler:
    def __init__(self, analysis: Analysis):
        self.an = analysis
        self.events: List[Event] = []

    def run(self) -> Score:
        ends = []
        for tr in self.an.tracks:
            st = _State()
            self.track_gain = (eval_expr(tr.volume, self.an.env) if tr.volume is not None else 100.0) / 100.0
            self.track = tr
            self.run_block(tr.body, st)
            ends.append(st.cursor)
        total = max(ends + [e.start + e.dur for e in self.events]) if ends else Fraction(0)
        score_secs = float(total) * 60.0 / self.an.tempo
        if score_secs > MAX_SECONDS:
            raise SemanticError(f"the song's length is {score_secs:.0f} s, the maximum is {MAX_SECONDS} s", self.an.song.line, self.an.song.col)
        self.events.sort(key=lambda e: e.start)      # stable: the same start time events maintain their insertion order
        return Score(self.an.tempo, self.an.master_volume, self.events, total, self.an.export, self.an.warnings)

    def amp(self, vel_expr):
        vel = eval_expr(vel_expr, self.an.env) if vel_expr is not None else 100.0
        return (vel / 100.0) * self.track_gain * (self.an.master_volume / 100.0)

    def add(self, ev: Event, node):
        if len(self.events) >= MAX_EVENTS:
            raise SemanticError(f"too many audio events (maximum {MAX_EVENTS})", node.line, node.col)
        self.events.append(ev)

    def pitch(self, lit: A.NoteLit, st: _State) -> int:
        m = lit.midi + st.transpose
        if not (MIDI_MIN <= m <= MIDI_MAX):
            raise SemanticError(
                f"the note {lit.text} is out of the instrument's range ({midi_name(MIDI_MIN)}–{midi_name(MIDI_MAX)})", lit.line, lit.col)
        return m

    def run_block(self, stmts, st: _State):
        saved = st.transpose                       # the transpose's effect lasts until the end of the block
        for s in stmts:
            self.run_stmt(s, st)
        st.transpose = saved

    def run_stmt(self, s, st: _State):
        env = self.an.env
        if isinstance(s, A.NoteStmt):
            d = duration_beats(s.duration)
            self.add(Event(self.track.name, self.track.instrument, "note", st.cursor, d,
                           self.pitch(s.note, st), None, self.amp(s.velocity)), s)
            st.cursor += d
        elif isinstance(s, A.RestStmt):
            st.cursor += duration_beats(s.duration)
        elif isinstance(s, A.ChordStmt):
            d = duration_beats(s.duration)
            if isinstance(s.spec, A.NamedChord):
                root = s.spec.root
                midis = []
                for iv in CHORDS[s.spec.quality]:
                    m = root.midi + iv + st.transpose
                    if not (MIDI_MIN <= m <= MIDI_MAX):
                        raise SemanticError(f"the chord's note ({m}) is out of the instrument's range", root.line, root.col)
                    midis.append(m)
            else:
                midis = [self.pitch(n, st) for n in s.spec.notes]
            for m in midis:
                self.add(Event(self.track.name, self.track.instrument, "note", st.cursor, d, m, None, self.amp(s.velocity)), s)
            st.cursor += d
        elif isinstance(s, A.DrumsStmt):
            steps = len(s.lines[0].steps)
            for ln in s.lines:
                for i, ch in enumerate(ln.steps):
                    if ch in "xX":
                        a = self.amp(None) * (1.0 if ch == "X" else 0.7)
                        self.add(Event(self.track.name, self.track.instrument, "drum",
                                       st.cursor + i * STEP, STEP, None, ln.drum, a), s)
            st.cursor += steps * STEP
        elif isinstance(s, A.TransposeStmt):
            st.transpose = int(round(eval_expr(s.amount, env)))
        elif isinstance(s, A.PlayStmt):
            n = int(round(eval_expr(s.times, env))) if s.times is not None else 1
            body = self.an.patterns[s.name].body
            for _ in range(n):
                self.run_block(body, st)
        elif isinstance(s, A.RepeatStmt):
            for _ in range(int(round(eval_expr(s.count, env)))):
                self.run_block(s.body, st)


def compile_score(analysis: Analysis) -> Score:
    return Compiler(analysis).run()
