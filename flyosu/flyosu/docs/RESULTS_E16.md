# Experiment 16 — held-out charts, and the thing accuracy was not measuring

**Short answer: the prediction failed. Scoring the same frozen policies on
charts nobody tuned against does not widen the real connectome's deficit, it
roughly halves it — 19/20 controls beat it on the sweep, 13/20 on held-out, and
the gap falls from +0.282 to +0.123 (p 0.952 → 0.667). It is still not ahead.
But looking at *why* the controls score turned up something the project has
been blind to for sixteen experiments: `accuracy` ignores stray presses
entirely, and the controls press 2.21 stray keys per note against the real
network's 0.48 — all twenty of them worse, without exception. The controls have
partly been buying their accuracy by mashing.**

Raw numbers: `results/e16_heldout_interval1400.json`, `results/e16_sh*.log`.

## What was done

Nothing was re-chosen. Each of the 21 networks from experiment 11 at the
1400 ms interval had its finished policy read back — its wiring from its own
silent probe, the threshold that maximised its sweep accuracy, and the four
per-key delays that threshold implies — and replayed on three charts it had
never seen (stage 3, seed 999, experiment 3's reserved seeds, disjoint from the
sweep's seed 7030). The threshold was 0.5 for the real network and for 19 of
the 20 controls, so no network is being handicapped by an unusual choice.

The reason to do it is that experiment 13 showed threshold-on-the-scored-charts
costs a single network more than it costs a twenty-draw distribution. The
question was which way that bias runs here.

## The pre-registered endpoint: prediction failed

`experiments/e16_heldout.py` predicted, in its docstring above the code, that
both sides would lose accuracy, that the ordering would not change, that the
real connectome would still be beaten by at least 18 of 20, and that the gap
would **widen**.

| | real | rewired ×20 | n ≥ real | p | gap |
|---|---|---|---|---|---|
| sweep (experiment 11) | 0.454 | 0.736 ± 0.192 | 19/20 | 0.952 | +0.282 |
| **held-out** | **0.569** | 0.692 ± 0.237 | **13/20** | **0.667** | **+0.123** |

Wrong on three counts of four. The real network did not lose accuracy, it
**gained** 0.115; the controls lost 0.043 ± 0.113; only 6 of the 20 controls
improved at all, and the real network's improvement is second-largest of the
21 networks (n ≥ real 2/20, p = 0.143). The gap narrowed rather than widened,
and 13/20 is well short of the 18/20 predicted.

The prediction text said a narrowing to within one standard deviation "would be
the first sign in seven varied policies that the deficit is procedural rather
than real, and would have to be chased." The gap is +0.123 against a control
spread of 0.237, so by the criterion recorded in advance, this has to be
chased — and the rest of this document is that chase.

**What it is not.** p = 0.667 is not a result in the real connectome's favour.
Thirteen of twenty controls still beat it. The claim here is that the
*magnitude* of its deficit was inflated by selecting the threshold on the
scored charts, not that the deficit is gone.

## What turned up on the way: strays

Accuracy in `mania.py` is a judgment-weighted mean over **notes**. A press that
lands on nothing is a `stray` and is invisible to it. Held out:

| | real | rewired ×20 | n ≥ real |
|---|---|---|---|
| hit rate | 0.833 | 0.774 ± 0.244 | 10/20 |
| accuracy | 0.569 | 0.692 ± 0.237 | 13/20 |
| **strays per note** | **0.483** | **2.212 ± 0.578** | **20/20** |
| presses counted near a note | 80 | 90.1 ± 26.4 | 13/20 |
| lane-correct | 0.750 | 0.544 ± 0.183 | 3/20 (p 0.190) |

The real connectome's hit rate is *above* the control mean and its accuracy is
below it, which is only possible because the controls are hitting more notes
per note hit — they press about four and a half times as often into empty
space. Every one of the twenty is worse on this, with no overlap at all.

That is not a small bookkeeping detail. In osu!mania a stray press is a real
cost; here it has been free for sixteen experiments, and the untrained policy
comparison that this project has repeatedly reported as "the controls win" has
been scored on a measure that cannot see the controls' main failure mode.

## The trap, named

The project already declares a combined quantity, `learn.reward` = accuracy −
`STRAY_PENALTY` × strays-per-note. There are two penalties in the codebase and
they give opposite answers:

| penalty | where it comes from | real | rewired ×20 | n ≥ real | p |
|---|---|---|---|---|---|
| 0.05 | `learn.STRAY_PENALTY`, the **evaluation** constant | +0.545 | +0.582 ± 0.239 | 11/20 | 0.571 |
| 0.40 | `reservoir.STRAY_PENALTY_FIT`, the **ridge-fitting** constant | +0.376 | −0.193 ± 0.332 | **0/20** | **0.048** |

**The 0.048 is not a result and must not be quoted as one.** The endpoint
pre-registered for this experiment was accuracy. The stray asymmetry was found
after the numbers were in, and 0.4 was then selected from two available
constants *after* seeing that it was the one that would separate them — and it
is the fitting penalty, not the evaluation penalty, so it is the wrong one on
its own terms as well. Choosing a metric to fit a result you have already seen
is the exact failure the pre-registration in experiment 14 exists to prevent.

The defensible line is the row above it: **on the project's own declared
evaluation reward the comparison is null**, 0.545 against 0.582, p = 0.571.

What the stray asymmetry licenses is a **new pre-registered test**, on fresh
charts, with the endpoint and the penalty fixed in writing before the run. That
is experiment 17.

## Honest caveats

- **Three charts, 60 notes.** A 0.115 accuracy swing on 60 notes is roughly
  1.8 binomial standard errors, so the real network's improvement on its own is
  not distinguishable from chart noise. What carries the paragraph above is that
  the 20 controls faced the *same three charts* and moved the other way.
- The controls' sweep-to-held-out rank correlation is ρ = 0.899, so the held-out
  ranking is mostly the sweep ranking; the change is concentrated in where the
  real network sits within it, which is a single draw.
- One interval (1400 ms), one stage, rewired topology only.
- The wiring was read back from the stored run rather than re-derived, so the
  replayed policy is exactly the one that was scored, but any error in the
  original probe is inherited rather than caught.
- Lane-correctness at 0.750 against 0.544 is the best direction any behavioural
  measure has shown in this project, and at 3/20, p = 0.190, it is still not
  significant and was not pre-registered here either.

## What this licenses

- **Stop quoting experiment 11's +0.282 gap as the size of the behavioural
  deficit.** Held out it is +0.123, and roughly half of what was being reported
  was threshold selection.
- **Never quote a bare accuracy figure from this project again without the
  stray count beside it.** Accuracy cannot see stray presses and the two
  populations differ on strays by more than they differ on anything else
  measured so far.
- Do not claim the real connectome plays better. On the pre-registered endpoint
  13 of 20 controls beat it, and on the declared evaluation reward 11 of 20 do.
- Treat the stray asymmetry as a hypothesis, not a finding, until experiment 17
  tests it on charts chosen before the endpoint was.
