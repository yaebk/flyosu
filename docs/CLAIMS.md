# What this project actually shows

One page, kept current, superseding anything older that contradicts it.
Twenty-one experiments, two connectomes, and fifteen occasions on which a result
got weaker once the comparison was pushed harder. One was a retraction of a
number this document itself carried, two were results that had been running
*against* the real connectome, and the latest two come from auditing earlier
experiments at a declared threshold. Written for someone deciding what to
believe, not what was believed at the time.

**Read the threshold and stray warnings in claim 6 before quoting any accuracy
figure from this project.** Accuracy here cannot see presses that land on
nothing; the two populations differ on those more than on anything else
measured; and every threshold chosen by sweeping accuracy was therefore chosen
for mashing. Under a *declared* threshold the untrained accuracy deficit is not
present in experiments 17 and 19; the audit of earlier experiments at that
threshold finds it survives only where the controller may wait (experiment 11).

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
experiment 3 that best survives re-measurement. `docs/RESULTS_E3.md`.

**4b. Untrained lane-correctness, held out.** Real 0.750 vs rewired 0.544 ±
0.183, 3/20, p = 0.190, with the policies frozen from experiment 11 and scored
on unseen charts (experiment 16). Note that on the *sweep* charts the same
comparison is level (claim 7), so this is the selection correction working in
the real connectome's favour rather than a new measurement. It was not
pre-registered, and at 3/20 it is not significant.

**4c. Stray presses.** Real 0.220 per note vs rewired 0.739 ± 0.369 over 40
seeds, **2/40, p = 0.073** against a declared Bonferroni floor of 0.049, under a
protocol frozen and committed before the controls ran and with the full control
distribution committed before the real network was built
(`experiments/e17_strays.py`, commit `31770be`). A third as many strays, 1.45 SD
below the control mean, beating 38 of 40 outright. **It fails.** The two
remaining controls tie it at exactly 0.220 — three of 41 networks on precisely
22 strays per 100 notes, which looks like a floor in the policy — and ties count
against the hypothesis here as everywhere else in this project. This is the
best-supported behavioural direction in the project and it is still not
significant. `docs/RESULTS_E17.md`.

**Experiment 19 re-ran it with four times the notes to break the ties, and it
failed again**: real 0.2575 vs 0.749 ± 0.370, **4/37, p = 0.132** against a
floor of 0.024 (all 40: 4/40, p = 0.122). Only one tie this time; three
controls beat it outright. Across both runs the real connectome makes about a
third of the controls' strays and sits at roughly the 90th percentile of their
distribution — consistent, and short of the 95th that significance needs. By
the stopping rule declared in advance, **the stray endpoint is closed**: a
direction with a measured effect size, not a result. `docs/RESULTS_E19.md`.

Those three are the only behavioural comparisons pointing the real connectome's
way. None is significant; only 4c was pre-registered, and it failed its declared
floor. Against them, on the same run as 4c, the real network is *behind* the
controls on lane-correctness (0.741 vs 0.809, 24/37).

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

*Two corrections to the size of this, both from experiment 16, neither of which
makes it a claim in the real connectome's favour.* First, **about half of the
gap was threshold selection.** Freezing the same policies and scoring them on
charts nobody tuned against takes the 1400 ms arm from 19/20 and a +0.282 gap
to **13/20, p = 0.667, and a +0.123 gap**; the real network was the only one of
the 21 to gain much from the change. Quote the held-out numbers, not the sweep
ones. Second, and more important, **`accuracy` is blind to stray presses**: it
is a judgment-weighted mean over notes, and a press landing on nothing costs
nothing. Held out, the controls make **2.21 strays per note against the real
network's 0.48, all twenty worse with no overlap**, while its hit rate is above
their mean. Some of what has been reported as controls playing better is
controls mashing. On the project's own declared evaluation reward the
comparison is null (0.545 vs 0.582, p = 0.571), and the apparent 0/40 under the
ridge-fitting penalty is **not a result** — that constant was picked after
seeing the strays. `docs/RESULTS_E16.md`.

*And then a third correction, from experiment 17, which is why this claim should
now be treated as open rather than settled.* **The deficit does not survive
declaring the threshold.** Sweeping theta and taking the accuracy argmax is not
finding each network's best operating point, it is finding how hard each one can
mash — the chosen value was the lowest offered for the real network and 19 of 20
controls. Fix theta at 1.5, the never-fitted default, run 40 controls on a fresh
chart set, and the real connectome scores **0.357 against 0.299 ± 0.191, level
at 14/40**, while hitting more notes than 34 of the 40. That is a *different
comparison* — other charts, other threshold, twice the controls — so it does not
overturn the 19/20 above, and it was a descriptive secondary with no inference
claimed. What it does is make the question live. **The honest state of claim 6
is that nobody currently knows**, and the registered test that would settle it
has not been run. `docs/RESULTS_E17.md`. Experiment 19 repeated the observation
on another fresh chart set, again as an uninferred secondary: 0.325 against
0.308 ± 0.197, 16/40 reaching it. Level again. `docs/RESULTS_E19.md`.

*The audit.* Reading the stored sweeps of experiments 7, 11 and 12 at the
declared θ = 1.5 (`docs/AUDIT_DECLARED_THRESHOLD.md`, plan written before the
numbers): experiment 7's no-delay comparison stays level and leans toward the
real network (4/20, p = 0.24, was 8/20); **experiment 11's deficit holds**
(17/20, gap 0.297 → 0.229), so the delay result is not a threshold artefact;
but experiment 12's gap at 1000 and 1400 ms shrinks from about 0.27 to about
0.07 (12/20, p = 0.62). At 450 ms the real network makes 13 counted presses,
below the guard of 20, so that arm is a fallback, not a measurement.

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

At the declared θ = 1.5 the eight-component arm's scored-chart lead is gone
(5/10) and **its stray result reverses**: the real network makes 1.225 strays
per note against the controls' 0.220 ± 0.194, worse than all ten. The other
three arms, and the male CNS arm of experiment 7, cannot be read at 1.5 because
the real network presses fewer than 20 times or not at all.
`docs/AUDIT_DECLARED_THRESHOLD.md`.

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

## The trained fly against rewired controls (experiment 21)

**Not supported, and reversed in direction.** Round 23's recipe was fitted
separately to the real connectome and to 20 degree-, weight- and
sign-preserving rewired controls, and all were scored once on the 30 held-out
maps. The real network scores **0.876 against 0.911 ± 0.016, and 19 of 20
controls beat it**: p = 0.952, −2.2 control SD, pre-registered with the
controls committed first (`docs/PREREGISTRATION_E21.md`). The recipe was
developed entirely on the real network, which favoured it, so the reversal is
the stronger for it. The gap is widest on fast jacks (0.153 against
0.378 ± 0.087, all twenty controls ahead) and holds (0.619 against 0.737, all
twenty ahead). The real network makes fewer stray presses than every control
(0.0024 against 0.0049), which is descriptive only.

A plausible mechanism, untested: the real connectome's much higher recurrent
gain (spectral radius 2.283 against 0.736 ± 0.117, the structural finding
above) keeps activity ringing, so quick repeats in one lane merge and hold
releases arrive late. `docs/RESULTS_E21.md`.

## Absolute performance, separately from any comparison

**Nothing in this section bears on the connectome-versus-rewired question.**
The capability work runs on the real connectome only, with no controls; the
comparison for the fly that actually plays is experiment 21, above.

**Real maps (experiment 20): 0.876 mean accuracy on 30 held-out 4K
difficulties from six songs** that no readout choice ever looked at: 0.933 /
0.891 / 0.707 up to 5.5 events/s, 5.5 to 8.5, and above. The readout
(round 23) is fitted on synthetic charts plus 6-second clips from the three
tuning songs, 102 clips taken only from even-numbered segments. The best
readout fitted on synthetic charts alone (round 15) scores 0.862 on the same
maps (0.935 / 0.871 / 0.677), and the one first played on real maps 0.576.
Round 23 is better on 22 of 30. Taps 0.940, chords 0.938, the note after a hold
0.704 and holds 0.619 against round 15's 0.922, 0.922, 0.589 and 0.599. Fast
jacks are unchanged at 0.153, and they and holds are two thirds of what is
lost. 200 fitted parameters. Quote the held-out numbers: the 17
tuning difficulties from three other songs were used to choose between
versions. Round 23 was chosen on their odd-numbered segments, which no fit
saw (0.815 against round 15's 0.772). `docs/RESULTS_E20.md`.

**Synthetic charts (experiment 18): 1.000 on single notes and chords up to 5
events/s, 0.973 / 0.810 / 0.713 on chords at 6.7 / 8 / 10**, holds 0.886–0.982,
on fresh charts, with 196 fitted parameters and the connectome frozen. Every
wall found so far was a protocol choice, not the network: chords were the
training set (the readout had only been fitted on single notes); density was
first the scroll speed (800 ms approach, now 250 ms), then the refractory and
the drive smoothing; holds were first invisible to the encoder, then missing
from the recordings the readout is fitted on. `docs/RESULTS_E18.md` has the
round-by-round table, including what did not help.

Two earlier statements here are superseded. Experiment 5's 0.92 on single notes
with 68 parameters (`docs/RESULTS_E5.md`) is no longer the best play, and "the
refractory never binds" was true only of uniform charts: dense random chords put
two notes in a lane inside 150 ms, and cutting it to 100 ms helped in round 13.

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
`docs/RESULTS_E12.md`. "The gap never closes" is a swept-threshold result: at
the declared θ = 1.5 it is about 0.07 at 1000 and 1400 ms (12/20), see claim 6.

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

**Experiment 16 then found that the eighth thing had never been varied because
nobody had noticed it was a choice.** All seven of those comparisons were scored
on `accuracy`, which cannot see a press that lands on nothing, and the two
populations differ on exactly that more than on anything else in the project.
The sentence above should be read as "none produces a comparison favouring the
real connectome *on a measure blind to stray presses*" — which is a weaker
sentence than it has been taken to be, and is why experiment 17 exists.
`docs/RESULTS_E16.md`.

**Experiment 17 then removed the eighth thing and the deficit went with it.**
All seven of those varied policies shared a procedure nobody had counted as a
choice: the threshold was picked by argmax over an accuracy sweep, on a measure
that cannot charge for pressing. Declare the threshold instead and the real
connectome is level on accuracy and ahead on hit rate. So the correct summary is
now: **seven parts of the untrained policy were varied and none helped, but all
seven were varied on top of a selection rule that was quietly optimising for the
controls' failure mode.** That does not mean the real connectome plays better —
the pre-registered endpoint failed — it means the project's central negative
result rests on a procedure that is now known to be biased, and has to be redone.
`docs/RESULTS_E17.md`.
