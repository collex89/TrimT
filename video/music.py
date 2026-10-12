"""Generate an original, royalty-free background track for the explainer.

    python video/music.py            # -> video/music.wav

Soft pad chords (C - G - Am - F), a plucked arpeggio and a light kick and hat at 100 BPM.
"""

import sys
import wave
from pathlib import Path

import numpy as np

SR = 44_100
BPM = 100
DURATION = 44.0
OUT = Path(__file__).resolve().parent / "music.wav"

BEAT = 60 / BPM
BAR = 4 * BEAT
# chord tones as MIDI notes
CHORDS = [[48, 55, 60, 64, 67], [43, 50, 55, 59, 62], [45, 52, 57, 60, 64], [41, 48, 53, 57, 60]]

t_all = np.arange(int(SR * DURATION)) / SR


def hz(midi: float) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


def env(n: int, attack: float, release: float) -> np.ndarray:
    e = np.ones(n)
    a, r = int(attack * SR), int(release * SR)
    if a:
        e[:a] = np.linspace(0, 1, a)
    if r:
        e[-r:] *= np.linspace(1, 0, r)
    return e


def place(track: np.ndarray, start: float, sound: np.ndarray) -> None:
    i = int(start * SR)
    j = min(i + len(sound), len(track))
    if i < len(track):
        track[i:j] += sound[: j - i]


def pad_chord(notes, length):
    t = np.arange(int(length * SR)) / SR
    out = np.zeros_like(t)
    for n in notes:
        f = hz(n)
        for detune in (-0.12, 0.0, 0.12):  # slightly detuned saw-ish stack, softened
            ff = f * 2 ** (detune / 12)
            out += np.sin(2 * np.pi * ff * t) + 0.25 * np.sin(4 * np.pi * ff * t) + 0.08 * np.sin(6 * np.pi * ff * t)
    return out / (len(notes) * 3) * env(len(t), 0.9, 1.2)


def pluck(midi, length=0.5):
    t = np.arange(int(length * SR)) / SR
    f = hz(midi)
    tone = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t) + 0.12 * np.sin(6 * np.pi * f * t)
    return tone * np.exp(-t * 7) * env(len(t), 0.004, 0.05)


def kick():
    t = np.arange(int(0.35 * SR)) / SR
    f = 110 * np.exp(-t * 18) + 42
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)


def hat(rng):
    n = int(0.06 * SR)
    noise = rng.standard_normal(n)
    noise = np.diff(noise, prepend=0)  # crude high-pass
    return noise * np.exp(-np.arange(n) / SR * 60)


def main() -> int:
    rng = np.random.default_rng(7)
    pad = np.zeros_like(t_all)
    arp = np.zeros_like(t_all)
    drums = np.zeros_like(t_all)

    bars = int(DURATION / BAR) + 1
    for b in range(bars):
        start = b * BAR
        chord = CHORDS[b % len(CHORDS)]
        place(pad, start, pad_chord(chord, BAR + 1.0))
        if b >= 1:  # arpeggio enters after the first bar
            pattern = [chord[2] + 12, chord[3] + 12, chord[4] + 12, chord[3] + 12] * 2
            for k, note in enumerate(pattern):
                place(arp, start + k * BEAT / 2, pluck(note))
        if b >= 2:  # beat enters after two bars
            for beat in range(4):
                if beat in (0, 2):
                    place(drums, start + beat * BEAT, kick())
                place(drums, start + beat * BEAT + BEAT / 2, hat(rng) * 0.25)

    mix = 0.55 * pad + 0.22 * arp + 0.35 * drums
    # simple stereo: arpeggio slightly delayed on the right for width
    delay = int(0.012 * SR)
    left = mix
    right = 0.55 * pad + 0.22 * np.concatenate([np.zeros(delay), arp[:-delay]]) + 0.35 * drums
    stereo = np.stack([left, right], axis=1)

    stereo *= env(len(t_all), 1.5, 3.0)[:, None]  # fade in and out
    stereo /= np.max(np.abs(stereo)) / 0.8
    pcm = (stereo * 32767).astype(np.int16)

    with wave.open(str(OUT), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
