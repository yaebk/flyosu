# Experiment 19 — the stray test, powered: it fails, and the endpoint is closed

**Short answer: the pre-registered stray test fails a second time, and by the
stopping rule declared in advance it will not be run a third. The real
connectome makes 0.2575 stray presses per note against the controls'
0.749 ± 0.370. That's a third as many and 1.3 SD better, the same direction and
size as experiment 17, but 4 of the 37 guarded controls do as well or better,
so p = 0.132 against a floor of 0.024. The all-40 sensitivity analysis agrees
(4/40, p = 0.122).**

**Ties were not the problem this time.** Experiment 17 failed at p = 0.073
because two controls tied the real network exactly. This run quadrupled the
chart count so that ties would become vanishingly rare, and they did (one
tie, 36 distinct values among 40 controls). Three controls beat the real
network *outright*, though, on 93, 96 and 96 strays against its 103. A
strict inequality, the reading experiment 17's ties had tempted, would still
give p = 4/41 = 0.098. The finer granularity did its job and showed that the
real network sits at about the 90th percentile of the control distribution,
not beyond the 95th.

Raw numbers: `results/e19_strays_powered.json`, `results/e19_real.log`,
`results/e19_controls_s*.log`. Protocol frozen in
`experiments/e19_strays_powered.py` and committed before any control ran;
the forty controls committed before the real network was measured
(`e006743`).

## The prediction, and how it did

Recorded in the protocol before any number: *the real connectome makes fewer
strays than at least 38 of the 40 controls, with at most one exact tie, and p
lands at or just above 0.024.* The tie count was right (one). The rank was
wrong: 36 of 40 rather than 38. The protocol also said "0/40 and 2/40 are both
entirely plausible"; 4/40 was outside even that range.

| endpoint | real | controls | as good or better | p |
|---|---|---|---|---|
| **strays/note, guarded (primary)** | **0.2575** | 0.749 ± 0.370 | 4/37 | **0.132** |
| strays/note, all 40 (sensitivity) | 0.2575 | 0.749 ± 0.361 | 4/40 | 0.122 |

Three controls failed the activity guard (#1, #4, #25). The guard and the
sensitivity analysis agree, so there is no disagreement to report.

## Secondary endpoints (descriptive, no inference)

| | real | controls | controls reaching real |
|---|---|---|---|
| accuracy | 0.325 | 0.308 ± 0.197 | 16/40 (+0.09 SD) |
| hit rate | 0.595 | 0.389 ± 0.237 | 7/40 (+0.87 SD) |
| reward | 0.313 | 0.271 ± 0.200 | 16/40 (+0.21 SD) |

On a fresh chart set, experiment 17's secondary finding holds: under a
declared threshold the real connectome is level with the controls on
accuracy, not behind them. That still has no registered test behind it.

The three controls that beat the real network on strays are not buying it
with silence. Their accuracies are 0.568, 0.473 and 0.497, all above the real
network's 0.325. A few rewired networks, then, are both cleaner and more
accurate at this protocol than the real one.

## What the two experiments say together

Experiments 17 and 19 are two independent measurements, on different chart
seeds and each against forty fresh controls, of the same declared protocol.
They agree closely:

| | real | control mean | real's rank | p |
|---|---|---|---|---|
| experiment 17 (100 notes) | 0.220 | 0.739 | 38 of 40 beaten, 2 tied | 0.073 |
| experiment 19 (400 notes) | 0.2575 | 0.749 | 36 of 40 beaten, 1 tied | 0.132 |

The real connectome reliably makes about a third as many stray presses as a
typical rewired network, and reliably lands in the top five to ten per cent
of the control distribution. It does not reliably land beyond the top five
per cent, which is what a single-draw permutation test at 0.05 requires. More
controls would not change that. As the experiment 19 protocol said before it
ran, more controls make p converge to the true quantile, not to zero, and
this quantile is about 0.9.

That is a real regularity, and it is not significant. Both statements belong
in the record, and neither should be traded for the other.

## Stopping rule

The protocol said: *If this fails, the stray endpoint is finished and must not
be run a third time. Two pre-registered failures is an answer.* It has failed
twice. The stray asymmetry stays in the claims as a well-measured direction
with an effect size, not a result, and no further registered test of it will
be run.

## A disclosure

While verifying that the batched play code (commit `07f000a`) is bit-identical
to the previous code on this experiment's measurement path, I ran the real
connectome through that path on 24 notes of this stage and interval, before
the controls were finished. That check should have used two controls. It
could not have influenced anything: the endpoint, threshold, chart set, test
and stopping rule were all fixed in code committed before any control ran, and
the script has no free parameters to tune. It is recorded here because the
point of the freeze is that no-one has to take that on trust.
