# What this project actually shows

One page, kept current, superseding anything older that contradicts it.
Fifteen experiments, two connectomes, and eleven occasions on which a result
got weaker once the comparison was pushed harder — one of them a retraction of a
number this document itself carried. Written for someone deciding what to
believe, not what was believed at the time.

Each claim below carries the control family it holds *against*. That
qualification is load-bearing: the project has three control families and they
are not interchangeable.

## The control families, and what each can test

| family | what it scrambles | what it can test |
|---|---|---|
| `shuffle_seed` — rewired topology | the graph, preserving degree, weight and sign multisets | everything; the direct test of "does the wiring matter" |
| `retino_seed` — shuffled retinotopy | which photoreceptor sees which direction; graph untouched | behaviour and dimensionality; **raises** the spectral radius |
| `channel_seed` — shuffled channel labels | which descending neurons form each of the four groups | behaviour only — **cannot move** the radius or the readout dimensionality, by construction |

"Against controls" is never an adequate statement. Name the family.

## Supported

**1. Rewiring the topology collapses the blank-field spectral radius.**
Real 2.283, rewired 0.733 ± 0.089 over 40 seeds, **0/40, p = 0.024**;
replicated on the male CNS (2.055 vs 0.650 ± 0.025, 0/10, p = 0.091).
Distributions do not approach each other — the largest of 40 rewired draws is
1.12. `docs/RESULTS_E9.md`.

**2. Rewiring the topology raises the readout population's dimensionality.**
Real PC1 0.384, rewired 0.144 ± 0.024, **0/40, p = 0.024**; holds identically
on the top-4 fraction and on the gain-invariant participation ratio, so it is
not an artefact of the large gain. Replicated on the male CNS (0/10). On
FlyWire the effect is specific to the *descending-neuron population* — the
whole network, the hidden population, and a size-matched random population show
no separation, and the random one reverses sign. On the male CNS it is
network-wide instead, and that difference is unexplained.
`docs/RESULTS_E9.md`.

**3. Those two are independent properties.** Within every control family on
both datasets the correlation between them is ≈ 0 (radius ~ PC1: +0.08 at
n = 40). The large correlation that appears if families are pooled (+0.74) is a
two-blob artefact and should never be quoted. `docs/RESULTS_E9.md`.

These three are the only results in the project below p = 0.05, and the only
ones that need no behavioural protocol — which is why no procedural correction
has touched them. **Every behavioural comparison has now been run under a fair
protocol and none favours the real connectome**; the one that comes closest is
"learning, thresholds-only" below, at p = 0.22, which is now the sole entry
under "supported in direction".

## Supported in direction, not significant

**4. Learning, thresholds-only.** Real 0.211 vs rewired 0.101 ± 0.079, 1/8,
p = 0.22. The condition where the wiring does the most work, and the part of
experiment 3 that best survives re-measurement. This is now the **only**
behavioural comparison in the project pointing the real connectome's way, and
it is not significant. `docs/RESULTS_E3.md`.

## Not supported

**5. The real network's channels are unusually lane-selective.** Real 0.790 vs
rewired 0.547 ± 0.174 over 40 seeds, **4/40, p = 0.122**, under a protocol
frozen and tagged before any network was measured and with the full control
distribution committed before the real network was run once
(`docs/PREREGISTRATION.md`, tag `e14-prereg`). It stood at 1/20, p = 0.095.
**Nothing about the procedure changed and the real value did not move** — 0.79
then, 0.790 now. Twenty more controls were drawn and four of them reached it,
which is roughly what a distribution 1.4 SD below the real value predicts. The
direction survives and the claim does not.

The declared `retino_seed` secondary gives 0/20, p = 0.048, and **must not be
quoted as support**: retinotopy-shuffled networks average 0.407 on this
endpoint against the rewired family's 0.547, so they are a *weaker* null —
scrambling which photoreceptor sees which direction degrades lane identity at
the input, before the graph is reached. The real network cleared the easy bar
and failed the hard one, and its p is pinned to the n = 20 floor. The
registration should have excluded that family for the same reason it excluded
`channel_seed`; that it did not is recorded as an error in the registration.
`docs/RESULTS_E14.md`.

**6. Untrained accuracy.** Real 0.242 vs rewired 0.539 ± 0.169, **19/20,
p = 0.95**, once the controller may wait before pressing (experiment 11).
Without delays it was already level at 8/20. `docs/RESULTS_E11.md`,
`docs/RESULTS_E7.md`.

**7. Untrained lane-correctness.** Real 0.655 vs rewired 0.652 ± 0.178,
**11/20, p = 0.571**, under the same protocol. This was the last behavioural
claim standing — it held at 1/20, p = 0.095 with a controller that had to press
the instant a channel crossed, and does not survive one that can wait. It also
reverses on the male CNS, where experiment 13 has since shown the reversal
itself to be an artefact of the anatomical readout ("the male CNS untrained
reversal", below). `docs/RESULTS_E11.md`.

**8. Any advantage at the supervised ceiling.** With the readout fitted in
closed form, the real network is inside the rewired distribution at every
readout size (best 3/10, p = 0.36) — while playing far better in absolute terms
(0.92 accuracy with 68 parameters). `docs/RESULTS_E5.md`.

**9. Recurrent gain as an explanation for behaviour.** Radius does not predict
untrained play across random graphs (ρ = 0.20, p = 0.39).
`docs/RESULTS_E4.md`.

**10. The male CNS untrained reversal is an artefact of the anatomical
readout, and removing it reaches level, not ahead.** Experiment 13 ran four
readouts on the same male CNS networks, charts and threshold grid. On the four
leg-motor pools the real network loses **9/10** on the scored charts and 9/10
again on held-out ones — a robust disadvantage, and the one experiment 7
reported. On eight principal components of the same 348 neurons it wins 1/10 on
the scored charts and **loses that entirely on charts nothing was re-chosen
for**: 0.258 → 0.122 while the controls hold at 0.131 → 0.138, giving 6/10,
p = 0.636. So the pooling is a real handicap and removing it leaves the real
connectome level with its controls rather than ahead of them. Nothing here is
significant — 10 controls give a floor of 0.091 and four arms a Bonferroni floor
of 0.364 — and the arms declare different amounts of lane knowledge (14.7 bits
against 4.6), so they are not a ranking of readouts. `docs/RESULTS_E13.md`,
`docs/RESULTS_E7.md`.

## Retracted

**11. "The real network is the only one admitting a single working threshold
for all four keys" (experiment 6).** Measured under a wiring rule that was not
optimising that band. With each network wired by the rule that does, 5/20
controls match it. `docs/RESULTS_E7.md`.

**12. "The real connectome's spectral radius is unusual."** Retinotopy-shuffled
networks exceed it 20/20 on FlyWire. The correct statement is directional:
rewiring the topology collapses the radius. `docs/RESULTS_E9.md`.

**13. "p = 0.048" as the untrained headline (experiment 4).** Measured at a
fixed θ = 1.5, which is the real network's best value and almost never a
control's. Under a per-network best threshold it is p = 0.095.
`docs/RESULTS_E6.md`.

**14. The clean monotone learning ordering (experiment 3).** Under the
corrected wiring rule it survives on area under the learning curve
(1/8 → 2/8 → 4/8) and breaks on final accuracy (1/8 → 3/8 → 2/8). Quote it with
the metric attached, or not at all. `docs/RESULTS_E3.md`.

**15. "The real network transfers to chords worse because its common mode
responds to both lanes at once" (experiment 5).** Measured directly, all
thirteen networks respond to a chord as the sum of the two single notes to
within 3–4%, and the real one shows *less* cross-talk than the controls, not
more. The `channels` deficit is a transfer failure that refitting on chords
fixes; the `pca8` deficit persists identically on *single notes* under the same
fit, so it is a fitting pathology rather than anything to do with chords.
`docs/RESULTS_E10.md`.

## The methodological result

**Ten times, a gap shrank or an explanation dissolved once the comparison
was made more carefully** — readout fitting (e5), the shared threshold (e6),
the wiring rule (e7), the sensory front end (e8), the learning comparison's
starting wiring (e3 re-run), the chord hypothesis (e10), and per-key delays
(e11), channel lane-selectivity under a pre-registered test (e14), the note
interval as the reason delays fail the real network (e12), and the male CNS
PC-readout advantage once it met held-out charts (e13). Six times the thing that
fell was a claim this project had already written down, and twice what fell was
a *mechanism* rather than a difference.

The mechanism was the same each time and is worth naming: a choice that is
*matched as a procedure* — the same rule applied to every network — can still
be *unmatched in outcome*, because it was developed while looking at the real
connectome and happens to suit it. θ = 1.5 and the margin wiring rule were both
of this kind. Neither looked like a degree of freedom at the time.

Experiment 11 produced the mirror image, which is worth knowing because it
shows the effect is not a bias in one direction: a 600 ms cap on the per-key
delays bound on 3 of the real network's 4 lanes and almost none of the
controls', and it was worth 0.2 accuracy and flipped the comparison. It was
caught before the number was reported. The rule is not "choices favour the real
network" but "a choice you did not think of as a parameter will be tuned by
whichever network you were looking at when you made it".

The practical consequence for anyone extending this: **design the comparison to
be adversarial to the real connectome from the start.** Give every control its
own best operating point on every free parameter, decide the metric before
looking, and treat any procedure tuned on the real network as suspect until it
has been swept per network.

The first seven were caught **after** the fact, which is the weakness in this
record.
A pattern of self-caught errors shows the mistake is easy to make here, not
that it has stopped happening. Experiment 14 is the response: one comparison in
which the mistake is structurally impossible, because the forty controls are
run and committed before the real network is measured at all, so there is no
distribution available to tune against. Its protocol is frozen and tagged
(`docs/PREREGISTRATION.md`, tag `e14-prereg`), it names one primary endpoint,
and it said in advance what a null licenses.

**It reported, and it is a null**: real 0.790 against 0.547 ± 0.174, 4/40,
p = 0.122 (`docs/RESULTS_E14.md`). Its eighth instance has a different cause
from the other seven and is worth separating out. Those were procedures
developed while looking at the real network. **This one was plain
undersampling: the procedure was beyond reproach, the real value did not move,
and twenty more controls were enough to dissolve the claim.** No fairness fix
would have prevented it.

The consequence is uncomfortable and should be stated in full: **this project
has reported "0/20" and "1/20" throughout, and at n = 20 those counts read as
far stronger than they are.** A single exceedance already gives p = 0.095, so
such a result was never significant, and the count created an impression the
p-value did not support. Treat every 20-control result in these documents as
weaker than it looks. The two structural claims are the exception — they are at
0/40, and experiment 14 independently reproduced the spectral radius at
2.283 vs 0.733 ± 0.090 on forty freshly built networks. **A claim that is
really there does not soften when the controls double.**

## Absolute performance, separately from any comparison

The best readout reaches **0.92 accuracy** on held-out stage-3 charts with 68
parameters, fitted in closed form, connectome frozen (`docs/RESULTS_E5.md`).
Across the curriculum it presses the right key essentially always
(lane-correct ≥ 0.95) and hardly ever presses an empty lane. What limits it is
timing, and experiment 8 established that ceiling is structural: the spread of
the four channels' peak times is the network's own latency structure, and no
sensory front end removes it. `docs/RESULTS_E8.md`.

Per-key delays in the controller were the prescription, and they work —
untrained accuracy nearly triples, from 0.186 to 0.539, giving the project its
best untrained play. The real connectome gains least from them.
`docs/RESULTS_E11.md`.

**Experiment 12 refuted the explanation experiment 11 offered for that.** The
story was that the real network's required waits (~650 ms) exceed the 600 ms
note gap, so each scheduled press lands on the following note. Tested at 450,
1000 and 1400 ms with 20 controls each: the gap to the controls never closes
(0.226, 0.297, 0.268, 0.282), and at 1000 ms and above **none of its lanes
overruns the interval** while it remains 18/20 and 19/20. It also gains +0.29
from delays once the chart leaves room, so "cannot use them" was wrong in the
other direction. The delay-versus-gain correlation quoted there as
counter-evidence (+0.39, p = 0.088) comes back +0.30, p = 0.200 at n = 20 and is
flat elsewhere; it was noise and should not be quoted either way.
`docs/RESULTS_E12.md`.

**A correction, recorded because it is the third instance of the same
mistake.** This section previously said that at wide intervals the real
network's lane-correctness without delays is 1.000 against controls' 0.56, and
called it the most promising untried lead in the project. That 1.000 was the
**fallback value on 9 presses**: no threshold in the sweep reaches the 20-press
guard, so lane-correctness is undefined there and the code emitted an argmax
over ineligible entries. The same fallback produced the male CNS 0.800 in
experiment 7 and the `pc4` value in experiment 13. In all three the guard
existed and the fallback branch defeated it; it now returns `None`, existing
result files are re-guarded on read, and the offending network is named.

What is true is weaker: without delays at a wide interval the real network
**presses very rarely** — 9 presses against 40 notes — and is in the right lane
when it does. Six of twenty controls are in the same position, so it is not
unusual. `docs/RESULTS_E12.md`.

**Experiment 15 then tested the controller idea anyway and closed it.** Changing
which edge of the drive fires the key favours the real connectome on no arm —
11/20 on the upward crossing, 11/20 on the falling edge, 20/20 on the peak — and
no free trigger comes near what four declared delay numbers achieve (controls
0.196 against 0.736). The falling edge does fix the timing almost completely, a
median 610 ms early becoming 86 ms, and that does not convert into accuracy:
what the delays buy is consistency, not offset. **Seven distinct parts of the
untrained policy have now been varied — shared threshold, wiring rule, sensory
front end, per-key delays, note interval, readout and firing edge — and none
produces a behavioural comparison favouring the real connectome.**
`docs/RESULTS_E15.md`.
