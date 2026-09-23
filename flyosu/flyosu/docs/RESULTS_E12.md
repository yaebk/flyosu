# Experiment 12 — the note interval was not the reason

**Short answer: experiment 11's explanation is refuted. It proposed that the
real connectome cannot use per-key delays because three of its four keys need to
wait ~650 ms against a 600 ms note gap, so each scheduled press lands on the
following note. Widen the gap to 1000 or 1400 ms and **none** of its lanes
overrun any more — the mechanism is entirely gone — and it is still beaten by 18
and 19 of 20 controls. Across a three-fold range of note intervals the gap
between the real network and its controls never closes: 0.226, 0.297, 0.268,
0.282. The interval moves every network together and is not what separates
them.**

Raw numbers: `results/e11_delays_cap1000_interval{450,1000,1400}.json`, the
600 ms arm in `results/e11_delays_cap1000.json`, analysis in
`experiments/e12_interval.py`.

## The predictions, written before the numbers

`experiments/e12_interval.py` states four predictions in its module docstring,
above the code that evaluates them. Reproduced here as written:

1. the real network's accuracy rank among the controls improves on 19/20 at
   600 ms;
2. its gain from delays grows with interval, from +0.046 at 600 ms;
3. at 450 ms, where its delays overrun the gap by even more, it should be no
   better and probably worse, while the controls (mean delay 242 ms) hold up;
4. within the controls, the +0.39 correlation between mean delay and gain
   should turn negative at 450 ms and weaken at 1400 ms.

## Result

Untrained accuracy with per-key delays, each network at its own best threshold,
20 rewired controls at every interval:

| interval | real | rewired ×20 | n ≥ real | p | gap | real lanes over interval |
|---|---|---|---|---|---|---|
| 450 ms | 0.183 | 0.410 ± 0.140 | 20/20 | 1.000 | +0.226 | 75% |
| 600 ms | 0.242 | 0.539 ± 0.173 | 19/20 | 0.952 | +0.297 | 75% |
| 1000 ms | 0.454 | 0.723 ± 0.202 | 18/20 | 0.905 | +0.268 | **0%** |
| 1400 ms | 0.454 | 0.736 ± 0.192 | 19/20 | 0.952 | +0.282 | **0%** |

**The decisive row is the last column.** Experiment 11's mechanism was that the
real network's required waits exceed the note gap. At 1000 ms and above, not one
of its four lanes overruns — the mechanism is switched off completely — and its
position is unchanged at 18/20 and 19/20. Whatever puts the real connectome last
is not the note interval.

## Prediction by prediction

**1. Rank improves — fails.** 20/20 → 19/20 → 18/20 → 19/20. There is no trend
worth the name, and the best it ever reaches is 18 of 20 controls beating it.

**2. Gain from delays grows — holds.** The real network's improvement from
adding delays goes +0.058 (450), +0.046 (600), +0.288 (1000), +0.279 (1400). So
the mechanism experiment 11 described is *real*: once notes stop colliding, the
delays do their job and are worth ~0.29 to the real network. But the controls'
gain grows too, and by more: +0.249, +0.353, +0.532, +0.549.

**3. Worse at 450 ms — holds for the real network, fails as a comparison.** Real
accuracy drops to 0.183, below its 600 ms value, exactly as predicted. But the
controls drop as well, to 0.410 from 0.539. The prediction that made this a
*test* was that the controls would hold up while the real network suffered. They
did not; everyone suffers when the notes crowd.

**4. The correlation flips — fails, and the original was never solid.** Spearman
ρ between a control's mean delay and its accuracy: −0.04 (450), +0.30 (600),
+0.00 (1000), −0.04 (1400), none significant. Experiment 11 reported +0.39,
p = 0.088 at 600 ms and used it as counter-evidence against its own explanation;
re-measured at n = 20 it is +0.30, p = 0.200. **It should not have been quoted
in either direction.** A correlation that moves that much between runs of the
same condition is noise, and this document is the place to say so.

## What survives, and what does not

**Survives:** per-key delays are a large, cheap improvement to untrained play,
and more so the more room the chart gives. At 1400 ms the controls reach 0.736,
the best untrained accuracy this project has produced.

**Survives:** the real connectome benefits from delays too — +0.29 once the
interval is wide enough. Experiment 11 recorded its gain as +0.046 and concluded
it "cannot use them". That was an artefact of the 600 ms chart, and the stronger
claim should be withdrawn: it can use them, it just does not thereby catch up.

**Does not survive:** the explanation. "Its delays exceed the note gap" is a
true description of the 450 and 600 ms charts and is not why it comes last, and
`docs/RESULTS_E11.md` was right to label it a candidate rather than a finding.
This is now the eighth time in this project that an explanation or a gap
dissolved once the comparison was pushed harder, and the second time the thing
that dissolved was a *mechanism* rather than a difference.

## An oddity worth recording

At 1000 and 1400 ms the real network's **no-delay** lane-correctness is 1.000,
against controls' 0.562 ± 0.40 (7/20) — its best showing anywhere in the
project. Adding delays *reduces* it to 0.645 (−0.355) while raising the
controls' (+0.22).

So with a wide enough gap and no delays, the real connectome presses the right
key essentially every time, and simply presses too early to score. That is
consistent with everything experiment 8 established about its latency structure,
and it means the delays are trading lane-correctness for timing in a way that
helps the controls and hurts it. Nobody has tested a policy that keeps the early
crossing and fixes timing some other way, and this is the clearest hint so far
that one is worth building.

## Honest caveats

- **Stage 3, two 20-note charts per network**, as in experiments 7 and 11; the
  paired comparison across 20 networks carries the result, not any single row.
- **The threshold is chosen on the charts being scored.** Experiment 13 showed
  that costs the real network more than its controls on the male CNS (0.258 →
  0.122 held-out against 0.131 → 0.138). No held-out arm was run here, and it
  should be.
- **Delays come from a silent probe** and are applied in noisy play, the same
  mismatch experiment 6 showed breaking per-key thresholds.
- Rewired topology only, at every interval.
- The delay cap is 1000 ms and non-binding at every interval tested; the
  600 ms cap that bound asymmetrically in experiment 11 is not in use here.

## What this licenses

- **Stop repeating the "delays exceed the note gap" explanation.** It is tested
  and it is not the cause.
- Do not say the real connectome cannot use per-key delays. It gains +0.29 from
  them when the chart leaves room; it just gains less than every control.
- Report the note interval alongside any untrained accuracy figure. Absolute
  numbers move by a factor of two and a half across the range tested here, so a
  bare "0.54" means nothing without it.
- Build and test a policy that exploits the real network's early, accurate lane
  choice instead of delaying it. That is where its one remaining behavioural
  strength actually sits.
