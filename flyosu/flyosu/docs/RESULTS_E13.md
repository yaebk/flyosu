# Experiment 13 — the male CNS reversal is the readout, not the connectome

**Short answer: experiment 7's male CNS reversal is an artefact of the
anatomical readout, and removing it makes the real connectome level with its
controls rather than better than them. On the four leg-motor pools the real
network loses 9/10 on the tuning charts and 9/10 again on held-out charts — a
robust disadvantage. On eight principal components of the same 348 neurons it
wins 1/10 on the tuning charts and that advantage **does not survive charts
nothing was re-chosen for**: 6/10, p = 0.636, with its accuracy falling 0.258 →
0.122 while the controls' holds at 0.131 → 0.138. The honest reading is that a
readout preserving lane identity removes a handicap; it does not confer an
advantage.**

Raw numbers: `results/e13_readout_malecns.json`, `results/e13.log`.

## Why this was run

`docs/RESULTS_E7.md` reported that the untrained comparison does not replicate
on the male CNS — it reverses, real 0.067 against controls' 0.237, 9 of 10
beating it. That result was recorded with a warning attached: the real network
was the only one of eleven that never reached the 20-press guard at any
threshold (8 presses over 40 notes against controls' 44–80), so its
lane-correctness was undefined rather than high.

The cause was known in advance and documented in `docs/MALECNS.md`. The male CNS
readout is four *real leg motor pools* grouped by neuromere and side, and those
pools respond to visual input as a common mode: lane identity is present in the
population at 0.98 and almost absent from the pool means. A threshold policy
reading four pools has nothing lane-specific to threshold, so it barely fires.
Experiment 5 made the same point from the other side — eight principal
components of those same 348 neurons reach 0.86 accuracy with a fitted readout.

So the reversal was uninterpretable: it could not distinguish "this connectome
is worse" from "this readout discards the signal". `docs/RESULTS_E7.md` said the
comparison worth running is one whose readout is not known beforehand to destroy
the signal. This is that comparison.

## Design

Four readout arms on **the same networks, the same charts, the same threshold
grid**, so the only thing that varies is what the policy reads:

| arm | what the four features are | declared bits |
|---|---|---|
| `channels` | the four anatomical motor pools, positive only | 4.6 |
| `channels_signed` | the same four, signs allowed | 8.6 |
| `pc4` | 4 features chosen from the top 4 PCs of the 348 neurons | 8.6 |
| `pc8` | 4 features chosen from the top 8 PCs | 14.7 |

The PCs come from an unsupervised fit on the calibration ensemble, which is
label-free. Choosing which feature drives which lane, and with which sign, is
lane knowledge — so it is declared and counted, exactly as the wiring
permutation and the per-key delays are, and it is derived **per network from
that network's own silent probe**, so no control inherits the real network's
mapping.

Protocol otherwise the project's current fair one: threshold swept per network
over 8 values and every network scored at its own best, `MIN_COUNTED = 20` guard
on lane-correctness, 10 rewired controls, `p = (n_ge + 1)/(n + 1)` one-sided.

## Result

Accuracy at each network's own best threshold, malecns, 10 rewired controls:

| arm | real | rewired ×10 | n ≥ real | p | floor |
|---|---|---|---|---|---|
| `channels` | 0.042 | 0.173 ± 0.117 | 9/10 | 0.909 | 0.091 |
| `channels_signed` | 0.067 | 0.116 ± 0.094 | 5/10 | 0.545 | 0.091 |
| `pc4` | 0.100 | 0.125 ± 0.095 | 5/10 | 0.545 | 0.091 |
| **`pc8`** | **0.258** | **0.131 ± 0.077** | **1/10** | **0.182** | 0.091 |

**The direction flips across the table.** Same networks, same charts, same
sweep. On the anatomical pools the real male CNS connectome is beaten by nine of
ten controls; on eight PCs of the very same 348 neurons it beats nine of ten.

This is what `docs/RESULTS_E7.md` predicted, and it settles what that result
meant: **the male CNS reversal is a property of the anatomical readout, not
evidence about the connectome.** The lane information is in the population and
the pooling by neuromere and side is what discards it.

## The held-out charts, which change the answer

Every number above is taken at each network's own best threshold, chosen on the
charts it was scored on. That is optimistic for every network in the same way,
which `docs/RESULTS_E7.md` already flagged. The generalisation test replays each
network's *chosen* policy — its features, its signs, its threshold — on three
charts it has never seen, with nothing re-chosen:

| arm | real sweep → held-out | rewired held-out | n ≥ real | p |
|---|---|---|---|---|
| `channels` | 0.042 → 0.019 | 0.171 ± 0.182 | 9/10 | 0.909 |
| `channels_signed` | 0.067 → 0.186 | 0.096 ± 0.098 | 2/10 | 0.273 |
| `pc4` | 0.100 → 0.044 | 0.131 ± 0.148 | 7/10 | 0.727 |
| **`pc8`** | **0.258 → 0.122** | **0.138 ± 0.091** | **6/10** | **0.636** |

**`pc8`'s advantage does not survive.** The real network's accuracy halves,
0.258 → 0.122, while its controls are unmoved, 0.131 → 0.138. Its 1/10 becomes
6/10 — dead level. So the real network was fitting the threshold to the tuning
charts substantially harder than the controls were, and the apparent advantage
was that overfit rather than better play.

The `channels` disadvantage, by contrast, is robust: 9/10 on the tuning charts
and 9/10 on held-out, with lane-correctness 0.146 against 0.514 and **9 of 9**
controls above it. That one is not an artefact of threshold choice.

So the two halves of the story are not symmetric, and only one of them holds:
**removing the anatomical pooling removes a real handicap, and puts the real
network level with its controls. It does not put it ahead.**

## What this does not show

**It does not show that the real male CNS connectome beats its controls.**
The held-out table settles that directly — `pc8` goes to 6/10, p = 0.636. Even
on the tuning charts `pc8` sat at p = 0.182, which is not significant, and it
*cannot* be made significant by this design: the per-arm floor is 0.091, so even a perfect 0/10
would only reach 0.091, and with four arms on the same networks the
Bonferroni-corrected floor is **0.364**. Four readouts is four chances at a low
p-value, and the arm that wins is the one that would be quoted. The correction
is reported in the script's own output rather than left to the reader.

Experiment 14 is the direct precedent and it is worth taking seriously here: a
claim at 1/20, p = 0.095 went to 4/40, p = 0.122 with **no procedural change and
no movement in the real network's value** — twenty more controls were the whole
difference. `pc8` was at 1/10, a weaker position than the claim experiment 14
dissolved, and it did not even need more controls: three unseen charts were
enough.

**The arms are not comparable to each other.** `pc8` declares 14.7 bits of lane
knowledge against `channels`' 4.6 — it picks 4 features out of 8 with signs,
where `channels` picks a permutation of 4. So "pc8 plays better than channels"
is partly a statement about how much the policy was told. That confound is
symmetric across networks, so it does not touch the real-vs-control comparison
*within* an arm, which is the comparison this experiment makes. It does mean the
table's rows must not be read against each other as a ranking of readouts.

## The press guard fired again, and is reported

Three network/arm combinations never reach 20 counted presses at any threshold:
**real / `pc4`, rewired #7 / `pc4`, rewired #7 / `pc8`**. Lane-correctness is
undefined there — it is a ratio over presses landing near a note — and is
printed as `-` rather than as a number, with those networks dropped from that
row and the drop stated.

This is the same degeneracy that produced the bogus 0.800 in experiment 7 on
this dataset, where a ratio over 8 presses was reported as a score. The guard
now names the offenders instead of silently emitting a fallback.

## Structural replication, incidentally

The same run re-measures the structural claim on 11 male CNS networks: real
spectral radius **2.05**, rewired **0.65 ± 0.02**, and all 10 controls reach a
blank-field fixed point. That reproduces `docs/CLAIMS.md` claim 1 on this
dataset, from an independent build.

It is worth noting what that contrast looks like next to everything above. The
behavioural rows move around by a factor of six depending on which readout is
used; the radius does not move at all. That is the difference between a
measurement that needs a behavioural protocol and one that does not.

## Honest caveats

- **10 controls, floor 0.091, four arms.** Nothing here can be significant.
- **One dataset.** This says nothing about FlyWire, where the anatomical
  readout is not known to be degenerate in the same way.
- The PC arms select features and signs from a silent probe, then play with
  noise; experiment 6 already showed that probe-to-play mismatch breaking
  per-key thresholds, and it plausibly costs these arms accuracy too.
- Rewired topology only. Neither the retinotopy nor the channel-label family was
  run.

## What this licenses

- State that **the male CNS untrained reversal is readout-dependent**, and stop
  quoting it as though it were a fact about that connectome. That part is
  robust: it holds on tuning and held-out charts alike.
- Do **not** state that the real male CNS network beats its controls, on `pc8`
  or anything else. The one arm that pointed that way lost it on charts it had
  not been tuned on.
- **Report held-out numbers whenever a threshold was chosen on the scored
  charts.** The gap between 0.258 and 0.122 here is entirely that choice, and
  every untrained comparison in this project has the same structure.
- Any follow-up should pre-register one arm, at higher n, before looking — see
  `docs/PREREGISTRATION.md` for the pattern and `docs/RESULTS_E14.md` for what
  happens when a 1-in-20 claim meets forty controls.
