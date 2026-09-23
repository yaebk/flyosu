# Experiment 11 — per-key delays: the fix works, for everyone else

**Short answer: experiment 8's prescription was right and its beneficiary is
not the real connectome. Letting each key wait before pressing nearly triples
untrained accuracy for the rewired controls (0.186 → 0.539) and moves the real
network almost not at all (0.196 → 0.242). Nineteen of twenty controls now beat
it, p = 0.95. And the last behavioural claim still standing — untrained
lane-correctness, 1/20 at p = 0.095 — goes to 11/20, p = 0.571. After this
experiment no behavioural comparison in the project favours the real
connectome.**

Raw numbers: `results/e11_delays_cap1000.json`, `results/e11.log`.

## What was changed

Experiment 8 established that the four channels peak 200–600 ms before the note
arrives, that the *spread* between them is the network's own latency structure
rather than the stimulus, and that therefore no sensory front end can fix the
timing — the fix had to go in the controller. This is that fix, and it is the
first change to the policy's *form* rather than its numbers: a threshold
crossing no longer presses the key, it **schedules** a press `delay_ms[k]`
later (`Controller.with_delays`).

The four delays are read off the same silent single-note probe every other
untrained quantity comes from — each key waits by however early its own channel
crosses, so the press lands at the judgment line. That is lane knowledge, four
more numbers, declared like the wiring permutation. Two deliberate choices:
delays are recomputed at every threshold in the sweep (where a channel crosses
depends on what it is crossing), and they are derived **per network from that
network's own probe**, so no control inherits the real network's.

Protocol otherwise unchanged: band wiring, θ swept per network and scored at its
own best, press-count guard on lane-correctness.

## Result

| | real | rewired ×20 | n ≥ real | p |
|---|---|---|---|---|
| accuracy, no delays (experiment 7) | 0.196 | 0.186 ± 0.075 | 8/20 | 0.429 |
| **accuracy, with delays** | **0.242** | **0.539 ± 0.169** | **19/20** | **0.952** |
| lane-correct, no delays | 0.727 | 0.469 ± 0.143 | 1/20 | 0.095 |
| **lane-correct, with delays** | 0.655 | 0.652 ± 0.178 | 11/20 | 0.571 |

Change from adding delays: real **+0.046** accuracy, controls **+0.353**.

This is the largest absolute improvement in untrained play the project has
produced — the best untrained accuracy goes from 0.196 to 0.539 — and it is
almost entirely a gain for the control family.

## Why the real network cannot use it

The delays it needs are enormous. Its channels cross threshold so early that
three of its four keys want to wait **652, 630 and 634 ms**; the fourth wants
24 ms. The control mean is 242 ms.

The note interval in these charts is **600 ms**. So on 3 of 4 lanes the real
network's required wait *exceeds the gap between consecutive notes* — the press
it schedules for one note lands while the next note is on screen. Only 1 of 20
controls is in that position; across controls 16% of lanes exceed the interval
against the real network's 75%.

**That is a plausible account and the control data do not establish it.** Across
the twenty controls, longer delays correlate with *larger* accuracy gains
(ρ = +0.39, p = 0.088) — the opposite sign to "long delays hurt". So the real
network is an outlier on the predictor while the predictor points the other way
within the family, which is the same shape as experiment 4's radius result and
experiment 9's pooled-correlation trap. The honest statement is: the real
network is alone in needing delays longer than the note interval, and that is a
candidate explanation for why it alone fails to benefit, not a demonstrated one.
Testing it properly means varying the note interval, which is one line in
`stage_chart` and would be a clean follow-up.

## A mistake caught in this experiment

The first run capped delays at 600 ms. That cap bound on **3 of the real
network's 4 lanes** and on only 11 of 80 control lanes — an asymmetric
procedural choice favouring the controls, the mirror image of the two (θ = 1.5,
the margin wiring rule) that cost this project claims in experiments 6 and 7.
It was caught before the result was reported, the cap was raised to 1000 ms
where it cannot bind (a note is visible for 800 ms, so no crossing can be
earlier), and the whole experiment was re-run. The capped run is kept as
`results/e11_delays_cap600.json`.

The numbers moved: under the 600 ms cap the real network scored 0.442 accuracy
against controls' 0.430 (9/20); uncapped it scores 0.242 against 0.539 (19/20).
A cap that looked like an implementation detail was worth 0.2 accuracy and
flipped the comparison. This is the third instance in this project of a choice
that is matched as a procedure and unmatched in outcome, and the first one that
went *against* the real connectome.

## What this does to the project's claims

**No behavioural comparison now favours the real connectome.** Untrained
lane-correctness was the last one standing, at 1/20 and p = 0.095; with a
controller that can wait it is 11/20 and p = 0.571. Untrained accuracy was
already level at 8/20 and is now 19/20 against. The supervised ceiling
(experiment 5) showed no advantage at any readout size. The learning comparison
(experiment 3, re-run) never reached significance.

What still stands is what stood before: the two structural measurements that
need no behavioural protocol — rewiring collapses the spectral radius and
raises the readout population's dimensionality, both 0/40, p = 0.024, both
replicated on the male CNS. See `docs/CLAIMS.md`.

## Honest caveats

- **Stage 3 only, two 20-note charts**, so ±0.08 on lane-correct and ±0.04 on
  accuracy per network. The paired comparison across 20 networks carries the
  result, not any one row.
- **Delays are set from a silent single-note probe** and applied in noisy
  continuous play. Experiment 6 already showed that mismatch breaking per-key
  *thresholds*; it plausibly costs the delays some accuracy too, and a version
  fitted on recorded play (as `reservoir.py` fits the readout) would be the
  stronger test.
- **The 600 ms note interval is a free parameter** that this experiment holds
  fixed and that the proposed explanation depends on.
- Rewired topology only. Nothing here has been run against the retinotopy or
  channel-label families.

## What this licenses

- Use per-key delays: they are a large, cheap improvement to untrained play in
  general, and the controller is the right place for the fix.
- Do not describe any untrained behavioural comparison as favouring the real
  connectome.
- Vary the note interval before repeating the "delays exceed the gap"
  explanation as though it were established.
