# A fruit fly connectome plays osu!mania

A virtual fly whose nervous system is taken from a real *Drosophila* connectome,
wired up to a four-key rhythm game.

Notes falling toward a judgment line are projected onto the fly's simulated
compound eyes; activity propagates through 19,367 real neurons and 729,558 real
synaptic connections from the FlyWire whole-brain reconstruction; the fly's
descending neurons — its actual output to the legs — are read as D / F / J / K,
originally as four anatomical channels (the diagram below) and now by a small
trained linear readout over the whole descending population.

[![Video: a fruit fly connectome plays osu!mania](https://img.youtube.com/vi/kp_HwA6wk5M/hqdefault.jpg)](https://www.youtube.com/watch?v=kp_HwA6wk5M)

**[Watch the video on YouTube](https://www.youtube.com/watch?v=kp_HwA6wk5M)**

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

**[`docs/CLAIMS.md`](docs/CLAIMS.md) is the single current statement of what is
and is not supported.** Each experiment has its own write-up (index below), and
[`docs/HISTORY.md`](docs/HISTORY.md) keeps the long narrative of how the project
got here.

## Current status

**How well it plays.** 0.876 mean accuracy on 30 held-out 4K difficulties from
six songs that no readout choice ever looked at. The connectome is frozen; the
only fitted part is a 200-parameter linear readout, fitted on synthetic charts
plus 6-second clips from three tuning songs (round 23). The best readout when
real maps were first played scored 0.576 on the same maps.

| held-out maps | difficulties | accuracy |
|---|---|---|
| up to 5.5 chord-events/s | 11 | 0.933 |
| 5.5 – 8.5 | 14 | 0.891 |
| above 8.5 (up to 13.7) | 5 | 0.707 |

Taps and chords are at 0.94. Holds (0.619) and fast jacks (a note in the same
lane within 150 ms of the last, 0.153) account for two thirds of what it loses.
Details: [`RESULTS_E20.md`](docs/RESULTS_E20.md) (real maps) and
[`RESULTS_E18.md`](docs/RESULTS_E18.md) (the recipe, round by round).

**Does the real wiring matter?** No behavioural comparison has favoured the real
connectome once the controls were treated fairly. Through experiment 15 the
answer got more negative with every fairer control. Experiments 16–19 found that
choosing thresholds by accuracy rewarded mashing. At a declared threshold the
untrained fly is level on accuracy with its controls, though still behind them
when the controller may delay its presses (experiment 11). It makes a third of the
stray presses, but that difference failed its pre-registered test twice. For the
trained fly, experiment 21 fitted the same recipe to the real connectome and to
20 rewired controls. **19 of 20 rewired networks played better** (0.911 ± 0.016
against 0.876, p = 0.952), even though the recipe was tuned on the real network.
The gap is widest on fast jacks and holds, which fits the real connectome's much
higher recurrent gain. Two structural findings survive, at p = 0.024 and
replicated on a second connectome.

**Watch it.** `demo/` is a browser replay of the fly on all 47 4K difficulties,
on an osu!mania-style stage with star ratings, score and the brain's activity.
It is built by `experiments/demo_replay.py`; serve the folder
(`python -m http.server -d demo`) and open `index.html`.

## Experiments

Comparison experiments test the real connectome against rewired controls;
capability experiments (18, 20) tune the real connectome only, with no controls.

| # | question | answer | write-up |
|---|---|---|---|
| 1 | Does visual position reach the motor output? | Yes: lanes decode at 0.99 from the descending neurons | [`RESULTS.md`](docs/RESULTS.md) |
| 2 | Can the fly play at all? | Yes, once a stable regime was found; untrained lane-correctness well above chance | [`RESULTS_E2.md`](docs/RESULTS_E2.md) |
| 3 | Does learning favour the real wiring? | Direction only, not significant; its recurrent gain is far higher | [`RESULTS_E3.md`](docs/RESULTS_E3.md) |
| 4 | Is recurrent gain why it picks lanes? | No: gain does not predict untrained play | [`RESULTS_E4.md`](docs/RESULTS_E4.md) |
| 5 | Does a closed-form readout favour it? | No: inside the rewired distribution at every size | [`RESULTS_E5.md`](docs/RESULTS_E5.md) |
| 6 | Where does the untrained advantage live? | In the shared threshold; its p-value was overstated | [`RESULTS_E6.md`](docs/RESULTS_E6.md) |
| 7 | Does a fairer wiring rule keep it? | No: the shared-threshold claim is retracted | [`RESULTS_E7.md`](docs/RESULTS_E7.md) |
| 8 | Can a different eye fix the timing? | It halves the lag and helps the controls as much | [`RESULTS_E8.md`](docs/RESULTS_E8.md) |
| 9 | Are the structural differences real? | Yes: spectral radius and dimensionality, 0/40, both connectomes | [`RESULTS_E9.md`](docs/RESULTS_E9.md) |
| 10 | Does it fail chords for a network reason? | No: refitting on chords fixes it | [`RESULTS_E10.md`](docs/RESULTS_E10.md) |
| 11 | Do per-key delays help? | Yes, for everyone except the real network | [`RESULTS_E11.md`](docs/RESULTS_E11.md) |
| 12 | Was the note interval the reason? | No | [`RESULTS_E12.md`](docs/RESULTS_E12.md) |
| 13 | Is the male CNS reversal the connectome? | No: it is the anatomical readout | [`RESULTS_E13.md`](docs/RESULTS_E13.md) |
| 14 | Pre-registered: are its channels lane-selective? | Not supported: 4/40, p = 0.122 | [`RESULTS_E14.md`](docs/RESULTS_E14.md) |
| 15 | Does a different firing edge help? | It fixes the timing and buys nothing | [`RESULTS_E15.md`](docs/RESULTS_E15.md) |
| 16 | What changes on charts nobody tuned on? | Half the gap was threshold selection; accuracy cannot see strays | [`RESULTS_E16.md`](docs/RESULTS_E16.md) |
| 17 | Pre-registered: fewer stray presses? | Direction yes, p = 0.073 | [`RESULTS_E17.md`](docs/RESULTS_E17.md) |
| 18 | Capability: how well can it play synthetic charts? | 1.000 up to 5 events/s; every wall was the protocol | [`RESULTS_E18.md`](docs/RESULTS_E18.md) |
| 19 | Pre-registered: the stray test with more notes | Fails, p = 0.132; endpoint closed | [`RESULTS_E19.md`](docs/RESULTS_E19.md) |
| 20 | Capability: how well does it play real beatmaps? | 0.876 on 30 held-out difficulties | [`RESULTS_E20.md`](docs/RESULTS_E20.md) |
| 21 | Pre-registered: does the trained fly need the real wiring? | No: 19/20 rewired networks play better | [`RESULTS_E21.md`](docs/RESULTS_E21.md) |

Also: an [audit](docs/AUDIT_DECLARED_THRESHOLD.md) of experiments 7, 11, 12, 13
and 15 at a declared threshold, and the frozen protocols for experiments
[14](docs/PREREGISTRATION.md) and [21](docs/PREREGISTRATION_E21.md).

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

Experiments 20 and 21 and the replay page also need the beatmaps: download the
nine sets listed in [`osumaps/README.md`](osumaps/README.md) into `osumaps/`.
Rebuilding the replay page's audio (`python experiments/demo_replay.py audio`)
also needs `ffmpeg` and `ffprobe` on the path.

`make experiment2 … experiment9` wrap these with the seed counts the published
numbers used; the male CNS variants are `DATASET=malecns`. Later experiments
give their run command at the top of their script and write-up.

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
  mania.py        4K osu!mania: notes, charts, curriculum, clock, judge
  encoder.py      playfield -> light on the eye; declared variants
  controller.py   channels -> keys: normaliser, threshold policy, per-key delays
  play.py         the game loop that couples all of the above
  learn.py        reward-modulated perturbation of the readout
  reservoir.py    the same readout fitted in closed form (ridge), + population PCA
  probes.py       time-resolved channel responses: shared threshold, timing, chords
  beatmap.py      .osu parser and writer
experiments/
  e1_sensorimotor.py … e21_trained_wiring.py   one script per experiment (see the index)
  e20_realfit.py      round 23: fit on real tuning-map clips, decide on unseen sections
  audit_declared.py   experiments 7/11/12/13/15 re-read at the declared threshold
  demo_replay.py      export the browser replay in demo/ (and `audio` to rebuild its sound)
  figures*.py, refresh_c.py, restats.py
tests/
  test_pipeline.py    32 checks on the network side
  test_play.py        115 checks on the game side, incl. probes, firing edges, jacks, holds and strays
  test_reservoir.py   20 checks on the closed-form readout
  test_experiments.py 24 checks on the replay export, the map loader and experiment 21's freeze guard
  test_malecns.py     the male CNS loader, pinning the numbers docs/MALECNS.md quotes
docs/
  CLAIMS.md           what is and is not supported, current
  RESULTS*.md         one write-up per experiment (see the index)
  HISTORY.md          how the project got here, including the full account of experiment 2
  CALIBRATION.md      every modelling decision the data did not make, incl. the regime
  MALECNS.md          the second connectome: loader, decisions, what transfers
  PREREGISTRATION*.md frozen protocols for experiments 14 and 21
  AUDIT_DECLARED_THRESHOLD.md  experiments 7/11/12/13/15 at a declared threshold
demo/                 browser replay of the fly on all 47 4K difficulties
osumaps/README.md     the nine beatmap sets to download (the .osz files are not committed)
data/SOURCES.md       where the data comes from, with citations
```

Try it:

```bash
python run_fly.py                    # the four lanes side by side
python run_fly.py --fall D           # watch a note descend
python run_fly.py --sweep            # azimuth tuning, as text
python run_fly.py --control rewired  # the same, on a randomised network
python -m tests.test_pipeline        # 32 checks
python -m tests.test_play            # 115 checks
python -m tests.test_reservoir       # 20 checks
python -m tests.test_experiments     # 24 checks, no network build; map checks skip without osumaps/
```

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
