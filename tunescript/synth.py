"""Hangszintézis és WAV-írás: mono, 16 bites, 44100 Hz. A hullámformák numpy-val készülnek,
a zajalapú dobhangok rögzített véletlen maggal, így a kimenet reprodukálható (azonos bemenet -> azonos fájl)."""
import wave
from dataclasses import dataclass
import numpy as np
from .compiler import Score

SAMPLE_RATE = 44100
TAIL_SECONDS = 0.3          # the drum decays at the end of the song 
BASE_GAIN = 0.28


@dataclass
class RenderInfo:
    frames: int
    peak_before_limit: float
    limited: bool


def _oscillator(instr: str, freq: float, t: np.ndarray) -> np.ndarray:
    ph = (freq * t) % 1.0
    if instr == "sine":
        return np.sin(2 * np.pi * freq * t)
    if instr == "square":
        return np.where(ph < 0.5, 1.0, -1.0) * 0.6
    if instr == "saw":
        return (2 * ph - 1) * 0.7
    if instr == "triangle":
        return 4 * np.abs(ph - 0.5) - 1
    if instr == "pluck":                      # sawtooth decay + mild harmonics
        return ((2 * ph - 1) * 0.6 + np.sin(2 * np.pi * 2 * freq * t) * 0.3) * np.exp(-t * 5.0)
    raise ValueError(instr)


def _envelope(n: int) -> np.ndarray:
    env = np.ones(n)
    na = min(int(0.01 * SAMPLE_RATE), n // 4)
    nr = min(int(0.06 * SAMPLE_RATE), n // 3)
    if na > 0:
        env[:na] = np.linspace(0.0, 1.0, na)
    if nr > 0:
        env[-nr:] *= np.linspace(1.0, 0.0, nr)
    return env


def render_note(instr: str, midi: int, seconds: float) -> np.ndarray:
    n = max(int(round(seconds * SAMPLE_RATE)), 1)
    t = np.arange(n) / SAMPLE_RATE
    freq = 440.0 * 2.0 ** ((midi - 69) / 12.0)
    return _oscillator(instr, freq, t) * _envelope(n)


def render_drum(name: str, rng: np.random.Generator) -> np.ndarray:
    def tt(sec):
        return np.arange(int(sec * SAMPLE_RATE)) / SAMPLE_RATE

    if name == "kick":
        t = tt(0.25)
        phase = 2 * np.pi * (45 * t + 110 * (1 - np.exp(-30 * t)) / 30)      # 155 Hz -> 45 Hz slide-down
        return np.sin(phase) * np.exp(-t * 14) * 1.6
    if name == "snare":
        t = tt(0.2)
        noise = rng.uniform(-1, 1, t.size)
        return (noise * np.exp(-t * 28) * 0.8 + np.sin(2 * np.pi * 190 * t) * np.exp(-t * 35) * 0.5)
    if name == "hat":
        t = tt(0.06)
        noise = rng.uniform(-1, 1, t.size)
        hp = np.diff(noise, prepend=0.0)                                      # simple high-pass filter
        return hp * np.exp(-t * 90) * 0.5
    if name == "clap":
        t = tt(0.18)
        noise = rng.uniform(-1, 1, t.size)
        bursts = np.zeros_like(t)
        for off in (0.0, 0.012, 0.024):
            m = t >= off
            bursts[m] += np.exp(-(t[m] - off) * 60)
        return noise * bursts * 0.5
    raise ValueError(name)


def render(score: Score):
    """The event list is rendered into a complete mix (float array, -1..1) and the render data."""
    total_frames = int(round(score.total_seconds * SAMPLE_RATE)) + int(round(TAIL_SECONDS * SAMPLE_RATE))
    buf = np.zeros(total_frames)
    rng = np.random.default_rng(1234)
    cache = {}
    for ev in score.events:
        start = int(round(score.beats_to_seconds(ev.start) * SAMPLE_RATE))
        if ev.kind == "note":
            seg = render_note(ev.instrument, ev.midi, score.beats_to_seconds(ev.dur))
        else:
            seg = render_drum(ev.drum, rng)
        seg = seg * (BASE_GAIN * ev.amp)
        end = min(start + seg.size, total_frames)
        buf[start:end] += seg[: end - start]
    peak = float(np.max(np.abs(buf))) if buf.size else 0.0
    limited = peak > 0.98
    if limited:
        buf *= 0.98 / peak            # simple limiter: to prevent distortion
    return buf, RenderInfo(total_frames, peak, limited)


def write_wav(path: str, samples: np.ndarray) -> None:
    pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm.tobytes())
