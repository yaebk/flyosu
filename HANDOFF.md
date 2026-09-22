# Handoff — Fruit Fly Connectome Plays osu!mania

Written at the end of the session that built steps 5–12 and ran experiment 2
once. Supersedes the previous handoff (which covered steps 1–4); everything from
that document that is still true is repeated here so this file stands alone.

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
  play_osu.py     .osu -> simulate -> replay     Makefile      data/cache/check/check-play/experiment/experiment2
  flyosu/         package (see README "Layout")
  experiments/    e1_*.py, e2_play.py, figures.py, figures_e2.py
  tests/          test_pipeline.py (28), test_play.py (46)
  docs/           CALIBRATION.md, RESULTS.md (e1), RESULTS_E2.md (e2)
  results/        e1_*.json, e2_play.json, e2.log, fig1–9, stats.txt, flyosu_stage4.osu
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
10    training experiments   run once   experiments/e2_play.py, N_CTRL=3, N_LEARN=2, N_EPISODES=30
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
   `θ += lr·½(R⁺−R⁻)·ε/σ`, σ = 0.2, lr = 1, no annealing. σ was lowered from
   0.3 after one smoke test on the real network — a small tuning-on-real bias,
   named in RESULTS_E2. Reward = accuracy − 0.05·strays/note.
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

- **Learner seeds in `results/e2_play.json` are unrecorded** — the running
  script used `hash(label)` (salted per process). Fixed to `zlib.crc32` and the
  seed is now saved; the existing file's learning streams are not bit-reproducible.
- **No learning-rate annealing.** The real fly's blank-start 0.44 → 0.32 dip is
  the visible cost. Fix before scaling the learning experiment.
- **Retinotopy-shuffled #2 is marginal** (drift 2 × 10⁻⁴ at 3 s, radius 3.08).
  Floor 30 has less margin for that family; a stability check per network is
  already in the results.
- **`figures_e2.py` was once truncated to 0 bytes** by a failed write on
  Windows (cp1252 default encoding + a `θ` in the source). Rewritten; the
  lesson is `PYTHONUTF8=1` or `encoding="utf-8"` for any script that rewrites
  files containing non-ASCII.
- Runtime: 2 ms wall per 2 ms game frame (19k neurons, 730k edges, sparse
  matvec). A 20-note chart ≈ 13 s; an untrained sweep (2 θ × 5 stages × 2
  charts) ≈ 4 min; 30 learning episodes ≈ 7 min + evals. E2 as run: 108 min.
- `Player.untrained()` costs ~25 s (settle + 61-stimulus normaliser + 4 falling
  notes). Cache it if you build many.

---

## What to do next, in order of value

1. **More controls for the learning experiment.** `RESUME=1 N_CTRL=3 N_LEARN=5
   N_EPISODES=30 python -m experiments.e2_play` continues the saved run; each
   trained control ≈ 25 min. Add annealing first (`lr *= 0.97` per episode is
   enough) and a `mask_for("thresholds")` condition to separate learning the
   timing from learning the mapping.
2. **Noise.** Re-run untrained play with `noise=0.03` and see whether the
   real-vs-control lane-correct gap survives sensory noise. It is one flag.
3. **The J lane.** Untrained J is never pressed. Either accept it as the
   honest cost of e1's lane placement or run the declared "lanes in the frontal
   zone" experiment as a separate condition.
4. **Encoder adaptation variant** (`Encoder(adapt=100, adapt_gain=1)`) — built,
   showed no gain in the chaotic regime, never tested in the play regime where
   it might matter. Cheap to check.
5. **Spectral radius as a metric.** Compute it for the shuffled-retinotopy and
   channel families across many seeds and for the whole-brain build; it is the
   cheapest connectome-specific number in the project.
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
