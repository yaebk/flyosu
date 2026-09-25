# Experiment 18 — capability on synthetic charts

**This is the capability thread: real connectome only, no controls, no
p-values.** A number here says nothing about whether the real wiring beats
rewired wiring. Experiment 21 applied the round-23 recipe to 20 rewired
controls, and 19 of them played better than the real connectome
(`RESULTS_E21.md`). The comparison thread is `docs/CLAIMS.md` and the
pre-registered experiments.

Real-map results, which are what the synthetic work is for, are in
[`RESULTS_E20.md`](RESULTS_E20.md).

## How it is measured

The connectome is frozen. The only fitted part is a ridge readout from a
principal-component projection of the descending neurons' activity to four key
drives, plus a per-lane timing offset and release level chosen on the training
charts. Arms are defined in `experiments/e18_capability.py` (`ARMS`) and
validated on `DEEP`: fresh charts (seed 4242), ten charts of twenty notes per
condition, 26 conditions from single notes at 1.7 events/s to chords at 10.
Results: `results/e18_capability_validate_<arm>.json`.

Run: `ARM=<arm> python experiments/e18_capability.py validate`; `ONLY=a,b`
scores just those conditions and merges them into an existing file.

Later rounds compare arms on this validation battery itself, so the synthetic
numbers of the chosen arm are selection-optimistic. The held-out real
maps in `RESULTS_E20.md` are the unbiased check.

## Current recipe: round 15, `fast_sm20_k48`

| | experiment 5 | now |
|---|---|---|
| training charts | 4 × single notes @ 600 ms | 36 × chords @ 600/450/350/250/200/150/125 ms + holds @ 600/400 ms |
| approach window (scroll speed) | 800 ms | 250 ms |
| refractory | 150 ms | 100 ms |
| drive smoothing | 40 ms | 20 ms |
| features | 16 PCs | 48 PCs of the calibration activity |
| hold charts recorded with | — | `HoldOracle` (a scripted perfect hold player) |
| release | drive falls through 0 | per-lane release level |
| fitted parameters | 68 | 196 |

## What it plays

| pattern | events/s | accuracy |
|---|---|---|
| single notes and chords, 11 conditions | 1.7 – 5.0 | **1.000** on all |
| chords | 6.7 / 8.0 / 10.0 | 0.973 / 0.810 / 0.713 |
| jacks (same lane repeated) | 2.2 – 4.0 / 6.7 / 8.3 | 1.000 / 0.988 / 0.627 |
| holds (stage 7) | 1.7 / 2.5 / 3.3 | 0.982 / 0.950 / 0.886 |
| holds followed in their own lane (stage 8) | 2.5 / 3.3 | 0.925 / 0.787 |
| 1.2 s holds | 0.7 | 0.745 |
| 80 % chords | 2.5 | 1.000 |
| **mean, 26 conditions** | | **0.938** |

Stray presses are zero everywhere except three hold conditions, at 0.01 per
note. At 8 to 10 events/s accuracy is within 0.01 of hit rate: the fly does not
mistime dense notes, it fails to press them, because two pulses in one lane
merge.

## Rounds

Effects are validation accuracy. "Dense" is the mean of chords at 6.7, 8 and
10 events/s; "holds" the three stage-7 conditions; "jacks" the five stage-6
conditions; "mean" is over every condition the arm was scored on.

| round | change | effect | verdict |
|---|---|---|---|
| 1–3 | fit on chords at several densities (was single notes only), 16 charts, 32 PCs | 11-condition mean 0.43 → 0.76 at 800 ms | kept: the chord wall was the training set |
| 4 | refractory 150 → 50 ms | bit-identical on uniform charts | no effect there (but see round 13) |
| 5–6 | approach 800 → 400 ms | 0.763 → 0.950; chords @ 4/s 0.529 → 0.900 | kept: the density wall was scroll speed |
| 7 | jack charts in the diet | chords @ 5/s 0.718 → 0.552 | worse: they displaced density charts |
| 8 | 200 ms chord chart in the diet, 300 ms approach | chords @ 5/s 0.718 → 0.948; 11-condition mean 0.995 | kept |
| 9 | hold charts, holds drawn as a head only | holds 0.630 either way | holds were invisible |
| 9b | draw hold bodies (`9b6b39e`), sustain through the body, 130 ms tail lead (`c4442cf`) | holds @ 600 ms 0.630 → 0.821; chords @ 5/s fall to 0.328 | holds learnable, but they displace density |
| 10 | one 28-chart diet: full density ladder + holds (`491ce15`) | density 0.994, holds 0.779, 19-condition mean 0.904 | kept: the chart budget was the limit; 48 PCs no gain (0.900) |
| 11 | fit's judge releases keys (bug fix) + release levels | holds 0.779 → 0.727 / 0.750 | exposed the recording bug below |
| 12 | record holds with `HoldOracle` (`bddd1c9`) | holds 0.841; with release levels 0.858, 19-condition mean 0.922 | kept. Stage-8 charts in the diet: no clear gain. Grid hold rendering: worse (holds 0.836) |
| 13 | 150/125 ms chord charts; approach 300 → 250 ms; refractory 150 → 100 ms (`da4cd91`) | dense 0.683 → 0.699 → 0.736; holds 0.862 → 0.925; jacks @ 150 ms 0.504 → 0.785; 24-condition 0.913 | all kept. Dense random chords do put notes in one lane inside 150 ms |
| 14 | approach 200 ms; refractory 75 ms; smoothing 40 → 20 ms; 48 PCs; target width 80 → 50 ms (`307ab8a`) | 0.912; 0.914; **0.929**; **0.925**; 0.915 | smoothing and 48 PCs kept; the rest tie or trade |
| 15 | 20 ms smoothing + 48 PCs (`d686223`) | **0.943**; jacks @ 150 ms 0.988; chords @ 6.7/s 0.973 | **current base**. 10 ms + 48 PCs also 0.943; 64 PCs was a bug |
| 16 | PCA fitted on recorded training activity instead of calibration | dense 0.832 → 0.859, holds 0.939 → 0.763; 0.920 | worse |
| 17 | long-hold (0.8, 1.2 s) and chord-heavy charts (`3686448`) | 1.2 s holds 0.745 → 1.000; dense 0.832 → 0.798 | chord-heavy charts do nothing (baseline already 1.000) |
| 18 | long-hold charts only; 56 PCs (`05b5d6a`) | 26-condition 0.942 vs 0.938; 56 PCs 0.917 | a trade; lost on the tuning maps (0.759 vs 0.770), not adopted |
| 19 | reward MAX over 300 in the timing search, at 305/300 and +10 % (`a9ee5d5`) | MAX share 29 % / 81 %; mean 0.932 / 0.920 vs 0.938 | a trade, not adopted; setting kept (`max_bonus`) |
| 20 | lanes at ±30/±90° and ±40/±120° instead of ±20/±60° (`6f3c32e`) | 11-condition mean 0.898 / 0.889 vs 0.929 | worse; the lanes share only ~30 photoreceptors already |
| 21 | jack charts at 200/150/120 ms in the diet, 100 and 75 ms refractory | with 75 ms: all 26 0.938 → 0.945; jacks @ 120 ms 0.627 → 0.702, chords @ 10/s 0.713 → 0.768; holds 0.891 → 0.874 | best on synthetic, **rejected on real maps**: tuning-map mean 0.770 → 0.741, worse on all 17, taps 0.900 → 0.874 and holds 0.518 → 0.483; the tuning maps hold only 69 fast jacks, so its one gain barely registers there |
| 22 | tail lead 130 → 80 / 40 ms | synthetic holds unchanged (0.891, 0.887, 0.878); tuning maps 0.770 → 0.751 at 80 ms, holds 0.518 → 0.533 but taps 0.900 → 0.857, better on 1 of 17 | **rejected**: fixes a little of what it aimed at and costs taps and chords, like round 21 |
| 23 | fit on real tuning-map clips as well (`experiments/e20_realfit.py`) | not scored on this battery; decided on unseen tuning-map segments: 0.772 → 0.815 | **kept**, see `RESULTS_E20.md`. Held-out 0.876 vs 0.862, better on 22 of 30 |

## Bugs found on the way

- **The recorder never showed a held hold's body.** The fit learns from
  recordings made with a controller that never presses, so every hold was
  missed and left the screen 164 ms after its head: on a 480 ms hold the last
  316 ms of body, the part that cues the release, was never seen. `HoldOracle`
  presses and lifts each hold exactly on time while recording and touches
  nothing else, so recordings still do not depend on the policy being fitted.
  Charts without holds record bit-identically. Opt-in, so old results
  reproduce. (`bddd1c9`)
- **The fit's offline judge never released keys**, so every training hold was
  scored as never let go and the timing search could not see releases. It now
  releases as live play does. No chart without holds changes, including every
  registered experiment. (`c83253d`)
- **`PopulationProjection` capped k at the number of singular values, not the
  rank.** The 61 calibration states have rank 60 after centering, so k = 64
  kept a component at rounding level, z-scoring blew it up, and the arm scored
  0.023. It now refuses k above the rank, with a test. No earlier result used
  k above 48. (`d686223`)

## What carries over

- **Suspect the protocol before the network.** Chords were the training set,
  density was the scroll speed, holds were first the rendering and then the
  recordings. None of the walls so far was the connectome.
- **The training diet is a budget.** Adding a pattern displaces something
  (rounds 7, 9b, 17–18); widening the budget, not dropping a skill, is what
  fixed it in round 10.
- **The refractory binds on dense random chords**, not on uniform charts.
  Round 4's "no effect" was a property of the charts. At 100 ms it no longer
  binds (75 ms changes nothing).
- **When accuracy equals hit rate, look at pulse width.** Dense misses were
  merged same-lane pulses; sharper smoothing and more components fixed them.
- Report the approach window, refractory and smoothing with any density figure.
