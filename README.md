![Bananflugakompassen](banner.png)

# Bananflugakompassen

A fruit fly brain answers the SVT Valkompass 2026.

The brain is the [MaleCNS v1.0](https://male-cns.janelia.org/) connectome: 166,700 neurons,
25.6 million connections, simulated as leaky integrate-and-fire cells at 0.1 ms. The
simulator, visual input mapping and dopamine circuit are copied unchanged from
[Stonkfly](https://github.com/nftechie/stonkfly), which uses the same fly to trade crypto.
This repo replaces the price chart with screenshots of election questions.

## How it works

1. Blank grey screen for 500 ms of neural time, then the question screenshot for
   500 ms, then blank again. The fly's 3,335 R1-R6 photoreceptors get luminance and
   811 R8 cells get blue/green, sampled at fixed points across the image. It cannot
   read. It sees layout and brightness. The blanks stop one question bleeding into
   the next.
2. Brain state is snapshotted.
3. From that snapshot the fly sees a blank for 500 ms. That gives the baseline.
4. From the same snapshot it sees each answer tile (four smileys, or five circles on
   a 1-5 question) for 500 ms. Score per tile = mean MBON07 rate minus mean MBON11
   rate, minus the baseline. MBON07 (alpha1) drives approach in the fly, MBON11
   (gamma1pedc) drives avoidance. These are the mushroom body output cells that
   dopamine rewires when a fly learns; here nothing teaches it, so this is innate
   preference.
5. Step 4 runs five times with small fixed pixel shifts and brightness changes on the
   tiles. The simulator is deterministic, real neurons are not; the jitter stands in
   for trial-to-trial noise. Highest mean score over the five runs wins. The `n/5`
   after the answer is how many runs agreed with it. An exact tie in the mean is
   "Hoppa över". All five agreeing flips the "Extra viktigt för mig" toggle.
6. Snapshot is restored and the fly sees the winning tile once more, so the choice
   carries into the next question.

No learning. Weights are frozen. No randomness. Same screenshots in the same order
give the same answers every run.

## Run it

[uv](https://docs.astral.sh/uv/), a C++ compiler, ~16 GB RAM. `prepare.py` downloads
about 1 GB from Janelia and compiles the graph.

```sh
uv run prepare.py
uv run valkompass.py
```

Screenshots go in `screenshots/` as `NN-anything.png`, numeric order. A 1-5 scale
question is `NNs-anything.png`, the `s` picks `options/scale/` instead of
`options/smiley/`. Output is one line per question: filename, score per tile,
answer. Click the answers into SVT yourself.

## Credits

The simulator, connectome import, visual mapping and dopamine circuit were written by
[nftechie](https://github.com/nftechie) for [DOOMFLY](https://github.com/nftechie/doomfly)
and [Stonkfly](https://github.com/nftechie/stonkfly), MIT. This repo only points the fly
at a different screen. Connectome data from the MaleCNS collaboration, CC BY 4.0.
See `THIRD_PARTY.md`.
