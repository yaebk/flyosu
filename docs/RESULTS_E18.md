# Experiment 18 — capability: neither wall was the network

**Short answer: both of the fly's apparent limits were protocol choices nobody
had registered as choices, and removing them roughly triples what it can play.
The chord wall was a training-set limitation — the readout had only ever been
fitted on single-note charts, so every other entry in experiment 5's curriculum
table was a transfer figure. The density wall was the fixed 800 ms approach
window, the fly's scroll speed, which past three notes a second puts two or
three notes in a lane at once and hands the encoder their superposition. Fit on
chords across four densities *and* shorten the approach to 400 ms, and on fresh
charts it has never seen the fly scores a perfect **1.000 on eight of eleven
conditions**, 0.988 at four notes per second with chords, and 1.000 on jacks it
was never trained for — with **zero stray presses on every condition**. Mean
accuracy across eleven conditions goes from 0.430 to **0.972**. The practical
ceiling moves from roughly 1.7 notes per second to about 4.**

**This document is engineering, not a comparison.** Real connectome only, no
controls, no p-values, nothing here bears on whether the real wiring beats
rewired wiring. `experiments/e18_capability.py` says the same at the top so that
no number from it leaks into a registered comparison.

Raw numbers: `results/e18_capability*.json`, `results/e18_*.log`.

## The recipe

| | experiment 5 | experiment 18 |
|---|---|---|
| training charts | 4 × stage 3 @ 600 ms | **16 × stage 4 @ 600 / 450 / 350 / 250 ms** |
| approach window | 800 ms | **400 ms** |
| features | pca16 | **pca32** |
| parameters | 68 | 132 |
| connectome | frozen | frozen |

Four changes, in order of how much they mattered: **shorten the approach
window**, **train on chords**, **vary the density while doing it**, and give it
more data and more capacity.

## Validation — fresh charts, 200 notes per condition

Selected on a seed-999 battery, then re-scored on seed 4242 with ten charts per
condition, because the arm was chosen by reading the battery and those numbers
are selection-optimistic in exactly the way experiments 13 and 16 warned about.
**These are the numbers to quote.**

| condition | notes/s | **final** | 350 ms diet | 800 ms scroll | e5's diet | e5 published |
|---|---|---|---|---|---|---|
| stage 3 @ 600 | 1.7 | **1.000** | 1.000 | 1.000 | 0.863 | 0.917 |
| stage 4 chords @ 600 | 1.7 | **1.000** | 1.000 | 0.977 | 0.655 | 0.506 |
| stage 5 varied tempo | 1.7 | **1.000** | 1.000 | 0.961 | 0.613 | 0.608 |
| stage 3 @ 450 | 2.2 | **1.000** | 1.000 | 0.948 | 0.442 | — |
| stage 3 @ 350 | 2.9 | **1.000** | 1.000 | 0.851 | 0.404 | — |
| stage 4 chords @ 400 | 2.5 | **1.000** | 1.000 | 0.852 | 0.295 | 0.286 |
| stage 3 @ 300 | 3.3 | **1.000** | 0.985 | 0.682 | 0.422 | — |
| stage 4 chords @ 300 | 3.3 | **1.000** | 0.980 | 0.584 | 0.281 | — |
| stage 3 @ 250 | 4.0 | **0.983** | 0.925 | 0.572 | 0.357 | — |
| stage 4 chords @ 250 | 4.0 | **0.988** | 0.900 | 0.529 | 0.247 | — |
| stage 4 chords @ 200 | 5.0 | **0.718** | 0.659 | 0.432 | 0.146 | — |
| **mean** | | **0.972** | 0.950 | 0.763 | 0.430 | — |
| *jacks @ 450* | *2.2* | ***1.000*** | — | — | — | — |
| *jacks @ 300* | *3.3* | ***1.000*** | — | — | — | — |
| *jacks @ 250* | *4.0* | ***0.895*** | — | — | — | — |

The "350 ms diet" column is the same recipe whose fastest training chart is
350 ms. Adding a 250 ms chart to it is what lifts the top end: 4 notes/s with
chords 0.900 → **0.988**. The jack rows are italicised because they use a chart
generator (stage 6) that did not exist when the other columns were measured.

Ahead on all eleven, and **zero stray presses on every condition** — not
rounded to zero, none at all. The old readout's published 0.917 comes back at
0.863 on ten fresh charts, so that figure was mildly optimistic too, the same
pattern this project has found a dozen times and worth recording rather than
quietly dropping.

**400 ms is a real optimum, not the best of a coarse grid.** The window was
swept at 800, 600, 450, 400, 350 and 300 ms on the same diet, and 400 wins:
at 4 notes/s with chords it scores 0.900 against 0.678 at 450 ms, 0.652 at
350 ms and 0.725 at 300 ms. Too long and the notes superpose; too short and
there is not enough approach left for the network's own latency, since the
channels peak 200–600 ms before the note (experiment 8).

The one place the ranking inverts is the densest condition: at 5 notes/s a
300 ms approach beats a 400 ms one, 0.790 against 0.718. That fits the same
story — the denser the chart, the more a shorter window pays, right up until it
starts eating the latency.

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

## Where the wall was, and where it is now

At the original 800 ms approach the ceiling was clear: above 0.95 only to about
2.2 notes/s, above 0.85 to 2.9, then 0.68 at 3.3, 0.57 at 4.0, 0.43 at 5.0. What
went in every case was the **hit rate** — 0.74 at 3.3 notes/s, 0.68 at 5.0 — so
the fly was missing notes rather than mistiming them or pressing wrong keys,
which is the signature of not being able to see them rather than of bad control.

Two candidates were tested. The second one was the answer.

### It is not the refractory — that was tested and it is not

The obvious suspect was the 150 ms refractory in `controller.py`, a declared
constant that makes two notes in the same lane closer than 150 ms physically
unpressable. This document previously predicted it was "plausibly binding" at
4–5 notes/s. **It is not, and the prediction was wrong.** Refitting the winning
arm at 100, 75 and 50 ms gives results *bit-identical* to 150 ms on all seven
battery conditions — not close, identical.

The reason is a property of the charts rather than of the fly. `stage_chart`
spreads notes over four lanes at a uniform interval, so the minimum gap between
two notes *in the same lane* is the full interval: 600 ms at `s4_600`, and still
200 ms at the most extreme condition tested. The refractory has never had an
opportunity to bind. It would bind on a real beatmap containing jacks, which is
a reason to keep the constraint in mind for step 12 and not a reason to change
it now.

### It was the approach window — the fly's scroll speed

The 800 ms approach window is how long a note is visible before its hit time.
At 3.3 notes/s a lane holds two or three notes at once, and the encoder hands
the network their superposition, so the channel cannot resolve which one is at
the judgment line. That is precisely what a human fixes by raising scroll speed,
and nobody had ever varied it — it had been 800 ms since experiment 1.

Refitting at 400 ms is the single largest improvement in this experiment:
chords at 150 BPM go from 0.852 to **1.000**, chords at 200 BPM from 0.584 to
**0.980**, and four notes a second with chords from 0.529 to **0.900**. Strays
go to exactly zero everywhere. The effect is not monotone — 300 ms is worse than
400 ms past three notes a second — so there is a real optimum, set by the
network's own 200–600 ms channel latency needing room inside the approach.

**This is a free parameter of the environment, not of the fly**, and it is the
one nobody thought to question. Every density result this project has ever
reported was measured at one arbitrary scroll speed.

At 400 ms the new ceiling is about **4 notes per second** — 0.925 single notes
and 0.900 with chords — falling to 0.659 at 5. The hit rate still tracks the
accuracy exactly (0.91 at 4 notes/s, 0.68 at 5), so whatever binds at five notes
a second is still a seeing problem rather than a control one, and the training
diet's fastest chart is 350 ms, so part of that is simply extrapolation.

## Jacks: easy, and you must not train for them

Stage 6 was added for this experiment because stages 1–5 never generate a jack —
they spread notes over four lanes at a uniform interval, so two notes are never
in the same lane close together. It asks a different question from the rest of
the curriculum: not whether the four channels can be told apart, but whether
*one* channel can resolve two notes in succession. It is also the only pattern
where the refractory could bind.

Three arms, all validated on fresh charts:

| | jacks @ 2.2/s | jacks @ 3.3/s | jacks @ 4.0/s | chords @ 4.0/s | chords @ 5.0/s |
|---|---|---|---|---|---|
| `fast_a400` — **never saw a jack** | **1.000** | **1.000** | **0.895** | **0.988** | **0.718** |
| `jack_a400` — trained on jacks | 1.000 | 1.000 | 0.815 | 0.905 | 0.552 |
| `jack_r50` — jacks, 50 ms refractory | 1.000 | 1.000 | 0.815 | 0.905 | 0.569 |

**Jacks are not hard for this fly.** The arm that has never seen one plays them
at 1.000 up to 3.3 notes/s, as well as it plays anything else at that density.
The worry that a single channel could not fire twice in quick succession was
unfounded at every rate it can actually play.

**Training on jacks makes it worse at jacks.** `jack_a400` is below `fast_a400`
on every condition including the jacks it was trained for, 0.815 against 0.895.
The reason is the same lesson as round 1, now with a second instance: its diet
spent two of its four slots on stage-6 charts and so dropped the 250 ms chord
chart, and **density training is worth more than pattern familiarity**. Adding a
pattern to the diet is not free — it displaces something, and here the thing it
displaced mattered more.

### The refractory, finally pinned down

`jack_r50` matches `jack_a400` to three decimals on every jack condition at
250 ms and slower, because a jack at 4 notes/s still leaves 250 ms between two
notes in a lane — outside the 150 ms dead time. So the question was pushed past
the point where it *must* bind: jacks at 150 ms, exactly the refractory, and at
120 ms, inside it. Best arm, refractory 150 ms against 50 ms:

| jacks at | notes/s | same-lane gap | refractory 150 ms | refractory 50 ms | gain |
|---|---|---|---|---|---|
| 450 ms | 2.2 | 450 ms | 1.000 | 1.000 | +0.000 |
| 300 ms | 3.3 | 300 ms | 1.000 | 1.000 | +0.000 |
| 250 ms | 4.0 | 250 ms | 0.895 | 0.895 | +0.000 |
| **150 ms** | 6.7 | **150 ms** | 0.431 | 0.467 | **+0.036** |
| **120 ms** | 8.3 | **120 ms** | 0.429 | 0.500 | **+0.071** |

**Exactly zero above the dead time, and nonzero at and below it** — the effect
appears precisely where the structural argument says it must and grows as the
gap goes further inside. That is as clean a confirmation as this project has
produced, and it settles the question in both directions: the refractory is a
real constraint, and it is **not a practical one**, because the only charts
where it binds are ones the fly plays at 0.43–0.50 for unrelated reasons.

My earlier caveat that it "would bind on a real beatmap with jacks" is now
precise: it binds on 1/4 jacks above roughly 100 BPM, which is out of reach for
other reasons. Do not spend effort tuning it.

## Rounds 8 and 9: the last density gap, and holds

**Adding a 200 ms chart to the diet closes the density ceiling.** Five events a
second was the one weak point left, at 0.718, and it was extrapolation -- the
diet's fastest chart was 250 ms. With a 200 ms chart added:

| condition | fast_a400 | fastest_a400 | **fastest_a300** |
|---|---|---|---|
| chords @ 5.0/s | 0.718 | 0.908 | **0.948** |
| chords @ 4.0/s | 0.988 | 1.000 | **1.000** |
| jacks @ 4.0/s | 0.895 | 1.000 | **1.000** |
| mean, non-hold | 0.968 | 0.993 | **0.996** |

`fastest_a300` scores a clean 1.000 on nine of the ten non-hold conditions.
**The synthetic curriculum is saturated** -- there is no headroom left in it, and
further capability work has to come from real maps.

**Holds, by contrast, are immovable, and that is the point.**

| | never trained on holds | trained on holds |
|---|---|---|
| holds @ 600 ms | 0.630 | **0.630** |
| holds @ 400 ms | 0.630 | **0.630** |

Training on hold notes changes the score by *nothing*. Stage 7 is 40% holds, so
0.630 is very close to what you get if every ordinary note scores 1.000 and
**every hold scores 0** -- the fly presses the head correctly and then misses the
tail, essentially always.

This is the third independent line of evidence for the same cause, and together
they are conclusive. Experiment 20's regression on real maps puts the cost of a
fully-held chart at 0.432 of accuracy. Holds here score about zero. And training
on them does not help at all -- which is what you expect when the information is
not in the input rather than when the policy is merely untuned. `Encoder.targets`
draws one point per visible note, so a hold is rendered as its head and nothing
else. **The fly cannot see that a note is a hold**, and no readout fitted on top
of that input can learn when to let go.

Note also that `hold_a400` is *worse* everywhere else (0.879 against 0.996),
which is the displacement lesson for the third time: its stage-7 charts came out
of the density budget, and bought nothing.

## In osu!mania terms

Roughly: from a comfortable **1.5–2★** to about **4★**. Chords at 150 BPM now
score a perfect 1.000 where they used to score 0.29; four notes a second with
chords scores 0.988; jacks score 1.000 up to 3.3 notes a second; and stage 5's
irregular rhythm — the closest thing here to a real map's phrasing — is at
1.000. The fall-off is at five notes a second (0.718), which is where a 4K map
starts being genuinely hard for people.

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
  transfer, not a trained ceiling. Training at those densities has not been
  tried and would probably lift them further.
- The approach window was swept at three values (800, 600, 400, 300) on one
  training diet. 400 ms is the best of those, not a located optimum.
- Nothing here says the *real* connectome is special. The same recipe has not
  been tried on a rewired control, and on this project's record it would
  probably work there too.

## What this licenses

- **Quote 1.000 up to 3.3 notes/s with chords, and 0.988 at 4 notes/s, as the
  project's best play** — not experiment 5's 0.92 — and cite the fresh-seed
  table rather than the battery.
- **Do not add a pattern to the training diet without asking what it displaces.**
  Training on jacks made the fly worse at jacks, because the slots it took came
  out of density training, which was worth more.
- **Report the approach window alongside any density result.** Every such number
  recorded before this experiment was measured at 800 ms, which is now known to
  be the wrong value above three notes a second.
- Stop describing chord density as the wall. It was the training set.
- When fitting a readout here, use stage 4 at several intervals. Never fit at a
  single fast density, and do not bother mixing stages.
- **Do not blame the refractory for the density ceiling.** It was varied from
  150 ms down to 50 ms and changes nothing, because uniform-interval stage
  charts never put two notes in one lane closer than the interval. It remains a
  real constraint for any beatmap with jacks.
- Try the approach window next. 800 ms puts two or three notes in a lane at once
  past 3 notes/s, which is the superposition a real player fixes with scroll
  speed.
