# A fruit fly connectome plays osu!mania

A virtual fly whose nervous system is taken from a real *Drosophila* connectome,
wired up to a four-key rhythm game.

Notes falling toward a judgment line are projected onto the fly's simulated
compound eyes; activity propagates through 19,367 real neurons and 729,558 real
synaptic connections from the FlyWire whole-brain reconstruction; the fly's
descending neurons — its actual output to the legs — are grouped into four
channels and read as D / F / J / K.

**Current state: step 4 of 12.** The pipeline exists and the sensorimotor
question has been answered. No learning yet, and no connection to the real osu!
client — both deliberate. See [Where this is](#where-this-is).

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
python -m experiments.e1_sensorimotor  # the experiment (~1 h with all controls)
python -m experiments.figures
```

Using it:

```python
from flyosu import model

fly = model.build()                       # cached after the first run
r   = fly.look([(-60.0, -25.0, 1.0)])     # a note in lane D at the judgment line
print(dict(zip(fly.readout.names, fly.channels(r))))
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
run_fly.py        poke the fly from the command line
flyosu/
  connectome.py   load FlyWire v783, join annotations, cache
  retina.py       photoreceptor -> (azimuth, elevation) retinotopic map
  subgraph.py     rank neurons on the retina -> descending pathway
  sim.py          LIF engine (kept, with its failure modes) + rate engine
  outputs.py      descending neurons -> four channels, defined blind to stimulus
  model.py        assembles and calibrates a runnable fly, plus the controls
experiments/
  e1_sensorimotor.py  the experiment: tuning, decoding, approach, chords
  e1b_variance.py     how much of the control spread is estimation noise
  figures.py          plots
  refresh_c.py        recompute one probe without re-running everything
  restats.py          recompute statistics from a saved results file
tests/test_pipeline.py  sanity checks that caught real bugs
docs/CALIBRATION.md     every modelling decision the data did not make
docs/RESULTS.md         experiment 1 written up, with the caveats
data/SOURCES.md         where the data comes from, with citations
```

Try it:

```bash
python run_fly.py                    # the four lanes side by side
python run_fly.py --fall D           # watch a note descend
python run_fly.py --sweep            # azimuth tuning, as text
python run_fly.py --control rewired  # the same, on a randomised network
python -m tests.test_pipeline        # 28 checks
```

## Where this is

```
 1  connectome subgraph          done   19,367 neurons on the visual->motor path
 2  visual neuron identification done   8,452 R1-6 with a fitted retinotopy
 3  visual stimulus              done   point sources on a cylindrical arena
 4  sensorimotor test            done   lanes are decodable at the motor output
 ─────────────────────────────────────
 5  mania environment            next
 6  sensory encoder              next
 7  fly controller
 8  scoring
 9  plasticity
10  training experiments
11  beatmap parser
12  osu! integration
```

Steps 5–8 are a straight build on what exists: `model.Fly` already takes a list
of `(azimuth, elevation, intensity)` targets and returns four channel
activations, and probe C shows the output tracks a note's approach
(|r| = 0.95 against elevation), which is the timing signal a scoring rule needs.

Step 9 is the one that needs a decision, and experiment 1 sharpens it. The
obvious move — backprop through the readout — would turn this into an ordinary
neural network with a connectome-shaped prior, and the results here predict that
a free decoder is precisely what *erases* the real-vs-rewired difference. So the
interesting question is not "can it learn" but **how fast, and with how
constrained a learning rule**. Candidates that keep the biology: reward-modulated
STDP; dopaminergic neuromodulation gating plasticity at specific synapses (the
fly's reward system in the mushroom body is well mapped, and those neurons are in
this dataset); or letting only a handful of readout parameters move while the
connectome stays frozen. The last is the cleanest experiment, because the
real-vs-rewired comparison then isolates what the topology contributes.

## Citations

FlyWire connectome: Dorkenwald et al., *Nature* **634**, 124–138 (2024).
Annotations: Schlegel et al., *Nature* **634**, 139–152 (2024).
LIF parameters and the connectivity mirror: Shiu, Sterne et al., *Nature*
**634**, 210–219 (2024). Full details in [`data/SOURCES.md`](data/SOURCES.md).
