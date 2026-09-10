"""Show SVT Valkompass screenshots to a fruit fly connectome and let its mushroom body pick.

Per question: blank screen, question screenshot, blank screen, snapshot. From that
snapshot the fly sees a blank (baseline) and each answer tile under a few fixed
pixel jitters. Valence per tile = mean MBON07 (approach) rate minus mean MBON11
(avoidance) rate, minus the same during the blank. Highest mean over the jitter trials wins;
the printed n/5 is how many trials agreed, and 5/5 marks the question "extra viktigt".
The fly then sees the winner so its state carries on. The fly cannot read.
"""

import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from neural.common import annotations
from neural.visual import VisualMemoryBrain

EXPOSURE_MS = 500
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


class Fly:
    def __init__(self):
        self.brain = VisualMemoryBrain()
        self.brain.weights_frozen = True
        types = annotations(self.brain.ids).type.fillna("")
        self.approach = np.flatnonzero(types.eq("MBON07"))
        self.avoid = np.flatnonzero(types.eq("MBON11"))

    def see(self, frame):
        self.brain.rgb_step(frame, EXPOSURE_MS, learning=False)

    def valence(self):
        counts = self.brain.counts
        hz = 1000 / EXPOSURE_MS
        return float(counts[self.approach].mean() - counts[self.avoid].mean()) * hz


def label(tile_name):
    return tile_name.split("-", 1)[1].replace("-", " ") if "-" in tile_name else tile_name


def question_number(path):
    return int(re.match(r"\d+", path.stem).group())


def tile_format(path):
    return "scale" if re.match(r"\d+s", path.stem) else "smiley"


def decide(fly, tiles):
    brain = fly.brain
    snap = snapshot(brain)
    fly.see(BLANK)
    baseline = fly.valence()
    scores = np.zeros((len(JITTERS), len(tiles)))
    for t, (dx, dy, gain) in enumerate(JITTERS):
        for i, (_, tile) in enumerate(tiles):
            restore(brain, snap)
            fly.see(jitter(tile, dx, dy, gain))
            scores[t, i] = fly.valence() - baseline
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
    fly = Fly()
    print(f"{'#':>3}  {'question':<40}  " + "".join(f"{i:>7}" for i in range(1, 6)) + "  answer")
    for shot in shots:
        scale = tile_format(shot) == "scale"
        tiles = tile_sets["scale" if scale else "smiley"]
        fly.see(BLANK)
        fly.see(load(shot))
        fly.see(BLANK)
        scores, votes = decide(fly, tiles)
        leaders = np.flatnonzero(scores == scores.max())
        if len(leaders) == 1:
            best = leaders[0]
            important = votes[best] == len(JITTERS)
            answer = f"{label(tiles[best][0])} ({votes[best]}/{len(JITTERS)})" + (" extra viktigt" if important else "")
            fly.see(tiles[best][1])
        else:
            answer = "hoppa över (" + ", ".join(label(tiles[i][0]) for i in leaders) + ")"
        question = shot.stem.split("-", 1)[1][:40]
        cells = "".join(f"{s:>+7.2f}" for s in scores) + "       " * (5 - len(scores))
        print(f"{question_number(shot):>3}  {question:<40}  {cells}  {answer}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "screenshots")
