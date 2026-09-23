# A fruit fly connectome plays osu!mania

A virtual fly whose nervous system is taken from a real *Drosophila* connectome,
wired up to a four-key rhythm game.

Notes falling toward a judgment line are projected onto the fly's simulated
compound eyes; activity propagates through 19,367 real neurons and 729,558 real
synaptic connections from the FlyWire whole-brain reconstruction; the fly's
descending neurons — its actual output to the legs — are grouped into four
channels and read as D / F / J / K.

**Current state: all 12 steps built; eleven experiments run.** The fly plays,
and plays well: the best readout reaches 0.92 accuracy on held-out charts with
68 parameters and the connectome frozen. Whether the *real* wiring plays better
than matched random wiring is a separate question, and the answer has got more
negative every time the controls were treated better — as of experiment 11 no
behavioural comparison favours the real connectome. Two structural
measurements do survive, at p = 0.024 and replicated on a second connectome.
Finding the regime in which the network could play at all turned out to be the
main event of the first session — see
[What changed](#what-changed-when-the-fly-started-playing).

```
                 osu!mania lanes  D    F    J    K
                                  │    │    │    │
   cylindrical arena, azimuth   -60  -20  +20  +60 deg
                                  ╰────┬────╯
                                       ▼
                     8,452 R1-6 photoreceptors  (real retinotopy,
                                       │         fitted to the lamina sheet)
                                       ▼
                      optic lobe ─► visual projection ─► central brain
                        6,443            1,260              1,566
                                       │
                                       ▼
                       1,303 descending neurons   (the brain's real
                                       │           output to the legs)
                              ┌────────┼────────┐
                            T2L   T1L    T1R   T2R
                             │     │      │     │
                             D     F      J     K
```

> **Reading this repository:** the sections below are written in the order the
> experiments happened, and seven of them were later weakened or corrected by a
> better control. **[`docs/CLAIMS.md`](docs/CLAIMS.md) is the single current
> statement of what is and is not supported**, and supersedes anything here
> that disagrees with it.

## The result so far

> **Does spatially different visual stimulation reliably cause different activity
> at the four motor outputs?**

Yes, clearly.

| lane decoding accuracy (chance 0.25) | real connectome |
|---|---|
| descending-neuron population (1,303 cells) | **0.99** |
| four anatomically pooled channels | **0.72** |
| untrained "press the loudest channel" policy | **0.57** |

Lane identity arrives essentially intact at the descending neurons, and survives
pooling into four anatomical groups well enough that a policy with *no learning
at all* gets more than twice chance.

**Does the real wiring beat random wiring at playing?** **On behaviour, no.**
Eleven experiments later, every behavioural comparison has been run under a
protocol that gives each control its own best operating point, and none favours
the real connectome. What survives is structural and is set out in
[`docs/CLAIMS.md`](docs/CLAIMS.md).

The rest of this section is **the answer as it stood at experiment 1**, kept
because how it fell apart is the most useful thing in this repository. It
looked strong: against 15 degree-matched rewired networks the real connectome
won on every metric that did not let a trained decoder compensate — 0/15
controls reached it on untrained policy accuracy (+1.9 SD), on channel
modulation depth (+3.7 SD), or on the note-approach timing signal (+2.0 SD).
Even then p = (n+1)/16, so **0.062 was the best p-value 15 controls could
produce**, and the metric that let a trained decoder compensate already showed
a much smaller gap (3/15). Each of those margins shrank as the controls were
given fairer treatment — seven times, across experiments 5 to 11.

Two findings worth flagging:

- At the *population* level the rewired control decodes lanes just as well as the
  real connectome (0.996 vs 0.992). That is not a bug — a random projection of an
  8,452-dimensional retinal input preserves almost everything. **Information
  preservation and useful structure are not the same thing**, and without the
  control, 0.992 would have looked like a result about the connectome.
- The gap grows as the readout gets dumber. The freer the decoder, the less the
  wiring matters. That was a prediction about the learning stage rather than a
  description of this one, and experiment 5 confirmed it in closed-loop play:
  with the readout fitted in closed form the real network plays far better than
  it ever has (0.92) and no better than its rewired controls.

**[`docs/RESULTS.md`](docs/RESULTS.md) has the full table, the control-by-control
breakdown, the figures, and the caveats.**

## What changed when the fly started playing

Experiment 1 measured every response 300 ms after a reset. The game never
resets, and run continuously the calibrated network is **chaotic**: with a blank
visual field it never settles, and its ongoing activity is the same size as a
note's effect on the four channels. The cause is the calibration — asking every
neuron's output to vary O(1) across stimuli gives a recurrent loop gain of ~8,
and it is self-consistent, so lowering the gain does not help.

The fix is one parameter. Flooring each neuron's calibrated input spread at 30×
the median (`model.build(regime="play")`) collapses the per-neuron sensitivity
normalisation into per-neuron bias plus a global gain cap. The blank field
becomes a fixed point, the static lane result is unchanged or better (untrained
argmax 0.567 → 0.567; 4-channel decoder 0.721 → 0.917), and the game becomes
playable. And a new connectome-specific fact appears: at that fixed point the
**real wiring has spectral radius 2.3 against 0.7 for degree-matched rewired
networks** — the real optic lobe contains structured recurrent loops that
randomisation destroys.

Full account, including what experiment 1's numbers now mean:
[`docs/CALIBRATION.md`](docs/CALIBRATION.md), "Ongoing activity".

## The fly plays (experiment 2)

Untrained — anatomical wiring, one shared threshold, no learning — fraction of
presses in the correct lane, by curriculum stage:

| stage | real | rewired ×3 | shuffled retinotopy ×3 | shuffled channels ×3 |
|---|---|---|---|---|
| one lane | **1.00** (acc 0.95) | 0.17 | 0.32 | 0.00 |
| four lanes in sequence | **1.00** | 0.22 | 0.46 | 0.28 |
| random lanes | **0.56** | 0.27 | 0.40 | 0.18 |
| chords | **0.63** | 0.45 | 0.50 | 0.27 |
| varied tempo | **0.53** | 0.33 | 0.45 | 0.19 |

Learning (20 readout parameters, reward-modulated perturbation, connectome
frozen), held-out accuracy on random charts after 30 episodes: real **0.30**
from the anatomical wiring and **0.44** (peak) from a blank readout; the two
trained rewired networks reach 0.06 / 0.25 and 0.18 / 0.23.

Three controls per family, so the smallest p available is 0.25 — the direction
is consistent, the size is large, and none of it is significant yet.
**[`docs/RESULTS_E2.md`](docs/RESULTS_E2.md)** has the tables, figures and the
caveats, including the ones about the learner.

Experiment 3 re-ran the learning comparison with an annealed learner, eight
rewired controls, eight channel-shuffled controls and three conditions. The gap
between real and rewired orders by how constrained the learning is: thresholds
only, real 0.21 vs 0.06 ± 0.05 (0/8 controls reach it); from the anatomical
wiring, 0.24 vs 0.12 ± 0.08 (1/8); from a blank readout, 0.27 vs 0.20 ± 0.11
(2/8). The real wiring supplies a starting point a small readout can exploit,
not a higher ceiling for one that learns from scratch — which is what
experiment 1 predicted. Shuffling the *channel labels* is the harsher control
in the blank condition (0.08 ± 0.08, 0/8): what a blank readout has to find is
a mapping onto coherent groups of descending neurons. The untrained lane result
survives photoreceptor noise, and the spectral-radius gap holds at n = 6 per
family (real 2.28, rewired 0.78 ± 0.16).
**[`docs/RESULTS_E3.md`](docs/RESULTS_E3.md)** — which has since been re-run
under the corrected wiring rule. The real network is unchanged and the controls
improve, so thresholds-only goes 0/8 → 1/8 and the anatomical-wiring condition
1/8 → 3/8. The ordering now depends on the metric: it holds on area under the
learning curve (1/8 → 2/8 → 4/8) and breaks on final accuracy
(1/8 → 3/8 → 2/8). Thresholds-only is the condition that survives best.

Experiment 4 asked whether those two properties of the real wiring — high
recurrent gain and good untrained lane choice — are one fact or two. Across 20
rewired graphs they are uncorrelated (Spearman ρ = 0.20, p = 0.39): gain does
not explain lane choice. With 20 controls the untrained lane result reached
**0/20, p = 0.048** — real 0.82 vs rewired 0.29 ± 0.15 — at the fixed threshold
those experiments used. **[`docs/RESULTS_E4.md`](docs/RESULTS_E4.md).**

Experiment 6 asked what that untrained advantage is made of, and corrected its
p-value. The real connectome is the only network of 21 whose four channels
admit **a single threshold** that fires each key on its own lane and not the
others (0/20 controls, as is its channel selectivity) — which is exactly the
policy's requirement and exactly what experiment 4's per-lane margin could not
see. But what predicts play *among* the controls is different again: how spread
out the four channels' peak times are (ρ = +0.57, p = 0.009), because four
channels that peak together cross one threshold together and press all four
keys. And the correction: experiments 2–4 fixed θ = 1.5, which is the real
network's best and almost never a control's. Give every network its own best
threshold and the gap halves — real 0.73 vs 0.43 ± 0.15, **1/20, p = 0.095**.
About a third of the published untrained gap was the threshold.
**[`docs/RESULTS_E6.md`](docs/RESULTS_E6.md).**

Experiment 7 took the obvious next step and swapped the wiring rule's criterion
for the one that discriminates, then re-ran the fair protocol. The new rule
works — it widens the band on 15 of 21 networks — but the real connectome was
*already at its optimum under the old rule*, so only the controls improve.
Untrained accuracy ends level (real 0.196 vs 0.186 ± 0.075, **8/20, p = 0.43**)
and lane-correctness stays at 1/20, p = 0.095. It also retracts experiment 6's
central claim: with each network wired by the rule that optimises the band,
**5 of 20 controls match the real network's band**, so it is not the only
network that admits a single working threshold. Its companion claim, channel
selectivity, was re-measured the same way and appeared to survive — real 0.79
vs 0.50 ± 0.17, **1/20, p = 0.095** — so the two came apart and selectivity
looked like the durable one. Experiment 14 later put that to a pre-registered
test at n = 40 and it failed. Three experiments in a row, a gap shrank as soon as the controls
were given a fairer procedure, which is by now the most robust finding here.
**[`docs/RESULTS_E7.md`](docs/RESULTS_E7.md).**

Experiment 8 went after the one cap that has nothing to do with the connectome:
every network's channels peak 200–600 ms *before* the note arrives, because a
note is visible from spawn and the total light reaching the eye barely changes
as it falls. A ventral gate plus a looming note halves the lag (365 → 185 ms
across networks) and lifts the real network to 0.808 lane-correct and 0.246
accuracy — but the controls gain as much, so the comparison weakens again
(3/12 → 5/12 on accuracy), and the front end that does it assumes the fly sees
only the bottom third of the playfield and that notes grow as they fall. Both
stay off by default. The finding worth keeping is the ceiling: **the spread of
the four channels' peak times is set by the network's own dynamics and no eye
removes it**, so the next timing effort belongs in the readout.
**[`docs/RESULTS_E8.md`](docs/RESULTS_E8.md).**

Experiment 9 gave the two surviving structural claims a proper treatment — 72
networks, both connectomes. Rewiring the topology collapses the spectral radius
(2.28 vs 0.73 ± 0.09, **0/40, p = 0.024**; male CNS 2.06 vs 0.65, 0/10) and
raises the readout population's dimensionality (same counts on PC1, on the top
four components, and on the gain-invariant participation ratio). At n = 40 these
are the only results in the project below 0.05, and the only ones that carry no
protocol caveat. They are two
*independent* properties: within every control family the correlation between
them is ≈ 0. Three qualifications came with it, and they matter. The
channel-label family cannot move either number by construction, so it is not a
control here. Retinotopy-shuffled networks have a **higher** radius than the
real connectome (20/20), so the claim is "rewiring collapses the radius", not
"the real radius is unusual" — the wording elsewhere has been corrected. And on
FlyWire the low dimensionality belongs to the *descending-neuron population*
specifically: the whole network and a size-matched random population show no
separation at all.
**[`docs/RESULTS_E9.md`](docs/RESULTS_E9.md).**

Experiment 5 changed the method. The fly is a frozen recurrent network with a
small linear readout — a reservoir computer — and osu!mania supplies free
supervision, because the notes fall whether or not the player presses. Fitting
the readout by ridge regression on one recording per network takes 40 seconds
instead of an hour, and the real network reaches **0.92 accuracy** on held-out
charts with 68 parameters, against 0.27 for the same network under reward-
modulated perturbation. It also **erases the connectome result**: at every
readout size the real network sits inside the rewired distribution (best 3/10,
p = 0.36). Both facts matter. The lane information is in every network; what
distinguishes the real one is that a small, constrained, reward-driven search
finds it. A third connectome-specific property fell out of the same data: the
real network's descending population is far more low-dimensional than any
rewired one's (PC1 0.38 vs 0.11–0.17), and because that low dimension is a
common mode carrying no lane information, *variance ordering is not information
ordering*. Replicated on the male CNS.
**[`docs/RESULTS_E5.md`](docs/RESULTS_E5.md).**

Experiment 10 went after the explanation experiment 5 had left on record — that
the real network transfers to chords badly because its amplified common mode
responds to both lanes at once — and every measurement made to test it points
the other way. **All thirteen networks respond to a two-note chord as the sum of
the two single notes to within 3–4%** (α = 0.985 real, 0.990 ± 0.010 rewired); a
2.28-radius recurrent network and a 0.63-radius one are equally linear about
chords. The real network's common-mode gain is slightly *sub*-additive, and
during a chord its two uninvolved channels sit at −0.11 z while 11 of 12
controls' rise. Refitting the readout on stage 4 fixes the `channels` deficit
(5/12, p = 0.46) and leaves `pca8` at 12/12 — where it is 12/12 on *single
notes* too, under the same fit, which no chord-specific limitation can explain.
What is left is a fitting pathology at the top-8-PC level, and that is a
hypothesis for a further experiment rather than a result.
**[`docs/RESULTS_E10.md`](docs/RESULTS_E10.md).**

Experiment 11 carried out experiment 8's prescription — put the timing fix in
the controller, so that a threshold crossing *schedules* a press rather than
making one — and it works for every network except the fly. Four per-key delays,
read off each network's own silent probe so no control inherits the real one's,
nearly triple untrained accuracy across the rewired family (0.186 → 0.539) and
move the real network from 0.196 to 0.242: **19 of 20 controls now beat it,
p = 0.95**. Untrained lane-correctness, the last behavioural comparison still
pointing the real connectome's way, goes from 1/20, p = 0.095 to **11/20,
p = 0.571**. The real network's channels cross so early that three of its four
keys want to wait 630–652 ms against a 600 ms gap between notes — the scheduled
press lands while the next note is on screen — and only 1 of 20 controls is in
that position; that is a candidate explanation and not a demonstrated one, since
within the control family longer delays go with *larger* gains (ρ = +0.39,
p = 0.088). The experiment also produced the mirror image of experiments 6 and
7: a first run capped the delays at 600 ms, which bound on 3 of the real
network's 4 lanes and 11 of 80 control lanes, was worth 0.2 accuracy, and
flipped the comparison the *other* way. It was caught before the number was
reported and the whole run repeated with the cap where it cannot bind.
**[`docs/RESULTS_E11.md`](docs/RESULTS_E11.md).**

Experiment 12 tested experiment 11's explanation and refuted it. If the real
network's trouble is that its 650 ms waits overrun a 600 ms note gap, widening
the gap should rescue it. Across 450, 1000 and 1400 ms with 20 controls each,
**the gap to the controls never closes** — 0.226, 0.297, 0.268, 0.282 — and at
1000 ms and above **not one of its lanes overruns the interval** while it stays
18/20 and 19/20. The mechanism is switched off and the deficit is unchanged, so
the note interval is not what puts it last. Two corrections came with that: it
*does* gain +0.29 from delays once the chart leaves room, so "cannot use them"
was wrong; and the delay-versus-gain correlation experiment 11 quoted against
itself (+0.39, p = 0.088) returns +0.30, p = 0.200 at n = 20 and is flat
elsewhere — it was noise. A third correction belongs to this write-up itself:
it first reported the real network's no-delay lane-correctness at wide intervals
as **1.000**, "its best showing anywhere", and that was the press-guard fallback
on 9 presses rather than a score. What is true is that without delays it presses
very rarely — 9 presses against 40 notes — and is in the right lane when it
does, which six of twenty controls also manage.
**[`docs/RESULTS_E12.md`](docs/RESULTS_E12.md).**

Experiment 13 went back to the male CNS with a readout not known in advance to
destroy the signal. Four readouts on the same networks, charts and threshold
grid: on the four anatomical leg-motor pools the real connectome loses 9/10,
and on eight principal components of *the same 348 neurons* it wins 1/10. That
confirms experiment 7's suspicion — **the male CNS reversal is the pooling, not
the connectome.** But the held-out phase takes the interesting half back: replay
each network's chosen policy on charts nothing was re-tuned for and the real
network's PC accuracy halves, 0.258 → 0.122, while the controls hold at 0.131 →
0.138, so 1/10 becomes 6/10. It had been fitting its threshold to the scored
charts harder than the controls were. The anatomical disadvantage survives
held-out intact. So removing the pooling removes a real handicap and leaves the
real network **level** with its controls, not ahead.
**[`docs/RESULTS_E13.md`](docs/RESULTS_E13.md).**

Experiment 14 is the first comparison here that was **pre-registered**. Seven
times a gap had shrunk once a comparison was made fairer, and every one of
those was caught after the fact — which shows the mistake is easy to make, not
that it stopped happening. So the protocol was frozen and tagged before
anything ran, one primary endpoint was named (channel lane-selectivity: no
threshold, no presses, no chart, so it could inherit none of the earlier
failure modes), and **all forty controls were run and committed to git before
the real network was measured once**. The result: real **0.790** against
0.547 ± 0.174, **4/40, p = 0.122**, and the claim moves to not supported. What
makes it interesting is what did not change — the real network scored 0.79 at
n = 20 and 0.790 here, with an identical procedure. **Twenty more controls were
the entire difference.** So this eighth correction has a cause the other seven
did not: not an unfair procedure but plain undersampling, which no fairness fix
would have caught. Its lesson applies backwards across the whole project — at
twenty controls a single exceedance already gives p = 0.095, so **every "0/20"
and "1/20" here reads stronger than it is**. The exception, measured on the
same forty networks, is the spectral radius: 2.283 vs 0.733 ± 0.090, 0/40,
identical to experiment 9. A claim that is really there does not soften when
the controls double.
**[`docs/RESULTS_E14.md`](docs/RESULTS_E14.md)**, protocol in
**[`docs/PREREGISTRATION.md`](docs/PREREGISTRATION.md)**.

## Quick start

```bash
pip install numpy pandas pyarrow scipy scikit-learn matplotlib

# ~130 MB of public connectome data (see data/SOURCES.md)
curl -L -o data/Connectivity_783.parquet \
  https://raw.githubusercontent.com/philshiu/Drosophila_brain_model/main/Connectivity_783.parquet
curl -L -o data/neuron_annotations.tsv \
  https://raw.githubusercontent.com/flyconnectome/flywire_annotations/main/supplemental_files/Supplemental_file1_neuron_annotations.tsv

python -m flyosu.connectome          # build the cache (~25 s)
python -m flyosu.retina              # check the retinotopic map
python -m experiments.e1_sensorimotor  # experiment 1 (~1 h with all controls)
python -m experiments.figures
python -m experiments.e2_play          # experiment 2 (~2 h at N_CTRL=3)
python -m experiments.figures_e2
python -m experiments.e3_learning      # experiment 3 (~1.5 h at N_LEARN=4)
python -m experiments.e3_stability
python -m experiments.figures_e3
python -m experiments.e4_covariate     # experiment 4 (~25 min at N_SEEDS=20)
python -m experiments.figures_e4
python -m experiments.e5_reservoir     # experiment 5 (~2 h at N_CTRL=10)
python -m experiments.figures_e5
python -m experiments.e6_timing        # experiment 6, phase 1 (~6 min)
PHASE=2 python -m experiments.e6_timing     # per-key thresholds (~17 min)
PHASE=3 python -m experiments.e6_timing     # threshold sweep (~32 min)
python -m experiments.figures_e6
python -m experiments.e7_wiring        # experiment 7 (~50 min)
python -m experiments.figures_e7
python -m experiments.e9_structure     # experiment 9 (~20 min, 72 networks)
python -m experiments.e10_chords       # experiment 10 (~55 min at N_CTRL=12)
python -m experiments.e11_delays       # experiment 11 (~32 min at N_SEEDS=20)
```

`make experiment2 … experiment9` wrap these with the seed counts the published
numbers used; the male CNS variants are `DATASET=malecns`.

Watch it play:

```bash
python run_play.py                          # stage 2, untrained, frame by frame
python run_play.py --stage 3 --learn 20     # 20 episodes of readout learning first
python run_play.py --control rewired        # the same on a rewired network
python run_play.py --stability              # is the blank field a fixed point?
python play_osu.py map.osu --sink log       # simulate a real 4K beatmap, replay presses
```

Using it:

```python
from flyosu import model, mania, play

fly    = model.build(regime="play")       # cached after the first run
player = play.Player.untrained(fly)       # label-free normaliser + anatomical wiring
result = player.play(mania.stage_chart(3, n_notes=20))
print(result.summary())                   # acc .. hit .. MAX:.. 300:.. ... stray ..

r = fly.look([(-60.0, -25.0, 1.0)])       # the experiment-1 static probe still works
```

## What is real and what is assumed

The connectome is a wiring diagram, not an executable brain. Being clear about
the seam is most of the point.

**Measured** — 139,262 neurons and 15,091,983 directed edges with synapse counts
(FlyWire v783); excitatory/inhibitory identity per edge from neurotransmitter
prediction; cell type, hemisphere and soma position for every neuron; the
retinotopic arrangement of the photoreceptors, fitted to their real positions.

**Assumed** — neuron dynamics; absolute synaptic strength; each cell's
excitability and gain; how a falling note becomes light on the eye; how
descending neurons map onto four keys.

The assumptions were not free choices. Three dynamical models were tried and
discarded first, including a faithful reproduction of the published whole-brain
LIF parameters, which turns out to have no stable operating point between
"signal dies in layer 1" and "the whole brain saturates". **[`docs/CALIBRATION.md`](docs/CALIBRATION.md)
records what failed, why, and exactly what the working model adds.** Read it
before trusting any number here.

Naming caveat: `T1L / T2L / T1R / T2R` are nicknames for the four descending
groups, not claims about which leg neuromere each innervates. FlyWire covers the
brain only, so the descending neurons' targets in the ventral nerve cord are not
in this dataset.

## Layout

```
run_fly.py        poke the fly from the command line (static probes)
run_play.py       watch the fly play in the terminal; optional learning first
play_osu.py       simulate a .osu beatmap and replay the presses (log or keyboard)
flyosu/
  connectome.py   load FlyWire v783, join annotations, cache
  malecns.py      the same loader for male CNS v1.0 (brain + VNC), for replication
  retina.py       photoreceptor -> (azimuth, elevation) retinotopic map
  subgraph.py     rank neurons on the retina -> descending pathway
  sim.py          LIF engine (kept, with its failure modes) + rate engine
  outputs.py      descending neurons -> four channels, defined blind to stimulus
  model.py        assembles and calibrates a runnable fly; regimes; controls; stability
  mania.py        4K osu!mania: notes, charts, curriculum, clock, judge   (steps 5, 8)
  encoder.py      playfield -> light on the eye; declared variants      (step 6)
  controller.py   channels -> keys: normaliser, threshold policy, per-key delays (step 7)
  play.py         the game loop that couples all of the above
  learn.py        reward-modulated perturbation of the readout            (step 9)
  reservoir.py    the same readout fitted in closed form (ridge), + population PCA
  probes.py       time-resolved channel responses: shared threshold, timing, chords
  beatmap.py      .osu parser and writer                                   (step 11)
experiments/
  e1_sensorimotor.py  experiment 1: tuning, decoding, approach, chords
  e1b_variance.py     how much of the control spread is estimation noise
  e2_play.py          experiment 2: stability, static probe, untrained play, learning
  e3_learning.py      experiment 3: annealed learning in three conditions, noisy untrained
  e3_stability.py     spectral radius across control seeds
  e4_covariate.py     radius vs untrained behaviour across 20 rewired graphs
  e5_reservoir.py     closed-form readouts of four sizes, real vs three families
  e6_timing.py        what predicts untrained play; the threshold sweep
  e7_wiring.py        a wiring rule chosen on the shared-threshold band
  e9_structure.py     spectral radius and dimensionality, both datasets
  e10_chords.py       chords: fit on stage 4, and chord additivity
  e11_delays.py       per-key delays: a crossing schedules a press
  e12_interval.py     does the note interval explain the delay result?
  e13_malecns_readout.py  male CNS: four readouts on the same networks
  e14_prereg.py       the pre-registered comparison: controls first, real network last
  e15_trigger.py      firing edge: crossing vs peak vs falling edge
  e16_heldout.py      the same frozen policies on charts nobody tuned against
  e17_strays.py       pre-registered: stray presses, declared threshold
  figures.py / figures_e2.py / ... / figures_e6.py / figures_e7.py
  refresh_c.py, restats.py
tests/test_pipeline.py  32 checks on the network side
tests/test_play.py      67 checks on the game side, incl. the probes and firing edges
tests/test_reservoir.py 20 checks on the closed-form readout
tests/test_malecns.py   the male CNS loader, pinning the numbers docs/MALECNS.md quotes
docs/CALIBRATION.md     every modelling decision the data did not make, incl. the regime
docs/MALECNS.md         the second connectome: loader, decisions, what transfers
docs/CLAIMS.md          what is and is not supported, current
docs/PREREGISTRATION.md protocol for experiment 14, frozen before it was run
docs/RESULTS.md         experiment 1
docs/RESULTS_E2.md      experiment 2
docs/RESULTS_E3.md      experiment 3
docs/RESULTS_E4.md      experiment 4
docs/RESULTS_E5.md      experiment 5
docs/RESULTS_E6.md      experiment 6
docs/RESULTS_E7.md      experiment 7
docs/RESULTS_E8.md      experiment 8
docs/RESULTS_E9.md      experiment 9
docs/RESULTS_E10.md     experiment 10
docs/RESULTS_E11.md     experiment 11
docs/RESULTS_E12.md     experiment 12
docs/RESULTS_E13.md     experiment 13
docs/RESULTS_E14.md     experiment 14
data/SOURCES.md         where the data comes from, with citations
```

Try it:

```bash
python run_fly.py                    # the four lanes side by side
python run_fly.py --fall D           # watch a note descend
python run_fly.py --sweep            # azimuth tuning, as text
python run_fly.py --control rewired  # the same, on a randomised network
python -m tests.test_pipeline        # 32 checks
python -m tests.test_play            # 67 checks
python -m tests.test_reservoir       # 20 checks
```

## Where this is

```
 1  connectome subgraph          done   19,367 neurons on the visual->motor path
 2  visual neuron identification done   8,452 R1-6 with a fitted retinotopy
 3  visual stimulus              done   point sources on a cylindrical arena
 4  sensorimotor test            done   lanes are decodable at the motor output
 5  mania environment            done   4K notes, curriculum, osu!mania judge
 6  sensory encoder              done   playfield -> eye (static; adaptation optional)
 7  fly controller               done   20-parameter threshold policy; per-key delays optional
 8  scoring                      done   MAX/300/200/100/50/MISS, accuracy, timing error
 9  plasticity                   done   reward-modulated perturbation; ridge fit as a ceiling
10  training experiments         run sixteen times e1-e16, two connectomes; best play 0.92 (ridge, 68 params)
11  beatmap parser               done   .osu v14 mania, both directions
12  osu! integration             built  simulate-then-replay driver; not verified live
```

Where the science is now: the connectome-vs-random comparison has moved from
"can a decoder tell the lanes apart" (experiment 1: yes, and so can a random
network) to "does the fly press the right key with no learning" (experiment 2:
yes, and random networks mostly do not) to "how much of that survives a better
readout" (experiment 5: none of it) to "what is the untrained advantage made
of, and how much of it was our threshold" (experiment 6: a shared-threshold
property, and about a third of it was the threshold) to "what happens when the
controls get every advantage the real network had" (experiment 7: the accuracy
gap closes, and the shared-threshold property is retracted) to "what happens
when the controller is allowed to wait" (experiment 11: the last behavioural
gap closes too).

**Every behavioural comparison has now been run under a fair protocol and none
favours the real connectome.** The closest is thresholds-only learning — real
0.211 vs rewired 0.101 ± 0.079, 1/8, **p = 0.22** — directional and not
significant. Untrained accuracy is 19/20 against (p = 0.95), untrained
lane-correctness 11/20 (p = 0.571), and the supervised ceiling shows no
advantage at any readout size. The one non-behavioural measurement in that
territory, how lane-selective the four channels are, went to a pre-registered
test at n = 40 and came back **4/40, p = 0.122** (experiment 14). The male CNS
comparison, re-run with a readout that can see lane identity, reaches level and
not ahead (experiment 13). The honest summary is that **the gap shrank every
time the comparison was made more careful**, and that is now the most robust
thing here — twelve times over, and twice what dissolved was an *explanation*
rather than a difference. The twelfth is the first one to run the other way:
experiment 16 shrank a gap that had been *against* the real connectome.

Experiment 15 closed the controller as a hiding place: no firing edge — upward
crossing, channel peak or falling edge — favours the real connectome, and the
falling edge fixes the timing almost completely (610 ms early becomes 86 ms)
without converting any of it into accuracy.

Experiment 16 then found that the measure itself had a hole in it. Every one of
those comparisons was scored on `accuracy`, which is a judgment-weighted mean
over **notes** and is blind to a press that lands on nothing. Scored on charts
nobody tuned against, the rewired controls make **2.21 stray presses per note
against the real network's 0.48, all twenty worse with no overlap**, while the
real network's hit rate sits above their mean. Some of what has been reported
as controls playing better is controls mashing a measure that cannot charge
them for it. The same experiment also showed that about half the accuracy
deficit was threshold selection: held out, the 1400 ms arm goes from 19/20 and
a +0.282 gap to 13/20 and +0.123.

None of that is yet a result in the real connectome's favour — on the project's
own declared evaluation reward the comparison is null — and it was found after
the numbers were in rather than predicted. **Experiment 17 is the
pre-registered test of it**, with the endpoints, the charts and a declared
(not swept) threshold frozen and committed before the real network was built.

What still stands are the two measurements that need no behavioural protocol at
all: rewiring the topology **collapses the spectral radius** (2.28 vs
0.73 ± 0.09) and **raises the readout population's dimensionality** (PC1 0.38 vs
0.14 ± 0.02), both **0/40, p = 0.024** against degree- and weight-preserving
rewiring, both replicated on the male CNS, and shown to be independent of each
other (experiment 9). They are the only results in the project below p = 0.05
and the only ones no procedural correction has touched.
**[`docs/CLAIMS.md`](docs/CLAIMS.md)** carries the current list claim by claim,
with the control family attached to each — which matters, because the three
families are not interchangeable.

Step 12 is built, not verified: `play_osu.py` simulates the fly on a beatmap
and replays its presses against the wall clock through a pluggable sink
(logging always; keyboard via `pynput`). Nobody has yet pointed it at a live
client. It is not screen-capture vision — the fly sees the encoder's rendering
of the beatmap — and closing that loop is a separate project.

## Gotchas

Four hazards that have each cost a session, recorded here because they live
nowhere else.

**`accuracy` cannot see a stray press, and the best threshold is therefore not
the best policy.** `PlayResult.accuracy` is a judgment-weighted mean over
*notes*; a press that lands on nothing is counted by `n_stray` and is invisible
to it. So pressing more can only raise accuracy, and every "best threshold" this
project chose by `argmax(accuracy)` over a sweep landed on the **lowest value
offered** — 0.5, for the real network and 19 of 20 controls in experiment 11.
Sixteen experiments were scored that way before anyone noticed, and the two
populations turn out to differ on strays (2.21 vs 0.48 per note) more than on
anything else measured. Never quote an accuracy figure from here without the
stray count beside it, and prefer `learn.reward`, which charges for both.

**The model cache is keyed on parameters, not code.** `model._key` hashes only
the build arguments, so any change to code feeding the calibration — retina,
encoder, sim — silently leaves two populations of models side by side in
`data/models`: cached-before and fresh-after, compared against each other
without warning. The calibration amplifies float-level differences: rewriting
the retina's Gaussian as `exp(c·θ·θ)` changed `drive()` by 10⁻⁷ and moved the
spectral radius by 2% (2.28 → 2.33). If you touch that path, either keep it
bit-identical and verify against the committed version, or bump the `v=` in
`model.build`'s cache key and rebuild everything — knowing that this
invalidates comparability with experiments 1–3.

**Experiment 2's learner seeds are unrecoverable.** That run seeded the learner
from Python's salted `hash(label)`, which differs between interpreter
processes. It was fixed to `zlib.crc32` and the seeds have been saved from
experiment 3 onward, so everything since is reproducible; `results/e2_play.json`
is not, and e2's learning streams cannot be regenerated bit-for-bit.

**Set `PYTHONUTF8=1`** (or pass `encoding="utf-8"` explicitly) for any script
that rewrites a file containing non-ASCII. `figures_e2.py` was once truncated to
0 bytes because Windows' cp1252 default choked on a `θ` in its own source. The
docs are full of θ, × and —, so this applies to almost any tooling run over
them.

## Citations

FlyWire connectome: Dorkenwald et al., *Nature* **634**, 124–138 (2024).
Annotations: Schlegel et al., *Nature* **634**, 139–152 (2024).
LIF parameters and the connectivity mirror: Shiu, Sterne et al., *Nature*
**634**, 210–219 (2024). Full details in [`data/SOURCES.md`](data/SOURCES.md).
