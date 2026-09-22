# Experiment 8 — can a different eye fix the timing?

**Short answer: the diagnosis is confirmed, the timing can be halved, and it
buys almost nothing. Mean |peak lag| falls from 365 ms to 185 ms across
networks, the real connectome's untrained play improves from 0.727 to 0.808
lane-correct and 0.196 to 0.246 accuracy — and the controls improve at least as
much, so the comparison gets *weaker*: 1/12 → 2/12 on lane-correct,
3/12 → 5/12 on accuracy. The front end that achieves it also costs two
assumptions I am not willing to adopt as the default. Honest negative, and the
fourth in a row.**

Raw numbers: `results/e8_encoder.json`, `results/e8.log`.

## Why this was run

Experiment 6 found that on every network measured, the four motor channels peak
200–600 ms *before* the note reaches the judgment line, while osu!mania's
windows are tens of milliseconds wide. Only about one lane in four crosses
threshold while a press would still be judged. That is a property of the
encoder and the game rather than of any connectome, and it caps what any
threshold policy on these channels can score — so it was the largest available
improvement to how well the fly actually plays, independent of the
real-vs-random question.

## The mechanism, measured

Total photoreceptor drive during one note's descent is essentially **flat**:
summed drive runs 100 → 230 over 800 ms and never approaches zero. The only
change the network ever sees is the step when the note spawns. Every response
is therefore onset-locked. This is the diagnosis stated precisely, and it
explains why the obvious fix fails.

## What did not work

**Adaptation** — the transient front end already built into `Encoder` and
switched off by default. Twenty-nine configurations (τ ∈ {30…500} ms,
gain ∈ {1…8}, plus a pure-transient variant). Mean peak lag stayed between
−271 and −299 ms, i.e. indistinguishable from the −284 ms baseline, and the
on-time count never exceeded 1 of 4. In play it made things worse
(lane-correct 0.727 → 0.560).

The reason is worth recording: a moving point already produces a local
transient at each photoreceptor, so a per-pixel high-pass adds gain but no new
*global* timing information. The aggregate drive the network integrates is
still flat.

**A Gaussian elevation band** at the judgment line fixed the timing (+40 to
−5 ms) but starved the network — three of four channels then never crossed any
threshold in the grid.

**Refitting the normaliser through the gate** made everything worse
(shared band −0.82 → −1.7…−3.5), because gating the calibration ensemble
shrinks some channels' spread and inflates their z scale. The normaliser stays
fitted on the ungated ensemble for every front end.

## What worked, and what it costs

A **ventral gate plus loom**: every photoreceptor's drive multiplied by a fixed
sigmoid that passes light below ≈ 0° elevation and blocks it above, and each
note's amplitude growing as `1 + 8·progress²`.

| front end | mean peak lag | real lane-correct | real accuracy |
|---|---|---|---|
| static (default) | −284 ms | 0.727 | 0.196 |
| adaptation τ120 g2 | −284 ms | 0.560 | 0.200 |
| loom only | −115 ms | 0.500 | 0.117 |
| ventral gate only | −8 ms | 0.450 | 0.150 |
| **gate + loom** | **−62 ms** | **0.808** | **0.246** |

Real connectome vs 12 rewired controls, current fair protocol (band wiring,
θ swept, every network at its own best, press-count guard):

| | real | rewired ×12 | n ≥ real | p |
|---|---|---|---|---|
| lane-correct, static | 0.727 | 0.462 ± 0.163 | 1/12 | 0.154 |
| lane-correct, gate + loom | 0.808 | 0.528 ± 0.325 | 2/12 | 0.231 |
| accuracy, static | 0.196 | 0.174 ± 0.088 | 3/12 | 0.308 |
| accuracy, gate + loom | 0.246 | 0.203 ± 0.194 | 5/12 | 0.462 |

**I am not adopting this as the default**, and the two reasons are different in
kind:

1. **The ventral gate says the fly only sees the bottom third of the
   playfield.** Nothing in this dataset supports that. A ventral acute zone is
   the nearest real phenomenon, but nothing puts it at 0° with a 2° edge. It is
   a receptive-field restriction chosen because it works.
2. **The loom changes the game, not the fly.** osu!mania sprites are a constant
   size; making notes grow ×9 on approach is a modification of the display.

Both remain available as declared, off-by-default variants in `encoder.py` —
they are useful as a diagnostic, and the diagnostic is the result.

## The real ceiling

No front end got the **spread** of the four channels' peak times below ~190 ms.
The channels have latencies of 200–1000 ms that differ from each other by
100–400 ms, and that is the network's own dynamics, not the stimulus: a front
end can shift the mean but not the spread. With one shared threshold and a
"300" window of ±64 ms, the on-time count is capped at 1–2 of 4 whatever the
eye does.

**So the lever is in the readout, not the eye.** Per-key delays, or a channel
combination chosen for matched latency, is where a successor should go. Note
that experiment 6 found the *spread* is also the strongest correlate of play
across random graphs (ρ = +0.57) — staggered peaks let one key win alone under
a shared threshold. Those two facts pull in opposite directions and reconciling
them is the interesting problem: spread helps lane *identity* and hurts
*timing*.

## Honest caveats

- **The gate+loom comparison is 12 controls, the others 4.** Only the 12-control
  row should be read as a comparison.
- **Control variance roughly doubles under gate+loom** (sd 0.163 → 0.325 on
  lane-correct), which is most of why the rank statistics move. A front end
  that makes every network more erratic is not obviously an improvement even
  where the mean rises.
- **Under gate-only, one control never reached the minimum press count at any
  threshold**, so its score is a fallback rather than a measurement. That row's
  control mean is not trustworthy. No such case arose under gate+loom.
- Default encoder behaviour is unchanged and was verified bit-identical
  against the committed version over 500 static frames (including chords and
  empty frames) and 300 frames of the stateful adaptation path, so nothing
  previously measured is affected.

## What this licenses

- Keep the static encoder as the default. Treat gate and loom as diagnostics.
- State the timing ceiling as a property of the model as a whole: **the
  channels' latency spread is set by network dynamics and no sensory front end
  removes it.**
- Put the next timing effort in the controller — per-key delays are 4 more
  parameters and would be the first change to the policy's *form* rather than
  its numbers.
- Add this to the tally: a better procedure narrowed the gap again.
