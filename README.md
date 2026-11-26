# TuneScript – a mini-language for describing music backing tracks

A custom-designed language for describing melodies, chord progressions, basslines, and drum patterns.
The compiler generates a **WAV audio file** from the source (mono, 16-bit, 44100 Hz).

```
source (.tune) ──► lexical+syntactic analysis (Lark, LALR) ──► AST
               ──► semantic analysis (symbol table, ranges, cycle check)
               ──► expansion into timed event list (Fraction-exact beat times)
               ──► synthesis + mixing (numpy) ──► WAV
```

## Running

```
pip install -r requirements.txt          # lark, numpy  (Python 3.10+)
python -m tunescript examples/demo.tune                       # -> demo_pop.wav (based on the export line)
python -m tunescript examples/demo.tune -o out.wav --play      # with playback
python -m tunescript examples/mini.tune --ast --events --roll --check   # analysis and display only
python -m tunescript examples/demo.tune --dot ast.dot         # AST for Graphviz:  dot -Tpng ast.dot -o ast.png
python tests/run_tests.py                                     # tests + tests/report.md
```

## 1. The Language

**Goal:** fast, text-based description of music backing tracks. **Use cases:** backing track for practice, sketch for game or
video background music, making music theory examples audible.

### Full Example
```
// Pop backing track: C – G – Am – F chord progression, 8 bars, 110 BPM
song "Pop backing track" {
  tempo 110;
  volume 90;
  let chord_volume = 55;
  let cycles = 2;             /* the 4-bar progression plays twice */

  pattern chords {
    chord C4 major whole;     // C major
    chord G3 major whole;     // G major
    chord A3 minor whole;     // A minor
    chord F3 major whole;     // F major
  }

  pattern bassline {
    C2 quarter; C2 eighth; C2 eighth; C2 quarter; G2 quarter;
    G2 quarter; G2 eighth; G2 eighth; G2 quarter; D3 quarter;
    A2 quarter; A2 eighth; A2 eighth; A2 quarter; E2 quarter;
    F2 quarter; F2 eighth; F2 eighth; F2 quarter; C3 quarter;
  }

  pattern melody {
    E5 quarter; G5 quarter; E5 half;
    D5 quarter; G4 quarter; B4 half;
    C5 quarter; E5 quarter; A4 half;
    C5 quarter; A4 quarter; F4 half;
  }

  pattern groove {
    drums {
      kick  "x.......x.x.....";
      snare "....X.......X...";
      hat   "x.x.x.x.x.x.x.x.";
    }
  }

  track pad   with triangle volume chord_volume { repeat cycles { play chords; } }
  track bass  with pluck    volume 100          { play bassline times cycles; }
  track lead  with square   volume 40           { play melody times cycles; }
  track beats with sine                         { repeat 4 * cycles { play groove; } }

  export "examples/demo_pop.wav";
}
```
Tracks start **simultaneously**, and the statements inside them play **sequentially**.

### Statements
| Statement | Meaning |
|---|---|
| `tempo E;` `volume E;` `let n = E;` `export "f.wav";` | settings, constant, output |
| `pattern name { ... }` | reusable section (a pattern can also call another pattern) |
| `track name with INSTRUMENT [volume E] { ... }` | one voice; instrument: `sine square saw triangle pluck` |
| `C4 quarter [dotted/triplet] [vol E];` | note (A–G, `#`/`b`, octave 0–9) |
| `rest eighth;` | rest |
| `chord C4 major half;` / `chord [C4, E4, G4] half;` | chord by name (`major minor dim aug maj7 min7 dom7`) or by note list |
| `drums { kick "x..."; snare "..X."; ... }` | drum grid; drums: `kick snare hat clap`; lines have equal length |
| `play name [times E];` | play a pattern |
| `repeat E { ... }` | repetition (nestable) |
| `transpose E;` | shift in semitones, active until the end of the block |

Durations: `whole`=4, `half`=2, `quarter`=1, `eighth`=½, `sixteenth`=¼ beats; `dotted` ×3/2, `triplet` ×2/3.
Expressions: `+ - * /`, unary `-`, parentheses, constants.

### Required Constructs in the Grammar
| Requirement | Where |
|---|---|
| Sequence | `song: "song" STRING "{" item* "}"`, `note_stmt: NOTE duration velocity? ";"`, statements in a block sequentially |
| Choice | `item`, `statement`, `chord_spec` (by name / by list), `atom`, `DURATION` |
| Repetition | `item*`, `statement*`, `drum_line+`, chord list, `repeat`, `play ... times` |
| Optional | `track_vol?`, `velocity?`, `MODIFIER?`, `("times" expr)?` |
| Compound | `repeat` inside `repeat`, pattern inside pattern, expression inside expression, `drums` block |

`grammar.lark` contains **~35 rules**.

## 2. The Parser

- **Tool:** Lark (Python). **Method:** LALR(1), bottom-up parsing; **basic lexer**, so keywords are reserved everywhere.
- **Tokens:** `NOTE` `/[A-G][#b]?[0-9]/`, `NAME` `/[a-z_][a-z0-9_]*/`, `NUMBER`, `STRING`, and the keyword groups
  (`INSTRUMENT DRUM QUALITY DURATION MODIFIER`, with `\b` and higher priority so `sinewave` does not become `sine`+`wave`).
- **Special symbols:** `{ } ( ) [ ] ; , = + - * /`.
- **Whitespace, comments:** `%ignore WS`, `%ignore COMMENT`; comments: `// ...` and `/* ... */`.
- **Precedence:** layered by the grammar (`expr` < `term` < `factor` < `atom`), no separate precedence table.
- **Error handling:** `parser.py`
  - `lexical_precheck`: unterminated string and unterminated `/* */` with exact starting position;
  - `UnexpectedCharacters` → **Lexical error** (e.g., `@`, `$`, `H4`);
  - `UnexpectedToken` / EOF → **Syntactic error**, with a list of expected tokens;
  - `Semantic error`: produced by `semantic.py` and `compiler.py`; each has the format `[category] line:column – message`, accompanied by the erroneous line and a `^` indicator.
  - Stops at the first error.

## 3. AST

The Lark parse tree is converted by the `Builder` class into a dataclass-based AST (`ast_nodes.py`), with every node storing line/column values.
Node types: `Song, Tempo, MasterVolume, Let, PatternDef, TrackDef, Export, NoteStmt, RestStmt, ChordStmt, NamedChord, ChordNotes, DrumsStmt, DrumLine, PlayStmt, RepeatStmt, TransposeStmt, Duration, NoteLit, Num, Var, BinOp, Neg`.

**Usage:**
1. `Analyzer` (semantic.py): traverses the tree, builds the symbol table, evaluates expressions, checks constraints.
2. `Compiler` (compiler.py): traverses the tree again; `PlayStmt` substitutes the pattern body, `RepeatStmt` repeats its body, `NoteStmt`/`ChordStmt`/`DrumsStmt` create an event at the current timestamp, `TransposeStmt` modifies the playback state.
3. `--ast` shows the tree in text form, `--dot` in Graphviz form (`visualize.py` with generic traversal).

## 4. Semantic Checks
1. undeclared variable, variable redeclaration; constant expressions are evaluated at compile time (division by zero → error);
2. ranges: tempo 20–300, volumes 0–100, repeat count 1–1000 integer, transpose −48…48 integer;
3. pattern/track names are unique; `play` only references an existing pattern; **circular pattern reference** detection (DFS, printing the cycle);
4. in a drum grid only `x X .`, and lines within a single block have equal length;
5. note within piano range (A0–C8) **even after transposition**; at least one track; export only `.wav`; tempo/master volume/export at most once;
6. resource limits: at most 600 seconds long song and 200,000 events;
7. warning: unused pattern, empty track.

## 5. Processing and Sound
- **Time:** in beats, using `fractions.Fraction` (triplet is ⅓, ⅔ exact), converted to seconds only right before synthesis: `s = beat · 60 / BPM`.
- **Pitch:** `f = 440 · 2^((midi−69)/12)`, `C4 = 60`.
- **Instruments:** `sine`, `square`, `saw`, `triangle`, `pluck` (sawtooth + harmonic, fast decay); 10 ms attack and ≤60 ms release against clicking.
- **Drums** (no sample files, all synthesized): kick (pitch-dropping sine), snare (noise + 190 Hz), hat (high-pass filtered noise), clap (3 noise bursts); noise uses a fixed seed → **identical input produces byte-for-byte identical WAV**.
- **Mixing:** waves are summed; if peak > 0.98, a simple limiter scales it back.
- At the end of the song, 0.3 s of silence remains for drum decay.

## 6. Testing (`tests/`)
Total of **41 tests**, all passing: **12 valid** inputs (V1–V12) with exact expected event lists, **14 lexical/syntactic errors** (E1–E14), **10 semantic errors** (S1–S10), **5 WAV tests** (length, 440 Hz peak via FFT, determinism, limiter, format).
For each test, the input, expected result, and actual result appear in the console and in the `tests/report.md` table.

## 8. Development Challenges and Solutions
- **Keyword vs. identifier:** a contextual lexer would have accepted `let pattern = 3;` → basic lexer, `\b` keyword groups with priority.
- **Separating lexical and syntactic errors:** Lark exception types + custom precheck for unterminated strings/comments.
- **Exact timing:** `Fraction` instead of accumulating floating-point errors; thus tests can be compared byte-for-byte.
- **Scope of transposition:** block-level restoration (inside a pattern or `repeat` does not leak out).
- **Distortion:** limiter when many notes play simultaneously.
- **Circular patterns:** DFS with three colors, printing the cycle; thus expansion is always finite.

## 9. Grading Alignment
| Requirement | Where It Is Fulfilled |
|---|---|
| Custom language and grammar | `grammar.lark`, Section 1 |
| Lexical and syntactic analysis | `parser.py`, E1–E14 |
| AST | `ast_nodes.py`, `Builder`, `--ast/--dot` |
| Working compiler | `semantic.py` + `compiler.py` + `synth.py` → WAV |
| Testing, presentation | `tests/`, Section 7 |

## 10. Further Improvement Ideas
time-signature checking (`time 4/4`), parameterized patterns, `swing`, stereo panning, MIDI export, key-dependent chord names (`chord Am7`), custom LL(1) parser.