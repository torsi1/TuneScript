"""Illustration of processing steps: AST in text format, AST in Graphviz (.dot) format, event table, piano roll."""
from . import ast_nodes as A
from .compiler import midi_name, Score


def _label(n) -> str:
    extra = []
    for k, v in n.__dict__.items():
        if k in ("line", "col") or isinstance(v, list) or hasattr(v, "__dataclass_fields__"):
            continue
        if v is not None:
            extra.append(f"{k}={v!r}")
    return type(n).__name__ + (" (" + ", ".join(extra) + ")" if extra else "")


def ast_text(node, indent=0) -> str:
    out = [" " * indent + _label(node) + f"  [{node.line}:{node.col}]"]
    for field, child in A.children(node):
        out.append(ast_text(child, indent + 2))
    return "\n".join(out)


def ast_dot(root) -> str:
    lines = ["digraph AST {", '  node [shape=box, fontname="Helvetica"];']
    counter = [0]

    def walk(n):
        my = counter[0]
        counter[0] += 1
        lab = _label(n).replace('"', "'")
        lines.append(f'  n{my} [label="{lab}"];')
        for field, c in A.children(n):
            cid = walk(c)
            lines.append(f'  n{my} -> n{cid} [label="{field}", fontsize=9];')
        return my

    walk(root)
    lines.append("}")
    return "\n".join(lines)


def events_table(score: Score) -> str:
    rows = [f"{'track':<10} {'note':<8} {'start (beats)':>13} {'duration':>7} {'start (sec)':>11} {'amp':>5}"]
    for e in score.events:
        what = midi_name(e.midi) if e.kind == "note" else e.drum
        rows.append(f"{e.track:<10} {what:<8} {str(e.start):>13} {str(e.dur):>7} "
                    f"{score.beats_to_seconds(e.start):>11.3f} {e.amp:>5.2f}")
    return "\n".join(rows)


def piano_roll(score: Score, width=64) -> str:
    """Per track a line: the time from left to right, '#' where something is playing."""
    total = float(score.total_beats) or 1.0
    names = []
    for e in score.events:
        if e.track not in names:
            names.append(e.track)
    out = []
    for name in names:
        row = ["."] * width
        for e in score.events:
            if e.track != name:
                continue
            a = int(float(e.start) / total * width)
            b = max(a + 1, int(float(e.start + e.dur) / total * width))
            for i in range(a, min(b, width)):
                row[i] = "#"
        out.append(f"{name:<10}|{''.join(row)}|")
    return "\n".join(out)
