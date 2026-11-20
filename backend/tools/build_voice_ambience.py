"""Reproduce original procedural beds; no recordings, voices or third-party audio."""
import math
import random
import struct
import wave
from pathlib import Path


def build(folder):
    rate, seconds = 16000, 20
    folder.mkdir(parents=True, exist_ok=True)
    rng = random.Random(190019)
    office, typing = [], [0.0] * (rate * seconds)
    low = 0.0
    for index in range(rate * seconds):
        t = index / rate
        low = 0.92 * low + 0.08 * rng.uniform(-1, 1)
        office.append(low * 0.25 + 0.007 * math.sin(2 * math.pi * 120 * t)
                      + 0.004 * math.sin(2 * math.pi * 187 * t))
    t = 0.35
    while t < seconds - 0.2:
        # Irregular typing groups, alternating key down/up and occasional space.
        for _ in range(rng.randint(3, 13)):
            if t >= seconds - 0.15:
                break
            start = int(t * rate)
            frequency, strength = rng.uniform(900, 2300), rng.uniform(0.15, 0.55)
            for index in range(int(rate * 0.045)):
                position = start + index
                if position >= len(typing):
                    break
                dt = index / rate
                click = (rng.uniform(-1, 1) * 0.65 + math.sin(2 * math.pi * frequency * dt) * 0.35)
                typing[position] += click * strength * math.exp(-dt * 170)
            t += rng.uniform(0.075, 0.22)
        t += rng.uniform(0.6, 2.5)
    for name, values in (("office", office), ("typing", typing)):
        with wave.open(str(folder / (name + ".wav")), "wb") as output:
            output.setparams((1, 2, rate, 0, "NONE", "not compressed"))
            output.writeframes(b"".join(struct.pack("<h", round(max(-1, min(1, value)) * 32767)) for value in values))


if __name__ == "__main__":
    build(Path(__file__).resolve().parents[1] / "app/institutional/voice_assets")
