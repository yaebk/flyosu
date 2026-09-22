# Handoff — Fruit Fly Connectome Plays osu!mania

Written at the end of the session that built steps 5–12 and ran experiments 2
and 3. Supersedes the previous handoff (which covered steps 1–4); everything
from that document that is still true is repeated here so this file stands
alone.

---

## Project goal (unchanged)

A purely software virtual fly whose nervous system comes from a real
*Drosophila* connectome, learning to play 4-key osu!mania. The point is not a
good osu! bot and not an ordinary neural network: the question is whether real
*Drosophila* connectivity provides useful structure for a novel visuomotor
timing task, measured against matched random networks.

---

## Where things live

The package root is `flyosu/flyosu/` (the zip was extracted into a subfolder;
`flyosu.zip` at the repo root is the *old* step-4 snapshot and is stale).

```
flyosu/flyosu/
  run_fly.py      static probes                 run_play.py   watch it play
  play_osu.py     .osu -> simulate -> replay     Makefile      data/cache/check/check-play/experiment{,2,3}/figures{,2,3}
  flyosu/         package (see README "Layout")
  experiments/    e1_*.py, e2_play.py, e3_learning.py, e3_stability.py, figures{,_e2,_e3}.py
  tests/          test_pipeline.py (28), test_play.py (46)
  docs/           CALIBRATION.md, RESULTS.md (e1), RESULTS_E2.md, RESULTS_E3.md
  results/        e1_*.json, e2_play.json, e3_learning.json, e3_stability.json, logs, fig1–12
  data/           SOURCES.md; raw data + caches are gitignored (make data)
  .venv/          gitignored; numpy pandas pyarrow scipy scikit-learn matplotlib
  scratch/        gitignored; this session's probe scripts, kept for reference
```

Environment used this session: Windows 11, Python 3.12, venv at
`flyosu/flyosu/.venv`. Both data files download fine from GitHub raw (no
sandbox egress problem this time). Full model build from cold: cache 25 s +
calibration 45 s per network.

---

## State of the 12 steps

```
 1–4  connectome, retina, stimulus, sensorimotor test   done (previous session)
 5    mania environment      done   flyosu/mania.py
 6    sensory encoder        done   flyosu/encoder.py  (static; adaptation variant built, untested in e2)
 7    controller             done   flyosu/controller.py  20 parameters
 8    scoring                done   in mania.py; osu!mania windows, OD-parameterised
 9    plasticity             done   flyosu/learn.py  reward-modulated perturbation
10    training experiments   run twice  e2_play.py (N_CTRL=3, N_LEARN=2); e3_learning.py (N_LEARN=4, 3 conditions, annealed)
11    beatmap parser         done   flyosu/beatmap.py, round-trip tested
12    osu! integration       built, NOT verified against a live client   play_osu.py
```

Tests: `python -m tests.test_pipeline` (28) and `python -m tests.test_play` (46),
all passing at the end of the session.

---

## The finding that shaped the session: the e1 network is chaotic

This is the most important thing for a successor to understand. Full account in
`docs/CALIBRATION.md`, "Ongoing activity".

- Experiment 1 measured every response 300 ms after a reset to zero. Run
  continuously with a blank field, the calibrated network **never settles**:
  channel sd 0.01–0.02, neurons flipping 0↔1, spectral radius 15 at the
  attractor, per-neuron gains up to 400. Persists at dt = 0.1 ms, so it is the
  model, not the integrator. A note moves the channels by 0.001–0.02, i.e. the
  signal is at or below the ongoing activity. Untrained lane accuracy in
  continuous play fell to 0.35–0.45; smoothing, common-mode rejection and
  projecting out blank-field PCs did not rescue it.
- Cause: the calibration `z = slope·(x−μ)/σ` makes every neuron O(1)
  stimulus-sensitive → recurrent loop gain ~8. It is **self-consistent** —
  lowering `slope` shrinks the fluctuations, shrinks σ, restores the gain.
  Verified at slope 1.0/1.5/2.0/2.5: signal-to-fluctuation ratio invariant.
  Running the e1-calibrated σ at a lower slope without recalibrating does not
  reach a fixed point either (radius > 5 at slope 2.5, so even 0.5 is unstable).
- Fix: `model.build(regime="play")` = `sigma_floor=30`. Every neuron's σ is
  floored at 30× the median → per-neuron *bias* homeostasis + one global gain
  cap. Fixed point; radius 2.28 (max Re 0.16). Floors 0.3/1/3/10/15/20 tried;
  boundary is between 20 and 25 at slope 2.5. Static probe B unchanged or
  better (argmax 0.567 → 0.567; 4-channel decoder 0.721 → 0.917).
- Consequence for the integrator: the surviving oscillatory modes (|λ| ≈ 2.3)
  are badly under-damped by Euler at dt = 5 ms. Everything game-side runs at
  **dt = 2 ms** (`model.DT_PLAY`). Experiment 1 was left at dt = 5.
- `model.build()` with no arguments is still the e1 regime, so e1 reproduces
  exactly. `Fly.settle()`, `Fly.stability()` (drift, spectral radius, max Re,
  max gain) are the new diagnostics. `tests/test_play.py` asserts the fixed
  point.

**New connectome-specific fact:** at the play-regime fixed point, real wiring
has spectral radius 2.28; degree/weight/sign-matched rewired networks have
0.72 ± 0.01 (3/3). Retinotopy-shuffled (same graph) 2.99; channel-shuffled (same
network) 2.28 exactly. The radius is a graph property and the real optic lobe's
recurrent loops are what randomisation destroys. Cheap to compute; put it in
every future control comparison.

---

## What experiment 2 found (n = 3 controls per family, 2 trained)

`docs/RESULTS_E2.md` has everything. The headline numbers:

- **Untrained, correct-lane fraction** (θ = 1.5): real 1.00 / 1.00 / 0.56 /
  0.63 / 0.53 across stages 1–5; best control family 0.17–0.50; 0/3 controls
  reach the real network in 13 of 15 cells. One-lane chart: 19/20 hit, all
  300s, −36 ± 0 ms.
- **Untrained accuracy on multi-lane charts is low for everyone** (0.06–0.23):
  one shared threshold fits one lane's amplitude. The J lane (+20° azimuth) is
  never pressed untrained — its notes read as D. Same J/K weakness as e1.
- **Learning** (stage 3, 30 episodes × 2 plays, held-out 3 charts): real 0.06 →
  0.30 from the anatomical wiring (lane-correct 0.65 → 0.91, timing error −36 →
  −4 ± 42 ms); real 0 → 0.44 at ep 20 → 0.32 from `W = 0`. Rewired #1/#2:
  0.06 / 0.25 (wired), 0.18 / 0.23 (blank).
- Every p ≥ 0.25. Direction consistent with e1's prediction (real wiring matters
  more the smaller the readout); nothing significant.

---

## What experiment 3 found (n = 4 rewired, annealed, three conditions)

`docs/RESULTS_E3.md`. The learning gap orders by how constrained learning is:

| condition | real | rewired ×4 | reach real |
|---|---|---|---|
| thresholds only | 0.21 | 0.09 ± 0.05 | 0/4 |
| from anatomical wiring | 0.24 | 0.13 ± 0.10 | 1/4 |
| from W = 0 | 0.27 | 0.24 ± 0.11 | 2/4 |

Reading: the real connectome supplies a starting point (an anatomical
lane→output mapping that is 0.65 lane-correct before any reward, and
lane-specific timing) that a constrained readout exploits; it does not raise
the ceiling of a readout learning from scratch. This is e1's prediction in a
third protocol. Untrained lane-correctness survives photoreceptor noise
(1.00/1.00/0.73/0.75/0.45 vs rewired 0.19–0.38). Spectral radius at n = 6:
real 2.28, rewired 0.78 ± 0.16 (max 1.12), same-graph families at the real
value (retinotopy family drifts to 3.0 and 2/6 are not fixed points at floor
30 — check stability per network for that family).

## What experiment 4 found (20 rewired graphs)

`docs/RESULTS_E4.md`. Spectral radius does not predict untrained lane choice
across random graphs (ρ = 0.20, p = 0.39), nor does the leading eigenvalue's
real part or the wiring rule's margin. The real network is off both
distributions independently. Untrained lane-correct: real 0.82 vs rewired
0.29 ± 0.15, 0/20, **p = 0.048** — the project's first sub-0.05 control
comparison. Lead worth following: the real network's wiring *margin* is
unremarkable (0.34 vs 0.37 ± 0.24) yet its play is far better, so the
untrained advantage is in something the play protocol exposes and the
single-note wiring probe does not — probably response timing, or behaviour
with several notes on screen.

## Male CNS (second connectome) — state at the end of the session

`docs/MALECNS.md` has all of it. Data downloaded (public GCS bucket, no
token; 1.1 GB in `data/malecns/`), loader `flyosu/malecns.py` (streams the
152 M-edge table, weight ≥ 2 → 15.3 M edges, 166,700 neurons, <1 GB, 17 s),
retinotopy `flyosu/retina_hex.py` (L1+L2 on the annotated column lattice —
the retina is outside the volume), readout `outputs.build_motor` (the real
T1/T2 leg motor neurons by side, 87/87/86/88), `model.build(dataset="malecns")`,
play floor 90 (`PLAY_FLOOR`; 30 is chaotic on this graph). 55 checks in
`tests/test_malecns.py`.

Results so far (n = 2 rewired):
- **Spectral radius replicates:** real 2.05 vs rewired 0.72 / 0.64. Same
  threefold gap as FlyWire, on an independent reconstruction of a different
  animal and sex. This is now the project's most robust connectome-specific
  fact.
- **Lane identity reaches real leg motor neurons** at 0.98 population
  decodability (rewired 1.00 — as on FlyWire, information preservation is not
  the discriminator).
- **The real leg pools respond as a common mode.** All four pools move
  together to a note anywhere (between-pool difference ~0.1 z); the untrained
  pooled readout presses nothing at any threshold, while rewired controls
  play by chance. FlyWire's channels were input-distinct *by construction*
  (k-means on input connectivity); real pools by neuromere × side are not.
  The untrained-pooled-readout result therefore does not transfer as-is.

Next on this dataset, in order: (1) label-free common-mode subtraction on
the four pools (cheap, probably insufficient); (2) a label-free
low-dimensional projection of the 348 motor neurons fitted on the calibration
ensemble (PCA on the ensemble responses, then the same 20-parameter
controller on the top components) — keeps the "small readout" discipline
while seeing within-pool pattern; (3) the e2/e3 protocols with ≥ 4 rewired
controls; (4) `Fly.stability()` for every control, since the play floor was
set on the real network only.

## What experiment 5 found (the method change)

`docs/RESULTS_E5.md`. The readout is now fitted in closed form
(`flyosu/reservoir.py`): record the descending population once per network
while charts fall past a silent controller, ridge-regress a per-frame press
target on label-free features, choose each lane's target-window position and
threshold offset by replaying the crossing rule through the judge. Forty
seconds per network instead of an hour, and the real network plays at 0.92
accuracy with 68 parameters.

It is also the project's clearest negative result: at every readout size the
real network is inside the rewired distribution (best 3/10, p = 0.36), where
the reward-trained comparison on the same networks and charts was 0/8. Read the
two together — the lane information is in every network, and the real wiring is
what makes it reachable by a constrained search. Two things a successor should
carry forward:

  * **Variance ordering is not information ordering.** The real network's
    descending population is much more low-dimensional than any rewired one's
    (PC1 0.38 vs 0.11-0.17; male CNS 0.63 vs 0.13-0.28), and the leading
    components are a common mode with no lane information. `pca4` therefore
    plays *worse* than the four anatomical channels on the real network and
    better on the controls. Population dimensionality is a third
    connectome-specific measurement, cheap, and it replicates across datasets.
  * **The judge does not punish stray presses.** Any fitting criterion built on
    accuracy alone will discover "fire every lane at every note" (it did, at
    1.5 strays per note). `reservoir.STRAY_PENALTY_FIT` is 0.4 for that reason;
    `learn.py`'s reward still uses 0.05, which is fine because perturbation
    never searches hard enough to find the degenerate solution.

## Design decisions a successor needs to know

1. **Controller = 20 parameters, connectome frozen.** `u = W·z_s + b`, press on
   upward zero-crossing, 150 ms refractory, 40 ms leaky integration on z. The
   normaliser (μ, σ per channel) is fitted on the 61-stimulus calibration
   ensemble from the fixed point — label-free, identical for all networks.
2. **The anatomical wiring is measured on a falling note**, not a static point:
   one silent note per lane, mean z over the second half of the descent, best
   1-1 assignment (24 permutations, 4.6 bits). Static point responses at the
   judgment line were tried first and disagree with the moving-note response,
   which is dominated by transients. The `W = 0` learning condition exists to
   remove even those 4.6 bits.
3. **Learning rule:** antithetic perturbation pairs on the same chart,
   `θ += lr·decay^k·½(R⁺−R⁻)·ε/σ`, σ = 0.2, lr = 1; e2 used no annealing, e3
   uses decay 0.97 per episode. σ was lowered from 0.3 after one smoke test on
   the real network — a small tuning-on-real bias, named in RESULTS_E2. Reward
   = accuracy − 0.05·strays/note. Seeds are recorded from e3 onward.
4. **Untrained play is deterministic and noise-free.** `Player(noise=0.03)`
   adds e1's photoreceptor noise; not run in e2 for time.
5. **Step 12 is simulate-then-replay**, not screen capture: the sim runs at
   ~1× real time with no slack, so the fly is run on the beatmap first and its
   presses are replayed against the wall clock (`--sink log|keyboard`,
   `--offset`, `--countdown`). Keyboard needs `pynput`; never tested live.
6. **Lanes, elevations, σ = 10° are imported from e1's values** (encoder.py) —
   the game the fly plays is the one it was measured on. Don't move lanes to
   exploit the frontal zone without declaring a separate experiment (e1 note).

---

## Known bugs and rough edges

- **The model cache is keyed on parameters, not code.** Any change to code
  that feeds the calibration (retina, encoder, sim) silently produces two
  populations of models: cached ones from before and fresh ones after. And the
  calibration amplifies float-level differences — a rewrite of the retina's
  Gaussian that changed `drive()` by 10⁻⁷ moved the spectral radius by 2%. If
  you touch that code path, either keep it bit-identical (verify against the
  committed version) or bump `v=` in `model._key` and rebuild everything,
  knowing that invalidates comparability with e1–e3.
- **Learner seeds in `results/e2_play.json` are unrecorded** — the running
  script used `hash(label)` (salted per process). Fixed to `zlib.crc32` and the
  seed is saved from e3 onward; e2's learning streams are not bit-reproducible.
- **The real network's learning curves flatten by episode 10** in two of three
  e3 conditions. Whether that is the 20-parameter readout's ceiling on four
  pooled channels or the learner is open.
- **Rewired #1 barely learns in any condition** and has the most negative
  leading eigenvalue (Re −0.69). Learning failure vs spectral properties across
  many controls is an open question.
- **Retinotopy-shuffled #2 is marginal** (drift 2 × 10⁻⁴ at 3 s, radius 3.08).
  Floor 30 has less margin for that family; a stability check per network is
  already in the results.
- **`figures_e2.py` was once truncated to 0 bytes** by a failed write on
  Windows (cp1252 default encoding + a `θ` in the source). Rewritten; the
  lesson is `PYTHONUTF8=1` or `encoding="utf-8"` for any script that rewrites
  files containing non-ASCII.
- Runtime: 1.4 ms wall per 2 ms game frame after the retina fix (19k neurons,
  730k edges, sparse matvec is now the main cost). A 20-note chart ≈ 9 s; 30
  learning episodes + 4 evals ≈ 7 min per condition. E3 as run: ~110 min for
  5 networks × 3 conditions + noisy sweeps.
- `Player.untrained()` costs ~25 s (settle + 61-stimulus normaliser + 4 falling
  notes). Cache it if you build many.

---

## What to do next, in order of value

0. **Male CNS** — see the section above; it is now the main line of work, and
   the FlyWire results are the first arm of a cross-dataset replication.


1. **More rewired controls through e3.** `RESUME=1 N_LEARN=8 python -m
   experiments.e3_learning` continues the saved run; each control ≈ 22 min for
   all three conditions. Eight would take the p floor to 0.11.
2. **The channel-shuffle family through e3's three conditions.** It keeps the
   graph and destroys only the output grouping's relation to the lanes, which
   is exactly what the thresholds-only result says matters. Add it to the plan
   list in `e3_learning.main()`.
3. **Where is the untrained advantage?** e4 says not in gain and not in the
   single-note wiring margin. Measure the *timing* of each channel's response
   to a falling note (peak latency relative to the judgment line) and
   behaviour with two notes on screen, real vs rewired. If a quantity there
   predicts play across rewired graphs, make it the wiring rule's criterion.
   The recordings `reservoir.record()` produces are exactly the right data for
   this and cost 10 s per chart.
4. **Chords are where the real network looks worst.** Fitted on stage 3 and
   asked to play stage 4 without refitting, it falls below the rewired mean at
   three of four readout sizes. Fit on stage 4 and see whether that survives;
   if it does, the amplified common mode responding to both lanes at once is
   the explanation to test.
5. **A learning rule that meets the ceiling.** e5 measures what a linear
   readout of size k can do; e3 measures what antithetic perturbation finds in
   30 episodes. The gap between them is large. A rule that closes it while
   staying biologically plausible (eligibility traces, a per-lane reward
   signal) would make the learning comparison as sharp as the untrained one.
4. **The J lane.** Untrained J is never pressed. Either accept it as the
   honest cost of e1's lane placement or run the declared "lanes in the frontal
   zone" experiment as a separate condition.
5. **Encoder adaptation variant** (`Encoder(adapt=100, adapt_gain=1)`) — built,
   showed no gain in the chaotic regime, never tested in the play regime where
   it might matter. Cheap to check.
6. **Live osu! test** of `play_osu.py --sink keyboard` with a silent audio
   file and `results/flyosu_stage4.osu`. Expect to tune `--offset`.
7. Longer term: the dopaminergic/MBON plasticity option from the previous
   handoff is still open and still the most biologically interesting; the
   `learn.py` interface (`ReadoutLearner` with a `mask`) is the place a
   connectome-internal rule would plug in alongside the readout rule.

---

## Measurement hygiene (carried forward, plus two additions)

- Every new claim gets a matched control, same procedure, same regime.
- Report permutation p *and* the floor 1/(n+1). With 3 controls the floor is
  0.25; say so every time.
- **Report `Fly.stability()` for every network** in every experiment from now
  on. The chaotic e1 regime went unnoticed for a whole experiment because
  nothing measured the resting state.
- **Prefer a stable regime + tiny signals over a chaotic regime + large ones.**
  A deterministic network at a fixed point reads a 10⁻⁴ deflection perfectly.
- `restats.py`/`refresh_c.py` pattern: recompute without re-simulating.
  `python -m experiments.e2_play report` re-prints the e2 summary from JSON.

---

## Citations

- FlyWire connectome — Dorkenwald et al., *Nature* 634, 124–138 (2024).
- Annotations — Schlegel et al., *Nature* 634, 139–152 (2024).
- LIF parameters + connectivity mirror — Shiu, Sterne et al., *Nature* 634,
  210–219 (2024).
- osu!mania judgment windows — osu! (stable) mania hit windows, OD-scaled.
