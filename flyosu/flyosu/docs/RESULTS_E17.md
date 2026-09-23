# Experiment 17 — the pre-registered stray test: direction yes, significance no

**Short answer: the stray asymmetry replicates in direction and size and does
not reach significance. The real connectome makes 0.220 stray presses per note
against the controls' 0.739 ± 0.369, beating 38 of 40 outright and tying with
the other two — but the two ties put p at 0.073, and the declared Bonferroni
floor for two co-primary endpoints was 0.049. The predicted count (at least
38 of 40) was met; the predicted significance was not available at it. Neither
co-primary endpoint passes, so this experiment establishes nothing, and the
stray asymmetry remains a well-supported direction rather than a result.**

**The unpredicted finding is larger than the predicted one.** With the threshold
*declared* instead of swept, the real connectome is no longer behind on
accuracy at all — 0.357 against 0.299 ± 0.191, 14 of 40 controls reaching it,
where sixteen experiments of swept-threshold comparisons had it beaten by 18 or
19 of 20. That was a secondary descriptive endpoint here, no inference is
claimed for it, and it needs its own registered test.

Raw numbers: `results/e17_strays.json`, `results/e17_sh*.log`. Protocol frozen
in `experiments/e17_strays.py` and committed before the controls ran; controls
committed before the real network was built (`bac88d3`).

## Why this experiment exists

Experiment 16 found, *after* its numbers were in, that `accuracy` in `mania.py`
is a judgment-weighted mean over notes and charges nothing for a press that
lands on nothing. It measured 2.21 strays per note in the controls against 0.48
in the real network, twenty out of twenty worse. A discovery made that way
cannot also be the evidence for itself, so everything here — endpoints,
threshold, charts, controls, guard and the stopping rule — was written down
first.

## What was declared, and what happened

| | declared | result |
|---|---|---|
| threshold | **1.5, not swept** — `Player.untrained`'s default, never fitted | applied |
| charts | stage 3, 5 × 20 notes, 1400 ms, **seed 20260923** (never used before) | applied |
| controls | 40 rewired, run and committed before the real network | 40, committed at `bac88d3` |
| co-primary 1 | `reward` = acc − 0.05 × strays, real higher | p = 0.366 — **fails** |
| co-primary 2 | strays per note, real lower, guarded | p = 0.079 — **fails** |
| sensitivity | same, guard dropped | p = 0.073 |
| floor | 2 × 1/41 = **0.049** | neither endpoint reaches it |

### Co-primary 1: reward — predicted to fail, and failed

| | real | rewired ×40 | n ≥ real | p |
|---|---|---|---|---|
| reward @ 0.05 | +0.346 | +0.262 ± 0.195 | 14/40 | 0.366 |

The prediction recorded in the docstring was that this would not separate them,
because 0.05 is far too weak a penalty to convert a stray gap of ~1.7 into the
~0.12 of accuracy the controls led by. That reasoning was right about the
mechanism and wrong about the premise — the controls did not lead on accuracy
here at all — but the endpoint failed as predicted, and the real network's
nominal lead on it is not significant.

### Co-primary 2: strays — the direction replicates cleanly

| | real | rewired | n ≤ real | p |
|---|---|---|---|---|
| strays/note, guarded (37) | **0.220** | 0.739 ± 0.369 | 2/37 | 0.079 |
| strays/note, all 40 | **0.220** | 0.743 ± 0.361 | 2/40 | 0.073 |

The real network is 1.45 SD below the control mean and makes **less than a
third** of their strays. The guarded and unguarded versions agree, so the bias
the pilot exposed did not matter; both were declared in advance precisely so
this could be stated rather than chosen.

**The two networks that match it, `rewired #3` and `rewired #15`, do not beat
it — they tie it, at exactly 0.220.** Three of the 41 networks landing on
precisely 22 strays per 100 notes is more likely a floor in the policy than a
coincidence, and it is what costs the endpoint its significance: with a strict
inequality this would have been 0/40. **That is not a reason to use a strict
inequality.** The convention `p = (n_ge + 1)/(n + 1)` counts ties against the
hypothesis throughout this project, changing it here would be choosing a rule
after seeing which way it cut, and the floor is a fact about the policy that
deserves investigating rather than discarding.

### Secondary, descriptive — where the real surprise is

No inference is claimed for any of these; they were declared as descriptive.

| | real | rewired ×40 | n ≥ real |
|---|---|---|---|
| accuracy | 0.357 | 0.299 ± 0.191 | 14/40 |
| hit rate | **0.620** | 0.381 ± 0.229 | **6/40** |
| presses near a note | **85** | 53.6 ± 32.8 | 9/40 |
| lane-correctness | 0.741 | 0.809 ± 0.263 | 24/37 |

The real connectome hits more notes than 34 of 40 controls, presses near a note
more often than 31 of 40, and makes a third of the strays — and is
**level, not ahead, on accuracy**. It is also *behind* on lane-correctness,
which is reported here because it is the one secondary that runs the other way
and it would be dishonest to list only the flattering three.

The controls' own correlation between hit rate and strays is −0.167, so their
strays are not a by-product of playing more. They are pressing when nothing is
there.

## What changed, and what it costs the earlier numbers

The single procedural difference from every previous untrained comparison is
that **the threshold was declared rather than swept**. Experiment 16 showed why
that matters: accuracy cannot see strays, so a lower threshold can only help
it, and the accuracy-maximising theta was the lowest value offered for the real
network and 19 of 20 controls. The sweep was not finding each network's best
operating point, it was finding how hard each one could mash.

Under a declared threshold the accuracy deficit is gone. That is consistent
with the deficit having been an artefact of the selection procedure, and it is
**not the same comparison** — different charts, different threshold, 40
controls instead of 20, five charts instead of two. It cannot be quoted as
overturning experiment 11. What it does is make the question live again, and it
should be settled by a registered like-for-like test, not by this paragraph.

## Honest caveats

- **Neither co-primary reached its floor. This experiment supports nothing at
  the 0.05 level**, and the header of any summary should say so before it says
  anything about direction.
- The stray endpoint's failure is due entirely to two exact ties at a value
  that looks like a floor. That makes p = 0.079 an *honest* number and also a
  fragile one; a chart set with finer stray granularity could move it either
  way, which is a reason to re-run it, not to prefer this reading of it.
- Five charts, 100 notes, one stage, one interval, rewired topology only.
- The accuracy reversal is a secondary endpoint on a condition chosen for a
  different purpose. It is the most interesting thing here and the least
  entitled to be believed.
- Three controls never press near a note and are excluded from the guarded
  endpoint. They are named in the report and the unguarded version agrees.
- `theta = 1.5` is declared and never fitted, which is the point, but it is
  still a number somebody chose once, in experiment 1, for a different reason.

## What this licenses

- **Do not say the real connectome makes significantly fewer stray presses.**
  Say it makes about a third as many, beating 38 of 40 and tying the rest, at
  p = 0.073 against a declared floor of 0.049.
- **Stop quoting the untrained accuracy deficit without saying the threshold was
  swept.** Under a declared threshold it is not there, on a fresh chart set with
  twice the controls.
- Investigate the 0.220 floor. Three networks on the same value is a fact about
  the policy nobody has looked at.
- The next registered test should be accuracy under a declared threshold, stated
  as the primary endpoint in advance, since that is now the open question and
  this experiment only stumbled on it.
