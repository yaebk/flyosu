# A fruit fly connectome plays osu!mania

A virtual fly whose nervous system is taken from a real *Drosophila* connectome,
wired up to a four-key rhythm game.

Notes falling toward a judgment line are projected onto the fly's simulated
compound eyes; activity propagates through 19,367 real neurons and 729,558 real
synaptic connections from the FlyWire whole-brain reconstruction; the fly's
descending neurons — its actual output to the legs — are grouped into four
channels and read as D / F / J / K.

**Current state: all 12 steps built; experiment 2 run once at small n.** The
fly plays. Untrained, it hits 19/20 notes in a one-lane chart and presses the
right key for the nearest note far more often than any matched random network;
with 20 readout parameters learning from reward and the connectome frozen, it
improves on random charts where rewired networks mostly do not. Finding the
regime in which the network could play at all turned out to be the main event
of the session — see [What changed](#what-changed-when-the-fly-started-playing).

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

**Does the real wiring beat random wiring?** Probably, but the evidence is
suggestive rather than conclusive, and it got weaker rather than stronger as
the controls got better (experiments 5 and 6). Against 15 degree-matched rewired networks the
real connectome wins on every metric that does not let a trained decoder
compensate — 0/15 controls reach it on untrained policy accuracy (+1.9 SD), on
channel modulation depth (+3.7 SD), or on the note-approach timing signal
(+2.0 SD). But p = (n+1)/16, so **0.062 is the best p-value 15 controls can
produce**, and the metric that lets a trained decoder compensate shows a much
smaller gap (3/15 controls reach it).

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
**[`docs/RESULTS_E3.md`](docs/RESULTS_E3.md).**

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
selectivity, was re-measured the same way and *does* survive — real 0.79 vs
0.50 ± 0.17, **1/20, p = 0.095** — so the two came apart and selectivity is the
durable one. Three experiments in a row, a gap shrank as soon as the controls
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
```

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
  retina.py       photoreceptor -> (azimuth, elevation) retinotopic map
  subgraph.py     rank neurons on the retina -> descending pathway
  sim.py          LIF engine (kept, with its failure modes) + rate engine
  outputs.py      descending neurons -> four channels, defined blind to stimulus
  model.py        assembles and calibrates a runnable fly; regimes; controls; stability
  mania.py        4K osu!mania: notes, charts, curriculum, clock, judge   (steps 5, 8)
  encoder.py      playfield -> light on the eye; declared variants      (step 6)
  controller.py   channels -> keys: normaliser, 20-parameter threshold policy (step 7)
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
  figures.py / figures_e2.py / ... / figures_e6.py / figures_e7.py
  refresh_c.py, restats.py
tests/test_pipeline.py  28 checks on the network side
tests/test_play.py      55 checks on the game side, incl. the probes
tests/test_reservoir.py 17 checks on the closed-form readout
docs/CALIBRATION.md     every modelling decision the data did not make, incl. the regime
docs/RESULTS.md         experiment 1
docs/RESULTS_E2.md      experiment 2
docs/RESULTS_E3.md      experiment 3
docs/RESULTS_E4.md      experiment 4
docs/RESULTS_E5.md      experiment 5
docs/RESULTS_E6.md      experiment 6
docs/RESULTS_E7.md      experiment 7
docs/RESULTS_E8.md      experiment 8
data/SOURCES.md         where the data comes from, with citations
```

Try it:

```bash
python run_fly.py                    # the four lanes side by side
python run_fly.py --fall D           # watch a note descend
python run_fly.py --sweep            # azimuth tuning, as text
python run_fly.py --control rewired  # the same, on a randomised network
python -m tests.test_pipeline        # 28 checks
python -m tests.test_play            # 55 checks
python -m tests.test_reservoir       # 17 checks
```

## Where this is

```
 1  connectome subgraph          done   19,367 neurons on the visual->motor path
 2  visual neuron identification done   8,452 R1-6 with a fitted retinotopy
 3  visual stimulus              done   point sources on a cylindrical arena
 4  sensorimotor test            done   lanes are decodable at the motor output
 5  mania environment            done   4K notes, curriculum, osu!mania judge
 6  sensory encoder              done   playfield -> eye (static; adaptation optional)
 7  fly controller               done   20-parameter threshold policy
 8  scoring                      done   MAX/300/200/100/50/MISS, accuracy, timing error
 9  plasticity                   done   reward-modulated perturbation; ridge fit as a ceiling
10  training experiments         run five times  e2-e5; best play 0.92 accuracy (ridge, 68 params)
11  beatmap parser               done   .osu v14 mania, both directions
12  osu! integration             built  simulate-then-replay driver; not verified live
```

Where the science is now: the connectome-vs-random comparison has moved from
"can a decoder tell the lanes apart" (experiment 1: yes, and so can a random
network) to "does the fly press the right key with no learning" (experiment 2:
yes, and random networks mostly do not) to "how much of that survives a better
readout" (experiment 5: none of it) to "what is the untrained advantage made
of, and how much of it was our threshold" (experiment 6: a shared-threshold
property, and about a third of it was the threshold). — to "what happens when the controls
get every advantage the real network had" (experiment 7: the accuracy gap
closes). The honest summary is that **the behavioural gap shrank every time the
controls were given a fairer procedure**, and that is now the most robust thing
here. What still stands are the two measurements that need no behavioural
protocol at all — spectral radius (2.28 vs 0.78) and population dimensionality
(PC1 0.38 vs 0.11–0.17), both replicated on the male CNS. What does not: the
untrained accuracy advantage (8/20, p = 0.43) and the supervised ceiling
(experiment 5, no advantage at any readout size). Untrained lane-correctness
survives in direction at 1/20, p = 0.095.

Step 12 is built, not verified: `play_osu.py` simulates the fly on a beatmap
and replays its presses against the wall clock through a pluggable sink
(logging always; keyboard via `pynput`). Nobody has yet pointed it at a live
client. It is not screen-capture vision — the fly sees the encoder's rendering
of the beatmap — and closing that loop is a separate project.

## Citations

FlyWire connectome: Dorkenwald et al., *Nature* **634**, 124–138 (2024).
Annotations: Schlegel et al., *Nature* **634**, 139–152 (2024).
LIF parameters and the connectivity mirror: Shiu, Sterne et al., *Nature*
**634**, 210–219 (2024). Full details in [`data/SOURCES.md`](data/SOURCES.md).
