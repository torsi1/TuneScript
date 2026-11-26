# TuneScript – test report

**33/41 tests passed.**

| Test | Input | Expected Result | Actual Result | |
|---|---|---|---|---|
| V1 minimal song | `song "V1" { tempo 120; track lead with sine { C4 quarter; } }` | lead:C4@0+1  \| total 1 beats | lead:C4@0+1  \| total 1 beats | ✅ |
| V2 duration values: dotted, triplet, rest | `song "V2" { tempo 60; track t with square { C4 half; D4 quarter dotted; rest eighth; E4 e…` | t:C4@0+2 t:D4@2+3/2 t:E4@4+1/3  \| total 13/3 beats | t:C4@0+2 t:D4@2+3/2 t:E4@4+1/3  \| total 13/3 beats | ✅ |
| V3 chords: by name and note list | `song "V3" { tempo 120; track pad with triangle { chord C4 major whole; chord [A3, C4, E4]…` | pad:C4@0+4 pad:E4@0+4 pad:G4@0+4 pad:A3@4+2 pad:C4@4+2 pad:E4@4+2  \| total 6 beats | pad:C4@0+4 pad:E4@0+4 pad:G4@0+4 pad:A3@4+2 pad:C4@4+2 pad:E4@4+2  \| total 6 beats | ✅ |
| V4 variables and expressions (precedence) | `song "V4" { let bpm = 60 + 30 * 2; let steps = 2 * (1 + 1); tempo bpm; track a with saw {…` | a:G4@0+1/4 a:G4@1/4+1/4 a:G4@1/2+1/4 a:G4@3/4+1/4  \| total 1 beats | a:G4@0+1/4 a:G4@1/4+1/4 a:G4@1/2+1/4 a:G4@3/4+1/4  \| total 1 beats | ✅ |
| V5 pattern and play ... times | `song "V5" { tempo 100; pattern riff { E4 eighth; G4 eighth; } track gt with pluck { play …` | gt:E4@0+1/2 gt:G4@1/2+1/2 gt:E4@1+1/2 gt:G4@3/2+1/2 gt:A4@2+1  \| total 3 beats | gt:E4@0+1/2 gt:G4@1/2+1/2 gt:E4@1+1/2 gt:G4@3/2+1/2 gt:A4@2+1  \| total 3 beats | ✅ |
| V6 nested patterns and repeat | `song "V6" { tempo 120; pattern a { C4 eighth; } pattern b { play a times 2; D4 eighth; } …` | t:C4@0+1/2 t:C4@1/2+1/2 t:D4@1+1/2 t:C4@3/2+1/2 t:C4@2+1/2 t:D4@5/2+1/2  \| total 3 beats | t:C4@0+1/2 t:C4@1/2+1/2 t:D4@1+1/2 t:C4@3/2+1/2 t:C4@2+1/2 t:D4@5/2+1/2  \| total 3 beats | ✅ |
| V7 transpose range (to block end) | `song "V7" { tempo 120; track t with sine { C4 quarter; transpose 2; C4 quarter; repeat 1 …` | t:C4@0+1 t:D4@1+1 t:F4@2+1 t:D4@3+1  \| total 4 beats | t:C4@0+1 t:D4@1+1 t:F4@2+1 t:D4@3+1  \| total 4 beats | ✅ |
| V8 drum pattern (kick, hat, accent) | `song "V8" { tempo 120; track beat with sine { drums { kick "x..."; hat "x.X."; } } }` | beat:kick@0+1/4 beat:hat@0+1/4 beat:hat@1/2+1/4  \| total 1 beats | beat:kick@0+1/4 beat:hat@0+1/4 beat:hat@1/2+1/4  \| total 1 beats | ✅ |
| V9 multiple tracks simultaneously + comments | `// line comment song "V9" { /* block comment */ tempo 90; track bass with saw volume 80 {…` | bass:C2@0+2 bass:G2@2+2 lead:E4@2+2  \| total 4 beats | bass:C2@0+2 bass:G2@2+2 lead:E4@2+2  \| total 4 beats | ✅ |
| V10 export + main volume + variable in track volume | `song "V10" { tempo 100; volume 80; let v = 50 + 25; export "ki.wav"; track t with triangl…` | t:A3@0+4  \| total 4 beats | t:A3@0+4  \| total 4 beats | ✅ |
| V11 modified notes and the boundaries of the range | `song "V11" { tempo 120; track t with sine { C#4 quarter; Bb3 quarter; A0 quarter; C8 quar…` | t:C#4@0+1 t:A#3@1+1 t:A0@2+1 t:C8@3+1  \| total 4 beats | t:C#4@0+1 t:A#3@1+1 t:A0@2+1 t:C8@3+1  \| total 4 beats | ✅ |
| V12 nested repeat | `song "V12" { tempo 120; track t with sine { repeat 2 { repeat 3 { C4 sixteenth; } rest qu…` | t:C4@0+1/4 t:C4@1/4+1/4 t:C4@1/2+1/4 t:C4@7/4+1/4 t:C4@2+1/4 t:C4@9/4+1/4  \| total 7/2 beats | t:C4@0+1/4 t:C4@1/4+1/4 t:C4@1/2+1/4 t:C4@7/4+1/4 t:C4@2+1/4 t:C4@9/4+1/4  \| total 7/2 beats | ✅ |
| E1 unknown character (@) | `song "E1" { tempo 120; track t with sine { C4 quarter @; } }` | Lexical error 3:34: …unknown character… | Lexical error 3:34: unknown character '@' | ✅ |
| E2 invalid note name (H4) | `song "E2" { tempo 120; track t with sine { H4 quarter; } }` | Lexical error 3:23: …unknown character 'H'… | Lexical error 3:23: unknown character 'H' (note: A–G letters, optional #/b, then octave number) | ✅ |
| E3 unknown string | `song "E3" { tempo 120; }` | Lexical error 1:6: …unknown string… | Semantic error 1:1: at least one track is required | ❌ |
| E4 unknown block comment | `song "E4" { /* never closes */ tempo 120; }` | Lexical error 2:3: …unknown block comment… | Semantic error 1:1: at least one track is required | ❌ |
| E5 unknown character in variable name ($) | `song "E5" { let $x = 5; }` | Lexical error 2:7: …unknown character '$'… | Lexical error 2:7: unknown character '$' | ✅ |
| E6 missing semicolon | `song "E6" { tempo 120 track t with sine { C4 quarter; } }` | Syntax error 3:3: …unexpected 'track'… | Syntax error 3:3: unexpected 'track'; expected: '*', '+', '-', '/', ';' | ✅ |
| E7 missing closing curly brace | `song "E7" { tempo 120; track t with sine { C4 quarter; }` | Syntax error 3:36: …unexpected end of file… | Syntax error 3:36: unexpected file end; expected: 'export', 'let', 'pattern', 'tempo', 'track', 'volume', '}' | ❌ |
| E8 invalid duration (quarte) | `song "E8" { track t with sine { C4 quarte; } }` | Syntax error 2:26: …unexpected 'quarte'… | Syntax error 2:26: unexpected 'quarte'; expected: duration (whole/half/quarter/eighth/sixteenth) | ✅ |
| E9 missing instrument (without 'with') | `song "E9" { track t { C4 quarter; } }` | Syntax error 2:11: …unexpected '{'… | Syntax error 2:11: unexpected '{'; expected: 'with' | ✅ |
| E10 unbalanced chord list | `song "E10" { track t with sine { chord [C4, E4 half; } }` | Syntax error 2:37: …unexpected 'half'… | Syntax error 2:37: unexpected 'half'; expected: ',', ']' | ✅ |
| E11 keyword as identifier (pattern) | `song "E11" { let pattern = 3; }` | Syntax error 2:7: …unexpected 'pattern'… | Syntax error 2:7: unexpected 'pattern'; expected: identifier | ✅ |
| E12 missing song header | `tempo 120;` | Syntax error 1:1: …unexpected 'tempo'… | Syntax error 1:1: unexpected 'tempo'; expected: 'song' | ✅ |
| E13 drums number instead of string | `song "E13" { track t with sine { drums { kick 1010; } } }` | Syntax error 2:36: …unexpected '1010'… | Syntax error 2:36: unexpected '1010'; expected: string ("...") | ✅ |
| E14 repeat without arguments | `song "E14" { track t with sine { repeat { C4 quarter; } } }` | Syntax error 2:30: …unexpected '{'… | Syntax error 2:30: unexpected '{'; expected: '(', '-', identifier, number | ✅ |
| S1 is not declared variable | `song "S1" { tempo bpm; track t with sine { C4 quarter; } }` | Semantic error 2:9: …'bpm' variable is not declared… | Semantic error 2:9: the variable 'bpm' is not declared | ❌ |
| S2 variable redeclaration | `song "S2" { let a = 1; let a = 2; track t with sine { C4 quarter; } }` | Semantic error 3:7: …already declared… | Semantic error 3:7: the variable 'a' is already declared | ✅ |
| S3 tempo out of allowed range | `song "S3" { tempo 500; track t with sine { C4 quarter; } }` | Semantic error 2:9: …tempo… | Semantic error 2:9: the tempo (BPM) value is 500, but only 20–300 is allowed | ✅ |
| S4 non-existent pattern | `song "S4" { track t with sine { play solo; } }` | Semantic error 2:23: …'solo' pattern is not defined… | Semantic error 2:23: the pattern 'solo' is not defined | ❌ |
| S5 circular pattern reference | `song "S5" { pattern a { play b; } pattern b { play a; } track t with sine { play a; } }` | Semantic error 3:15: …circular… | Semantic error 3:15: circular pattern reference: a → b → a | ✅ |
| S6 out of allowed range note | `song "S6" { track t with sine { transpose 1; C8 quarter; } }` | Semantic error 2:36: …out of allowed range… | Semantic error 2:36: the note C8 is out of the instrument's range (A0–C8) | ❌ |
| S7 different length drum patterns | `song "S7" { track t with sine { drums { kick "x..."; hat "x."; } } }` | Semantic error 2:44: …different lengths… | Semantic error 2:44: the lengths of the drum patterns differ: 2 steps, the first line has 4 steps | ❌ |
| S8 invalid character in drum pattern | `song "S8" { track t with sine { drums { kick "x-.."; } } }` | Semantic error 2:31: …invalid character in drum pattern… | Semantic error 2:31: invalid character in the drum pattern: '-' (only x, X and . are allowed) | ❌ |
| S9 division by zero | `song "S9" { let z = 0; tempo 120 / z; track t with sine { C4 quarter; } }` | Semantic error 3:9: …division by zero… | Semantic error 3:9: division by zero | ✅ |
| S10 non-integer repeat count | `song "S10" { track t with sine { repeat 2.5 { C4 quarter; } } }` | Semantic error 2:30: …integer… | Semantic error 2:30: the repeat count (repeat) must be an integer (got: 2.5) | ✅ |

## WAV tests

| Test | Result | |
|---|---|---|
| W1 the WAV length (4 s + tail) | 189630 samples (expected 189630) | ✅ |
| W2 the A4 note frequency is 440 Hz | measured peak: 440.00 Hz | ✅ |
| W3 deterministic (same output twice) | d9455f96 / d9455f96 | ✅ |
| W4 the limiter prevents over-modulation | peak before limiter: 3.07, after: 0.98 | ✅ |
| W5 WAV-format: mono, 16 bit, 44100 Hz | wave module read back | ✅ |
