"""Command-line interface: python -m tunescript program.tune [-o ki.wav] [--ast] [--dot f.dot] [--events] [--roll] [--check] [--play]"""
import argparse
import os
import subprocess
import sys

from .api import build_score
from .errors import TuneError
from .visualize import ast_text, ast_dot, events_table, piano_roll


def _play(path):
    try:
        if sys.platform.startswith("win"):
            import winsound
            winsound.PlaySound(path, winsound.SND_FILENAME)
        elif sys.platform == "darwin":
            subprocess.run(["afplay", path], check=False)
        else:
            subprocess.run(["aplay", path], check=False)
    except Exception as exc:                                           # the playback is optional
        print(f"(the playback failed: {exc})")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="tunescript", description="TuneScript translator: .tune source to WAV file")
    ap.add_argument("source", help="the .tune source file")
    ap.add_argument("-o", "--output", help="output WAV file (overrides the export directive in the source)")
    ap.add_argument("--ast", action="store_true", help="print the AST")
    ap.add_argument("--dot", metavar="FILE", help="save the AST to a Graphviz .dot file")
    ap.add_argument("--events", action="store_true", help="print the audio events table")
    ap.add_argument("--roll", action="store_true", help="print the piano roll table")
    ap.add_argument("--check", action="store_true", help="just check, don't generate WAV")
    ap.add_argument("--play", action="store_true", help="play the generated WAV file")
    args = ap.parse_args(argv)

    with open(args.source, encoding="utf-8") as f:
        source = f.read()
    try:
        ast, score = build_score(source)
    except TuneError as e:
        print(e.format(source), file=sys.stderr)
        return 1

    if args.ast:
        print(ast_text(ast))
    if args.dot:
        with open(args.dot, "w", encoding="utf-8") as f:
            f.write(ast_dot(ast))
        print(f"AST saved: {args.dot}")
    if args.events:
        print(events_table(score))
    if args.roll:
        print(piano_roll(score))
    for w in score.warnings:
        print(f"Warning: {w}")
    print(f"OK: {len(score.events)} events, {score.total_seconds:.2f} s, {score.tempo:g} BPM")
    if args.check:
        return 0

    from .synth import render, write_wav            # numpy csak a szintézishez kell
    out = args.output or score.export or os.path.splitext(args.source)[0] + ".wav"
    samples, info = render(score)
    write_wav(out, samples)
    print(f"WAV ready: {out} ({info.frames} sample, 44100 Hz, mono, 16 bit)"
          + ("; the limiter limited the peak" if info.limited else ""))
    if args.play:
        _play(out)
    return 0
