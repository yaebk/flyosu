# Experiment 14 — the pre-registered comparison: H1 fails

**Short answer: the real connectome's channels are not significantly more
lane-selective than rewired controls'. Real 0.790, rewired 0.547 ± 0.174 over
40 seeds, 4/40 controls reach or exceed it, p = 0.122 against a pre-registered
threshold of 0.05. The claim moves from "supported in direction" to "not
supported".**

**What makes this instance different from the previous seven: nothing about the
procedure changed, and the real network's number did not move at all.** It
scored 0.79 under the n = 20 comparison and 0.790 here. The entire difference
is that twenty more controls were drawn, and four of them landed at or above a
value that one of the first twenty had reached. The earlier 1/20 was not a
biased protocol. It was too few controls.

Protocol frozen and tagged at `e14-prereg` before any network ran:
`docs/PREREGISTRATION.md`. Raw numbers: `results/e14_prereg_controls.json`,
`results/e14_prereg_real.json`, `results/e14.log`.

## The design, and why its ordering mattered

The forty controls were run, reported and **committed to git before the real
network was measured once** (commit `1a3d163`). The script refuses to run the
real network until that file exists. From the moment the null was committed
there was no way to adjust the endpoint, the wiring rule or the threshold to
suit the real network's value, because that value had not been computed.

This matters more than usual here. Seven times this project has watched a gap
shrink once a comparison was made fairer, and every one of those seven was
caught after the fact. A record of self-correction shows the mistake is easy to
make, not that it has stopped. This is the first comparison in the project where
it could not have happened.

The commit message on the null said, while still blind, that the largest control
sat at 0.874 — above the 0.79 the real network had scored before — and that the
result would therefore come down to one or two controls either side. That is on
the record, in git, timestamped before the real run.

## Result

Primary endpoint, `probes.selectivity(...)["argmax_mean"]`: how often each
lane's wired channel is the largest of the four during its own lane's note,
averaged over lanes. Label-free, threshold-free, press-free.

| | real | rewired ×40 | n ≥ real | p | floor |
|---|---|---|---|---|---|
| **argmax_mean (primary)** | **0.790** | **0.547 ± 0.174** | **4/40** | **0.122** | 0.024 |
| peak_margin_mean (secondary) | 0.998 | 0.730 ± 0.584 | 14/40 | 0.366 | 0.024 |
| spectral radius (not an endpoint) | 2.283 | 0.733 ± 0.090 | 0/40 | 0.024 | 0.024 |

All 40 controls reached a fixed point; none was excluded, and the
pre-registration forbade exclusion in any case.

**H1 is not supported at the pre-registered threshold.** The real network is
+1.4 SD above the control mean, so the direction survives, but four controls
reach it and a fifth (`rewired #31`, 0.789) sits one thousandth below. Calling
that five-controls-at-the-value is fairer than calling it four.

The four that reach it: `#8` 0.874, `#38` 0.866, `#29` 0.809, `#23` 0.807.

## Why n = 20 said 1/20 and n = 40 says 4/40

The real value is identical to three decimal places. The control *mean* is also
stable (0.50 ± 0.17 at n = 20, 0.547 ± 0.174 at n = 40). What changed is the
tail. A distribution with SD 0.174 whose mean sits 1.4 SD below the real value
will put roughly 8% of its draws above that value — about 1.6 of 20, and about
3.2 of 40. **Both observations are consistent with the same distribution. The
first was not evidence of an advantage; it was the expected number of
exceedances, read as if it were a rank.**

This is the specific hazard of quoting "1/20" as though the count were the
finding. With 20 controls the p-floor is 0.048, so a single exceedance already
gives p = 0.095 — the result was never significant, and its apparent strength
came from the count looking impressive rather than the p-value being small. The
project has been quoting the count in this form throughout. The counts were
never wrong; the impression they create at n = 20 is.

## A structural detail worth keeping

The real network's per-lane selectivity is **[0.186, 1.000, 0.975, 1.000]**.
Three of its four lanes are essentially perfect and the fourth (lane 0, D) is
far below chance-adjacent. Its aggregate 0.790 is not "uniformly good"; it is
three lanes at ceiling dragged down by one broken one.

That is consistent with the long-standing observation that the D/J extremes
suffer from where experiment 1 placed the lanes on the arena, and it suggests
the aggregate endpoint was the wrong summary: a measure over four lanes where
one is structurally handicapped by a modelling choice mixes a connectome
property with an arena-placement artefact. **This is an observation, not a
rescue.** The pre-registration named one primary endpoint precisely so that a
failed test could not be followed by a better-looking recomputation, and a
per-lane or best-three-lane variant is exactly the recomputation it forbade.
Anyone who wants to test it must pre-register it as a new experiment.

## What this changes

- **Claim 4 in `docs/CLAIMS.md` moves to "Not supported".** Channel
  lane-selectivity was the last non-behavioural directional claim and it does
  not survive a properly powered test.
- **The methodological count goes from seven to eight**, with a caveat: this
  eighth instance has a different cause from the other seven. Those were
  procedures developed while looking at the real network. This one is plain
  undersampling, and no procedural fairness fix would have prevented it. The
  lesson it adds is that **"0/20" and "1/20" are weak evidence even when the
  procedure is beyond reproach**, and that this project's habit of reporting
  counts made them read as stronger than they were.
- **The two structural claims are untouched and were independently reproduced
  here.** The spectral radius came out at 2.283 vs 0.733 ± 0.090, 0/40,
  p = 0.024 — identical to experiment 9, on forty independently rebuilt
  networks. That is a real replication, and it is the contrast that makes the
  point: a claim that is genuinely there does not soften when the controls
  double. The largest of forty rewired draws is 1.125 against the real 2.283.

## Honest caveats

- **One connectome, one control family, one endpoint.** The `retino_seed`
  secondary declared in the pre-registration was not run; it is recorded here as
  not run rather than omitted.
- **p = 0.122 is not evidence of no effect.** The direction is +1.4 SD and an
  effect could be real and this design underpowered to show it. The correct
  statement is that the claim is not supported, not that it is refuted.
- **The p-floor is 0.024**, so even a perfect 0/40 could not have gone below it.
- The model is assumed, not measured, and a comparison between a real graph and
  a rewired one holds every assumption in `docs/CALIBRATION.md` fixed.

## What this licenses

- Do not state that the real connectome's channels are more lane-selective than
  rewired controls'. State the direction with the p-value attached, or not at
  all.
- **Treat every "0/20" and "1/20" in this project's history as weaker than it
  reads.** The two structural claims are at 0/40 and are the exception.
- Pre-register the per-lane version before measuring it, or leave it alone.
- Keep running the controls before the real network. It cost nothing here and
  it is the reason this write-up needs no one to take anything on trust.
