"""Test runner: for each test, it prints the input, the expected and the actual result.
Output: console + tests/report.md (for the demonstration). Running from the project root:  python tests/run_tests.py"""
import hashlib
import os
import sys
import wave
from fractions import Fraction

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np

from cases import VALID, INVALID, SEMANTIC
from tunescript.api import build_score
from tunescript.errors import TuneError
from tunescript.synth import render, write_wav, SAMPLE_RATE, TAIL_SECONDS

rows = []          # (name, input, expected, actual, success)


def short(src, n=70):
    s = " ".join(src.split())
    return s if len(s) <= n else s[: n - 1] + "…"


def run_valid(name, src, expected_events, expected_beats):
    try:
        _, score = build_score(src)
        actual = " ".join(e.label() for e in score.events) + f"  | total {score.total_beats} beats"
    except TuneError as e:
        actual = e.format()
    expected = expected_events + f"  | total {expected_beats} beats"
    rows.append((name, src, expected, actual, actual == expected))


def run_invalid(name, src, category, loc, fragment):
    expected = f"{category} {loc}: …{fragment}…"
    try:
        build_score(src)
        actual, ok = "no error occurred", False
    except TuneError as e:
        actual = f"{e.category} {e.location()}: {e.message}"
        ok = e.category == category and e.location() == loc and fragment in e.message
    rows.append((name, src, expected, actual, ok))


for t in VALID:
    run_valid(*t)
for t in INVALID + SEMANTIC:
    run_invalid(*t)

# WAV-tests
wav_rows = []


def wav_check(name, ok, detail):
    wav_rows.append((name, ok, detail))


src_a4 = 'song "W" { tempo 60; track t with sine { A4 whole; } }'
_, sc = build_score(src_a4)
buf, info = render(sc)
expected_frames = int(round(4 * SAMPLE_RATE)) + int(round(TAIL_SECONDS * SAMPLE_RATE))
wav_check("W1 the WAV length (4 s + tail)", info.frames == expected_frames, f"{info.frames} samples (expected {expected_frames})")
spec = np.abs(np.fft.rfft(buf))
peak_hz = float(np.argmax(spec) * SAMPLE_RATE / len(buf))
wav_check("W2 the A4 note frequency is 440 Hz", abs(peak_hz - 440.0) < 1.0, f"measured peak: {peak_hz:.2f} Hz")
buf2, _ = render(build_score(src_a4)[1])
h1 = hashlib.md5(buf.tobytes()).hexdigest()
h2 = hashlib.md5(buf2.tobytes()).hexdigest()
wav_check("W3 deterministic (same output twice)", h1 == h2, f"{h1[:8]} / {h2[:8]}")
chord4 = "chord [C4, E4, G4, C5] whole;"
src_loud = ('song "W" { tempo 120; '
            + " ".join(f"track t{i} with saw {{ {chord4} }}" for i in range(4)) + " }")
bufl, infol = render(build_score(src_loud)[1])
wav_check("W4 the limiter prevents over-modulation",
          infol.limited and float(np.max(np.abs(bufl))) <= 0.98 + 1e-9,
          f"peak before limiter: {infol.peak_before_limit:.2f}, after: {float(np.max(np.abs(bufl))):.2f}")
out = os.path.join(os.path.dirname(__file__), "_tmp_test.wav")
write_wav(out, buf)
with wave.open(out) as w:
    fmt_ok = (w.getnchannels(), w.getsampwidth(), w.getframerate()) == (1, 2, 44100)
os.remove(out)
wav_check("W5 WAV-format: mono, 16 bit, 44100 Hz", fmt_ok, "wave module read back")

# output
passed = sum(r[4] for r in rows) + sum(r[1] for r in wav_rows)
total = len(rows) + len(wav_rows)
for name, src, exp, act, ok in rows:
    print(f"[{'OK ' if ok else 'ERROR'}] {name}")
    if not ok:
        print(f"      expected:   {exp}\n      actual: {act}")
for name, ok, detail in wav_rows:
    print(f"[{'OK ' if ok else 'ERROR'}] {name} – {detail}")
print(f"\n{passed}/{total} tests passed  (correct: {len(VALID)}, lexical/syntactic errors: {len(INVALID)}, semantic errors: {len(SEMANTIC)}, WAV: {len(wav_rows)})")

# report (Markdown)
md = ["# TuneScript – test report", "",
      f"**{passed}/{total} tests passed.**", "",
      "| Test | Input | Expected Result | Actual Result | |", "|---|---|---|---|---|"]
esc = lambda s: s.replace("|", "\\|").replace("\n", " ")
for name, src, exp, act, ok in rows:
    md.append(f"| {esc(name)} | `{esc(short(src, 90))}` | {esc(exp)} | {esc(act)} | {'✅' if ok else '❌'} |")
md += ["", "## WAV tests", "", "| Test | Result | |", "|---|---|---|"]
for name, ok, detail in wav_rows:
    md.append(f"| {name} | {detail} | {'✅' if ok else '❌'} |")
with open(os.path.join(os.path.dirname(__file__), "report.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(md) + "\n")
sys.exit(0 if passed == total else 1)
