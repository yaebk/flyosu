# Experiment 18 — capability: the fly now plays about three times harder

**Short answer: the chord wall was never a capacity limit, it was a diet. The
readout had only ever been fitted on stage-3 charts at 600 ms, so every other
number in experiment 5's curriculum table was a transfer figure. Fit the same
kind of readout on chords at three densities and, on fresh charts it has never
seen, it scores 0.852 where the old best scored 0.295 at 150 BPM with chords,
0.977 against 0.655 on chords at 600 ms, and a clean 1.000 on the condition the
old one was specialised for. Mean accuracy across eleven conditions goes from
0.430 to 0.763. The practical ceiling moves from roughly 1.7 notes per second to
roughly 2.5–2.9.**

**This document is engineering, not a comparison.** Real connectome only, no
controls, no p-values, nothing here bears on whether the real wiring beats
rewired wiring. `experiments/e18_capability.py` says the same at the top so that
no number from it leaks into a registered comparison.

Raw numbers: `results/e18_capability*.json`, `results/e18_*.log`.

## The recipe

| | experiment 5 | experiment 18 |
|---|---|---|
| training charts | 4 × stage 3 @ 600 ms | **16 × stage 4 @ 600 / 450 / 350 ms** |
| features | pca16 | **pca32** |
| parameters | 68 | 132 |
| connectome | frozen | frozen |

Three changes, in order of how much they mattered: **train on chords**, **vary
the density while doing it**, and give it more data and more capacity.

## Validation — fresh charts, 200 notes per condition

Selected on a seed-999 battery, then re-scored on seed 4242 with ten charts per
condition, because the arm was chosen by reading the battery and those numbers
are selection-optimistic in exactly the way experiments 13 and 16 warned about.
**These are the numbers to quote.**

| condition | notes/s | **experiment 18** | experiment 5's diet | e5 as published |
|---|---|---|---|---|
| stage 3 @ 600 | 1.7 | **1.000** | 0.863 | 0.917 |
| stage 4 chords @ 600 | 1.7 | **0.977** | 0.655 | 0.506 |
| stage 5 varied tempo | 1.7 | **0.961** | 0.613 | 0.608 |
| stage 3 @ 450 | 2.2 | **0.948** | 0.442 | — |
| stage 3 @ 350 | 2.9 | **0.851** | 0.404 | — |
| stage 4 chords @ 400 | 2.5 | **0.852** | 0.295 | 0.286 |
| stage 3 @ 300 | 3.3 | 0.682 | 0.422 | — |
| stage 4 chords @ 300 | 3.3 | 0.584 | 0.281 | — |
| stage 3 @ 250 | 4.0 | 0.572 | 0.357 | — |
| stage 4 chords @ 250 | 4.0 | 0.529 | 0.247 | — |
| stage 4 chords @ 200 | 5.0 | 0.432 | 0.146 | — |
| **mean** | | **0.763** | 0.430 | — |

It is ahead on all eleven, by 0.14 to 0.51. The old readout's 0.917 comes back
at 0.863 on ten fresh charts, so that figure was mildly optimistic too — the
same pattern this project has found a dozen times, and worth recording rather
than quietly dropping.

## What the arms showed on the way

Eleven training compositions, same solver, same held-out battery:

| arm | training diet | battery mean |
|---|---|---|
| `s3_600` | stage 3 @ 600, 8 charts | 0.521 |
| `s4_450` | stage 4 @ 450, 8 charts | 0.390 |
| `s4_dense` | stage 4 @ 600/450/350, 8 charts | 0.549 |
| `mixed_fast` | stages 3/4/5, 8 charts | 0.575 |
| `mixed` | stages 3/4/5, 8 charts | 0.592 |
| `s4_pca32` | stage 4 @ 600, pca32 | 0.606 |
| `s4_600` | stage 4 @ 600, 8 charts | 0.655 |
| `s4_x16` | stage 4 @ 600, 16 charts | 0.675 |
| `s4_x24_pca32` | stage 4 @ 600, 24 charts, pca32 | 0.683 |
| `s4_x16_pca32` | stage 4 @ 600, 16 charts, pca32 | 0.684 |
| **`s4_x16_var`** | **stage 4 @ 600/450/350, 16 charts, pca32** | **0.871** |

Three things worth keeping:

**Mixing *stages* is the wrong kind of variety, and it cost the obvious arms
their advantage.** `mixed` and `mixed_fast` both underperform plain `s4_600`.
Stage 4 already generates single notes — chords are only 30% of its events — so
it is a *superset* of stage 3, and adding stage-3 charts just dilutes the chords
without adding anything the readout had not already seen. Variety in **density**
is what pays; variety in stage is what does not.

**Capacity and data help in different places and compose.** `pca32` at 8 charts
is superb right next to its training condition (0.983 on chords at 600 ms) and
brittle away from it (0.283 at 2.9 notes/s); 16 charts at `pca16` is even but
never spectacular. Together they are better than either, and adding the density
variety on top is what produces the jump from 0.684 to 0.871.

**Training at a single fast density is actively harmful.** `s4_450` is the worst
arm in the set at 0.390, below even experiment 5's diet, and its hit rate on
600 ms charts collapses to 0.267 — it learns an operating point that does not
transfer *down* in density any better than the old one transferred up. Density
variety works; density substitution does not.

## Where the new wall is

Accuracy stays above 0.95 to about 2.2 notes/s, above 0.85 to about 2.9, and
then falls off steeply: 0.68 at 3.3, 0.57 at 4.0, 0.43 at 5.0. Below roughly
0.85 the hit rate is what goes — 0.93 at 2.9 notes/s, 0.74 at 3.3, 0.68 at 5.0 —
so it is missing notes rather than mistiming them or pressing the wrong key.

**The next thing to test is the 150 ms refractory in `controller.py`.** It is a
declared constant that makes two notes in the same lane closer than 150 ms
physically unpressable, and at 4–5 notes/s across four lanes that is now
plausibly binding. It has never been varied. Whether the remaining wall is the
refractory, the channels' temporal resolution, or the readout is an open and
cheap question.

## In osu!mania terms

Roughly: from a comfortable **1.5–2★** to a comfortable **3★**. Chords at 150 BPM
now score 0.85 where they used to score 0.29, and stage 5's irregular rhythm —
the closest thing here to a real map's phrasing — is at 0.961.

The caveats from before still hold and none of them is addressed by this
experiment: these are synthetic charts, no real `.osu` beatmap has ever been
played, hold notes are judged on the head only, and the scroll speed is fixed at
an 800 ms approach.

## Honest caveats

- **The arm was chosen on the seed-999 battery.** The validation table above is
  a fresh seed with ten charts a condition and is the honest number; the 0.871
  battery mean is not.
- One connectome, one noise level, one threshold, one OD.
- `s4_200` and `s4_250` are extrapolations past anything the training diet
  contained (its fastest chart is 350 ms), so the falloff there measures
  transfer, not a trained ceiling.
- Nothing here says the *real* connectome is special. The same recipe has not
  been tried on a rewired control, and on this project's record it would
  probably work there too.

## What this licenses

- **Quote 0.852 at 2.5 notes/s with chords as the project's best play**, not
  experiment 5's 0.92, and cite the fresh-seed table rather than the battery.
- Stop describing chord density as the wall. It was the training set.
- When fitting a readout here, use stage 4 at several intervals. Never fit at a
  single fast density, and do not bother mixing stages.
- Vary the refractory next; it is the only untested hard constraint left between
  the current ceiling and 4 notes per second.
