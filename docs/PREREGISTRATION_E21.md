# Pre-registration — experiment 21: does the trained fly's play depend on the wiring?

**Comparison thread.** Frozen when this document and
`experiments/e21_trained_wiring.py` are committed together, before any control
is run.

## 1. Why

Every registered comparison so far used an *untrained* fly: a fixed threshold
policy on four channels. The fly that actually plays — round 23's readout,
0.8+ on real maps — has never been compared against rewired wiring. The
capability write-ups warn that its recipe "would very likely work on a rewired
control too". This experiment finds out.

## 2. Hypothesis

**H1:** with round 23's recipe applied to each network separately, the real
FlyWire connectome's mean accuracy over the 30 held-out 4K difficulties exceeds
that of every one of 20 degree-, weight- and sign-preserving rewired controls.

One-sided. The null is that the real network is exchangeable with the controls.

## 3. Protocol, fixed

| parameter | value |
|---|---|
| dataset / regime | `flywire`, `model.build(regime="play")` |
| controls | `shuffle_seed` 1..20 |
| player | `Player.untrained(theta=1.5, noise=0.03)`, refractory 100 ms, smoothing 20 ms, approach 250 ms |
| features | each network's own 48-component `PopulationProjection` of its own 61 calibration states |
| training charts | round 15's 36 synthetic charts (seed 100) + 6 evenly spaced even-segment clips from each of the 17 tuning difficulties (102 clips), holds recorded with `HoldOracle` |
| fit | `RidgeReadout`, per-lane lead and offset, per-lane release level from 0..1 in 0.05, tail lead 130 ms, `project_on_record=True` |
| scored maps | the 30 held-out 4K difficulties (6 songs), each played once in full, seed 4242 |
| primary endpoint | mean of the 30 per-difficulty accuracies (osu!mania OD-scaled windows) |
| p | `(n_ge + 1) / 21`, `n_ge` = controls with accuracy >= the real network's |

Every value comes from `RECIPE` in the script. Nothing is swept per network
except what the recipe itself fits, and the recipe fits on the training
charts only, never on the scored maps.

Declared edge case: a network whose calibration ensemble has rank below 48 is
fitted at its rank, flagged, and kept. `fly.stability()` is recorded for every
network, and any network that is not at a fixed point is reported and kept. A
network that fails to complete for a deterministic reason counts against H1.

## 4. Analysis, fixed

1. All 20 controls are measured, merged, and committed as
   `results/e21_trained_wiring.json`.
2. Only then is the real network measured, once (`run_real` refuses before that
   and refuses to overwrite).
3. Report the real value, the control mean, SD, minimum, maximum, the full sorted
   vector, `n_ge/20`, `p`, and the effect in control SD units.
4. **H1 is supported only if `n_ge = 0` (p = 0.048).** Anything else is not
   support.

Secondary, descriptive only, with no test: strays per note, accuracy by kind of
note (tap, chord, hold, after-hold, fast jack) and by density band. One
interpretation rule is fixed in advance: if the real network wins on accuracy
but makes more strays per note than every control, the win is reported as
bought with extra presses.

No exclusions, outlier rules or alternative tests.

## 5. Known biases, declared

- **The recipe was developed entirely on the real network.** Rounds 1–23 chose
  every setting by how the real connectome played. The controls get a recipe
  tuned for someone else. This favours H1: a win is weaker evidence than it
  looks, and a level result or a loss is stronger.
- **The real network's held-out accuracy under this recipe is already known.**
  Round 23's capability milestone scored it at 0.876
  (`results/e20_realfit_mix_holdout.json`) before this document was frozen. The freeze still protects the control
  distribution: the controls are measured with a procedure fixed before any of
  them existed. The registered real value is the one this script measures, which
  records with `project_on_record`. That path moved no press in a side-by-side
  check, but it is not bit-identical to the milestone run.
- 20 controls make the p floor 0.048, so a single control tying or beating the
  real network ends support.

## 6. What each outcome licenses

- **n_ge = 0:** the trained fly's held-out play depends on the wiring, against
  this control family, under a recipe that was tuned on the real network.
- **n_ge ≥ 1, real above the control mean:** the direction without support.
  Report the effect size; do not describe it as a finding.
- **Real at or below the control mean:** the capability recipe works on wiring
  that preserves degree, weight and sign, with no advantage from the real
  connectome's arrangement. This is what the capability write-ups predicted.

## 7. Deviations

Any change after the freeze is recorded here with its date and reason before
the real network is run.
