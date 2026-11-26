"""Test cases: source + expected result.
 - valid input:  ("ok", expected_events_space_separated, expected_total_duration_beats)
 - invalid input:   ("error", category, "line:column", message_fragment)
The event format is:  track:note@start+duration  (in beats, exact fractions)."""

VALID = [
    ("V1 minimal song",
     'song "V1" { tempo 120; track lead with sine { C4 quarter; } }',
     "lead:C4@0+1", "1"),

    ("V2 duration values: dotted, triplet, rest",
     'song "V2" { tempo 60; track t with square { C4 half; D4 quarter dotted; rest eighth; E4 eighth triplet; } }',
     "t:C4@0+2 t:D4@2+3/2 t:E4@4+1/3", "13/3"),

    ("V3 chords: by name and note list",
     'song "V3" { tempo 120; track pad with triangle { chord C4 major whole; chord [A3, C4, E4] half vol 50; } }',
     "pad:C4@0+4 pad:E4@0+4 pad:G4@0+4 pad:A3@4+2 pad:C4@4+2 pad:E4@4+2", "6"),

    ("V4 variables and expressions (precedence)",
     'song "V4" { let bpm = 60 + 30 * 2; let steps = 2 * (1 + 1); tempo bpm; '
     'track a with saw { repeat steps { G4 sixteenth; } } }',
     "a:G4@0+1/4 a:G4@1/4+1/4 a:G4@1/2+1/4 a:G4@3/4+1/4", "1"),

    ("V5 pattern and play ... times",
     'song "V5" { tempo 100; pattern riff { E4 eighth; G4 eighth; } '
     'track gt with pluck { play riff times 2; A4 quarter; } }',
     "gt:E4@0+1/2 gt:G4@1/2+1/2 gt:E4@1+1/2 gt:G4@3/2+1/2 gt:A4@2+1", "3"),

    ("V6 nested patterns and repeat",
     'song "V6" { tempo 120; pattern a { C4 eighth; } pattern b { play a times 2; D4 eighth; } '
     'track t with sine { repeat 2 { play b; } } }',
     "t:C4@0+1/2 t:C4@1/2+1/2 t:D4@1+1/2 t:C4@3/2+1/2 t:C4@2+1/2 t:D4@5/2+1/2", "3"),

    ("V7 transpose range (to block end)",
     'song "V7" { tempo 120; track t with sine { C4 quarter; transpose 2; C4 quarter; '
     'repeat 1 { transpose 5; C4 quarter; } C4 quarter; } }',
     "t:C4@0+1 t:D4@1+1 t:F4@2+1 t:D4@3+1", "4"),

    ("V8 drum pattern (kick, hat, accent)",
     'song "V8" { tempo 120; track beat with sine { drums { kick "x..."; hat "x.X."; } } }',
     "beat:kick@0+1/4 beat:hat@0+1/4 beat:hat@1/2+1/4", "1"),

    ("V9 multiple tracks simultaneously + comments",
     '// line comment\nsong "V9" { /* block comment */ tempo 90;\n'
     ' track bass with saw volume 80 { C2 half; G2 half; }\n'
     ' track lead with square { rest half; E4 half; } }',
     "bass:C2@0+2 bass:G2@2+2 lead:E4@2+2", "4"),

    ("V10 export + main volume + variable in track volume",
     'song "V10" { tempo 100; volume 80; let v = 50 + 25; export "ki.wav"; '
     'track t with triangle volume v { A3 whole; } }',
     "t:A3@0+4", "4"),

    ("V11 modified notes and the boundaries of the range",
     'song "V11" { tempo 120; track t with sine { C#4 quarter; Bb3 quarter; A0 quarter; C8 quarter; } }',
     "t:C#4@0+1 t:A#3@1+1 t:A0@2+1 t:C8@3+1", "4"),

    ("V12 nested repeat",
     'song "V12" { tempo 120; track t with sine { repeat 2 { repeat 3 { C4 sixteenth; } rest quarter; } } }',
     "t:C4@0+1/4 t:C4@1/4+1/4 t:C4@1/2+1/4 t:C4@7/4+1/4 t:C4@2+1/4 t:C4@9/4+1/4", "7/2"),
]

# (name, source, category, "line:column", message fragment)
LEX = "Lexical error"
SYN = "Syntax error"
SEM = "Semantic error"

INVALID = [
    ("E1 unknown character (@)",
     'song "E1" {\n  tempo 120;\n  track t with sine { C4 quarter @; }\n}',
     LEX, "3:34", "unknown character"),

    ("E2 invalid note name (H4)",
     'song "E2" {\n  tempo 120;\n  track t with sine { H4 quarter; }\n}',
     LEX, "3:23", "unknown character 'H'"),

    ("E3 unknown string",
     'song "E3" {\n  tempo 120;\n}',
     LEX, "1:6", "unknown string"),

    ("E4 unknown block comment",
     'song "E4" {\n  /* never closes */\n  tempo 120;\n}',
     LEX, "2:3", "unknown block comment"),

    ("E5 unknown character in variable name ($)",
     'song "E5" {\n  let $x = 5;\n}',
     LEX, "2:7", "unknown character '$'"),

    ("E6 missing semicolon",
     'song "E6" {\n  tempo 120\n  track t with sine { C4 quarter; }\n}',
     SYN, "3:3", "unexpected 'track'"),

    ("E7 missing closing curly brace",
     'song "E7" {\n  tempo 120;\n  track t with sine { C4 quarter; }',
     SYN, "3:36", "unexpected end of file"),

    ("E8 invalid duration (quarte)",
     'song "E8" {\n  track t with sine { C4 quarte; }\n}',
     SYN, "2:26", "unexpected 'quarte'"),

    ("E9 missing instrument (without 'with')",
     'song "E9" {\n  track t { C4 quarter; }\n}',
     SYN, "2:11", "unexpected '{'"),

    ("E10 unbalanced chord list",
     'song "E10" {\n  track t with sine { chord [C4, E4 half; }\n}',
     SYN, "2:37", "unexpected 'half'"),

    ("E11 keyword as identifier (pattern)",
     'song "E11" {\n  let pattern = 3;\n}',
     SYN, "2:7", "unexpected 'pattern'"),

    ("E12 missing song header",
     'tempo 120;',
     SYN, "1:1", "unexpected 'tempo'"),

    ("E13 drums number instead of string",
     'song "E13" {\n  track t with sine { drums { kick 1010; } }\n}',
     SYN, "2:36", "unexpected '1010'"),

    ("E14 repeat without arguments",
     'song "E14" {\n  track t with sine { repeat { C4 quarter; } }\n}',
     SYN, "2:30", "unexpected '{'"),
]

SEMANTIC = [
    ("S1 is not declared variable",
     'song "S1" {\n  tempo bpm;\n  track t with sine { C4 quarter; }\n}',
     SEM, "2:9", "'bpm' variable is not declared"),

    ("S2 variable redeclaration",
     'song "S2" {\n  let a = 1;\n  let a = 2;\n  track t with sine { C4 quarter; }\n}',
     SEM, "3:7", "already declared"),

    ("S3 tempo out of allowed range",
     'song "S3" {\n  tempo 500;\n  track t with sine { C4 quarter; }\n}',
     SEM, "2:9", "tempo"),

    ("S4 non-existent pattern",
     'song "S4" {\n  track t with sine { play solo; }\n}',
     SEM, "2:23", "'solo' pattern is not defined"),

    ("S5 circular pattern reference",
     'song "S5" {\n  pattern a { play b; }\n  pattern b { play a; }\n  track t with sine { play a; }\n}',
     SEM, "3:15", "circular"),

    ("S6 out of allowed range note",
     'song "S6" {\n  track t with sine { transpose 1; C8 quarter; }\n}',
     SEM, "2:36", "out of allowed range"),

    ("S7 different length drum patterns",
     'song "S7" {\n  track t with sine { drums { kick "x..."; hat "x."; } }\n}',
     SEM, "2:44", "different lengths"),

    ("S8 invalid character in drum pattern",
     'song "S8" {\n  track t with sine { drums { kick "x-.."; } }\n}',
     SEM, "2:31", "invalid character in drum pattern"),

    ("S9 division by zero",
     'song "S9" {\n  let z = 0;\n  tempo 120 / z;\n  track t with sine { C4 quarter; }\n}',
     SEM, "3:9", "division by zero"),

    ("S10 non-integer repeat count",
     'song "S10" {\n  track t with sine { repeat 2.5 { C4 quarter; } }\n}',
     SEM, "2:30", "integer"),
]
