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
suggestive rather than conclusive. Against 15 degree-matched rewired networks the
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
  wiring matters. That is a prediction about the learning stage, not just a
  description of this one.

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
  encoder.py      playfield -> light on the eye                            (step 6)
  controller.py   channels -> keys: normaliser, 20-parameter threshold policy (step 7)
  play.py         the game loop that couples all of the above
  learn.py        reward-modulated perturbation of the readout            (step 9)
  beatmap.py      .osu parser and writer                                   (step 11)
experiments/
  e1_sensorimotor.py  experiment 1: tuning, decoding, approach, chords
  e1b_variance.py     how much of the control spread is estimation noise
  e2_play.py          experiment 2: stability, static probe, untrained play, learning
  figures.py / figures_e2.py
  refresh_c.py, restats.py
tests/test_pipeline.py  28 checks on the network side
tests/test_play.py      46 checks on the game side
docs/CALIBRATION.md     every modelling decision the data did not make, incl. the regime
docs/RESULTS.md         experiment 1
docs/RESULTS_E2.md      experiment 2
data/SOURCES.md         where the data comes from, with citations
```

Try it:

```bash
python run_fly.py                    # the four lanes side by side
python run_fly.py --fall D           # watch a note descend
python run_fly.py --sweep            # azimuth tuning, as text
python run_fly.py --control rewired  # the same, on a randomised network
python -m tests.test_pipeline        # 28 checks
python -m tests.test_play            # 46 checks
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
 9  plasticity                   done   reward-modulated perturbation, connectome frozen
10  training experiments         run once  real vs 3 controls/family, 2 trained
11  beatmap parser               done   .osu v14 mania, both directions
12  osu! integration             built  simulate-then-replay driver; not verified live
```

Where the science is now: the connectome-vs-random comparison has moved from
"can a decoder tell the lanes apart" (experiment 1: yes, and so can a random
network) to "does the fly press the right key with no learning" (experiment 2:
yes, and random networks mostly do not) and "how fast does a 20-parameter
readout learn" (experiment 2: faster and higher for the real wiring, n = 2).
The measurement that most needs more controls is the learning one. The
measurement that is cheapest and newest is the spectral radius.

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
