"""Show SVT Valkompass screenshots to a fruit fly connectome and let its mushroom body pick.

Per question: blank screen, question screenshot, blank screen, snapshot. From that
snapshot the fly sees a blank (baseline) and each answer tile under a few fixed
pixel jitters. Valence per tile = mean MBON07 (approach) rate minus mean MBON11
(avoidance) rate, minus the same during the blank. Each jitter trial votes for its
best tile; most votes wins. The fly then sees the winner so its state carries on.
The fly cannot read.
"""

import re
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from PIL import Image

from neural.common import annotations
from neural.controller import FlyController

SETTINGS = SimpleNamespace(
    neural_ms=500,
    neural_bin_ms=10,
    pulse_ms=200,
    pulse_current=20,
    decoder_threshold_hz=2,
    learning=False,
)
BLANK = np.full((180, 320, 3), 128, dtype=np.uint8)
# (dx, dy, brightness gain). Trial 0 is the unjittered tile.
JITTERS = [(0, 0, 1.0), (2, 1, 1.05), (-2, -1, 0.95), (1, -2, 1.03), (-1, 2, 0.97)]


def load(path):
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.uint8)


def jitter(frame, dx, dy, gain):
    shifted = np.roll(frame, (dy, dx), axis=(0, 1))
    return np.clip(shifted.astype(np.float32) * gain, 0, 255).astype(np.uint8)


def snapshot(brain):
    return {k: getattr(brain, k).copy() for k in brain.fields}, brain.cursor


def restore(brain, snap):
    fields, cursor = snap
    for k, v in fields.items():
        getattr(brain, k)[:] = v
    brain.cursor = cursor
    brain.sim_ms = cursor * brain.dt


class Valence:
    def __init__(self, brain):
        types = annotations(brain.ids).type.fillna("")
        self.approach = np.flatnonzero(types.eq("MBON07"))
        self.avoid = np.flatnonzero(types.eq("MBON11"))
        self.brain = brain

    def __call__(self):
        seconds = SETTINGS.neural_ms / 1000
        counts = self.brain.counts
        return float(counts[self.approach].mean() - counts[self.avoid].mean()) / seconds


def label(tile_name):
    return tile_name.split("-", 1)[1].replace("-", " ") if "-" in tile_name else tile_name


def question_number(path):
    return int(re.match(r"\d+", path.stem).group())


def tile_format(path):
    return "scale" if re.match(r"\d+s", path.stem) else "smiley"


def decide(fly, valence, tiles):
    brain = fly.brain
    snap = snapshot(brain)
    fly.observe(BLANK, "none")
    baseline = valence()
    scores = np.zeros((len(JITTERS), len(tiles)))
    for t, (dx, dy, gain) in enumerate(JITTERS):
        for i, (_, tile) in enumerate(tiles):
            restore(brain, snap)
            fly.observe(jitter(tile, dx, dy, gain), "none")
            scores[t, i] = valence() - baseline
    votes = np.zeros(len(tiles), dtype=int)
    for row in scores:
        winners = np.flatnonzero(row == row.max())
        if len(winners) == 1:
            votes[winners[0]] += 1
    restore(brain, snap)
    return scores.mean(axis=0), votes


def main(folder):
    shots = sorted(Path(folder).glob("*.png"), key=question_number)
    if not shots:
        sys.exit(f"No PNGs in {folder}")
    tile_sets = {
        fmt: [(o.stem, load(o)) for o in sorted(Path("options", fmt).glob("*.png"))]
        for fmt in ["smiley", "scale"]
    }
    fly = FlyController(SETTINGS)
    valence = Valence(fly.brain)
    print(f"{'#':>3}  {'question':<40}  " + "".join(f"{i:>7}" for i in range(1, 6)) + "  answer")
    for shot in shots:
        tiles = tile_sets[tile_format(shot)]
        fly.observe(BLANK, "none")
        fly.observe(load(shot), "none")
        fly.observe(BLANK, "none")
        scores, votes = decide(fly, valence, tiles)
        leaders = np.flatnonzero(votes == votes.max())
        if len(leaders) == 1 and votes.max() > 0:
            answer = f"{label(tiles[leaders[0]][0])} ({votes.max()}/{len(JITTERS)})"
            fly.observe(tiles[leaders[0]][1], "none")
        else:
            answer = "hoppa över (" + ", ".join(label(tiles[i][0]) for i in leaders) + ")"
        question = shot.stem.split("-", 1)[1][:40]
        cells = "".join(f"{s:>+7.2f}" for s in scores) + "       " * (5 - len(scores))
        print(f"{question_number(shot):>3}  {question:<40}  {cells}  {answer}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "screenshots")
