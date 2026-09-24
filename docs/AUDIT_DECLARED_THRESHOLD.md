# Audit: experiments 7, 11, 12, 13 and 15 under a declared threshold

## Declared before computing

Written and saved before any audited number was computed.

**Why.** Experiments 7, 11, 12, 13 and 15 read every network at its own best
threshold, chosen by sweeping theta on the charts being scored. Accuracy cannot
see stray presses, so that sweep selects for mashing (experiment 16), and under
a declared threshold experiment 17 found no untrained accuracy deficit. This
audit asks what each experiment's real-vs-rewired comparison says when every
network is read at the same declared threshold instead.

**Threshold.** theta = **1.5**, `Player.untrained`'s default, never fitted. No
other threshold is reported as the audited figure. The swept figures are
quoted only as what each experiment originally claimed.

**Data.** Stored results only; nothing is rerun. Every experiment's stored sweep
grid contains 1.5, so each network's value at 1.5 is read from its stored grid.
Where a quantity was stored only at the swept threshold (experiment 13's
held-out charts), it is reported as not auditable, with the run that would be
needed.

**Endpoints**, per experiment, the metric it originally quoted, read at 1.5 on
the same charts it was quoted on:

| exp | file(s) | controls | endpoint(s) at theta = 1.5 |
|---|---|---|---|
| 7 | `e7_wiring.json` (FlyWire), `e7_wiring_malecns.json` | 20 / 10 rewired | accuracy; lane-correct (band-rule wiring) |
| 11 | `e11_delays_cap1000.json` (600 ms, the reported run) | 20 rewired | accuracy with delays; lane-correct |
| 12 | `e11_delays_cap1000_interval{450,1000,1400}.json` (+ 600 ms from exp 11) | 20 rewired | accuracy with delays at each interval |
| 13 | `e13_readout_malecns.json`, four readout arms | 10 rewired | accuracy; strays per note; score = acc - 0.4 x strays (tuning charts) |
| 15 | `e15_trigger_interval1400.json`, three trigger arms | 20 rewired | accuracy; lane-correct |

Strays per note are recorded only in experiment 13; the others did not store
them, so no stray endpoint is reported for them.

**Statistic.** The project convention: one-sided rank p = (n_ge + 1) / (n + 1),
where n_ge counts controls scoring >= the real network (ties count against the
real network). For strays, where lower is better, n_ge counts controls scoring
<= the real network. Reported with the control mean +- sd (sample sd, ddof = 1).
No multiple-comparison correction is applied or claimed; this is an audit of
direction and size, and each experiment's own floor (1/21 = 0.048 for 20
controls, 1/11 = 0.091 for 10) is stated alongside.

**Press guard.** Each experiment's own guard: 20 counted presses (presses landing
near a note). Any network below 20 at theta = 1.5 is named. Its lane-correct is
a ratio over too few presses and is not a measurement; lane-correct is
therefore compared only over networks meeting the guard, and if the real network
fails it the lane-correct comparison is reported as not auditable. Accuracy is
reported over all networks, with the count of those below the guard alongside.

**Verdicts**, relative to each experiment's original swept-threshold claim:
*holds* (same direction, n_ge/n within about one network of the original),
*weakens* (same direction, clearly fewer controls on the winning side),
*reverses* (the other side now leads by the rank), or *cannot audit from stored
data*.

**Disclosure.** While inspecting file structure to write this plan, three stored
values at theta = 1.5 were seen incidentally before this section was saved: the
real network's experiment 7 band-rule entries on FlyWire and on the male CNS,
and its no-delay entries in the 1400 ms interval file. No control values and no
comparison were computed before saving.

## Findings

Computed by `experiments/audit_declared.py` from the stored JSONs. Recomputing
the swept figures from the same files reproduces each experiment's published
numbers. (Control sd here uses ddof = 1, so some are about 0.004 wider than the
published ones.) "Guard" = counted presses at theta = 1.5, real network /
controls below 20.

| exp | original claim (swept theta) | at theta = 1.5: real | controls | n_ge/n | p | guard | verdict |
|---|---|---|---|---|---|---|---|
| 7 FlyWire, accuracy | level: 0.196 vs 0.186, 8/20, p = 0.43 | 0.146 | 0.103 ± 0.066 | 4/20 | 0.238 | 22 / 4 of 20 | **holds**: still level, now leaning toward real (8/20 → 4/20) |
| 7 FlyWire, lane-correct | real ahead: 0.727 vs 0.469, 1/20, p = 0.095 | 0.727 | 0.332 ± 0.181 | 1/16 | 0.118 | as above | **holds** |
| 7 male CNS, accuracy | real behind: 0.067 vs 0.237, 9/10 | 0.000 | 0.122 ± 0.090 | 10/10 | 1.000 | **0** / 1 of 10 | **cannot audit**: real never presses at 1.5 |
| 11 accuracy (600 ms) | real behind: 0.242 vs 0.539, 19/20, p = 0.95 | 0.121 | 0.350 ± 0.176 | 17/20 | 0.857 | 22 / 1 of 20 | **holds**, slightly smaller (gap 0.297 → 0.229) |
| 11 lane-correct | level: 0.655 vs 0.652, 11/20 | 0.591 | 0.587 ± 0.194 | 11/19 | 0.600 | as above | **holds** |
| 12 accuracy, 450 ms | behind, 20/20 (gap 0.226) | 0.067 | 0.278 ± 0.140 | 18/20 | 0.905 | **13** / 2 of 20 | **holds** in direction; real below guard |
| 12 accuracy, 1000 ms | behind, 18/20 (gap 0.269) | 0.271 | 0.344 ± 0.215 | 12/20 | 0.619 | 31 / 7 of 20 | **weakens** (gap 0.073) |
| 12 accuracy, 1400 ms | behind, 19/20 (gap 0.282) | 0.271 | 0.342 ± 0.211 | 12/20 | 0.619 | 31 / 7 of 20 | **weakens** (gap 0.071) |
| 13 pc8 (primary), accuracy | real ahead on tuning charts: 0.258 vs 0.131, 1/10 | 0.104 | 0.098 ± 0.087 | 5/10 | 0.545 | 35 / 6 of 10 | **weakens** to level |
| 13 pc8, strays/note (lower better) | 0.325 vs 0.540, 2/10 | 1.225 | 0.220 ± 0.194 | 10/10 | 1.000 | as above | **reverses** |
| 13 pc8, score | real ahead: 0.128 vs −0.085, 1/10 | −0.386 | 0.010 ± 0.119 | 10/10 | 1.000 | as above | **reverses** |
| 13 channels (leg pools), accuracy | real behind: 0.042 vs 0.173, 9/10 | 0.000 | 0.122 ± 0.090 | 10/10 | 1.000 | **0** / 1 of 10 | **cannot audit**: real never presses |
| 13 channels_signed, accuracy | 0.067 vs 0.116, 5/10 | 0.000 | 0.113 ± 0.104 | 10/10 | 1.000 | **12** / 1 of 10 | **cannot audit**: real below guard |
| 13 pc4, accuracy | 0.100 vs 0.125, 5/10 | 0.025 | 0.020 ± 0.044 | 2/10 | 0.273 | **9** / 9 of 10 | **cannot audit**: nearly all below guard |
| 13, all arms, held-out charts | pc8 6/10, p = 0.636 | — | — | — | — | — | **cannot audit from stored data** |
| 15 cross, accuracy (1400 ms) | level: 0.175 vs 0.187, 11/20 | 0.037 | 0.050 ± 0.083 | 8/20 | 0.429 | **9** / 16 of 20 | **cannot audit**: mostly fallbacks |
| 15 peak, accuracy | real behind: 0.000 vs 0.190, 20/20 | 0.000 | 0.123 ± 0.134 | 20/20 | 1.000 | **0** / 12 of 20 | **cannot audit**: real never presses |
| 15 fall, accuracy | level: 0.158 vs 0.196, 11/20 | 0.000 | 0.085 ± 0.105 | 20/20 | 1.000 | **11** / 13 of 20 | **cannot audit**: mostly fallbacks |

Wherever the real network fails the guard at 1.5, the guarded lane-correct
comparison is not auditable either. That covers the male CNS in experiment 7,
the 450 ms arm of experiment 12, three of the four experiment 13 arms, and all
of experiment 15. At 1000 and 1400 ms the real network's lane-correct stays
behind (10/13 controls above it in both). In experiment 13's channels arm the
real network makes zero strays and scores 0 at theta = 1.5 simply because it
never presses. That is the degenerate optimum experiment 13's guard was written
to exclude, so the arm's 0/10 strays and 2/10 score are not results.

### What the audit says

- **The accuracy deficit with per-key delays (experiments 11 and 12) survives a
  declared threshold at short note intervals and mostly disappears at long
  ones.** At 450 and 600 ms the real network is still behind 18/20 and 17/20.
  At 1000 and 1400 ms it drops to 12/20, with the gap cut from about 0.27 to
  about 0.07. Experiment 12's claim that the gap "never closes" across
  intervals is therefore a swept-threshold result. The caveat is that 7 of the
  20 controls make fewer than 20 counted presses at 1.5 in those arms.
- **Experiment 7 on FlyWire holds and leans slightly toward the real network**
  (accuracy 4/20; lane-correct 1/16).
- **Experiment 13's primary-arm advantage on the tuning charts does not survive
  the audit.** On pc8 the real network is level on accuracy and much worse on
  strays (1.225 per note against 0.220, 10/10). That agrees with the held-out
  result in experiment 13, but it has the opposite sign on strays from
  experiment 17's finding on FlyWire. One caution: on the PC arms theta sits on
  a projection whose scale differs from the channel readout, so 1.5 is the same
  number there without being the same operating point.
- **At theta = 1.5 most of experiment 15, and the male CNS channel readouts,
  measure mostly silence.** Most networks barely press, and the real network
  fails the guard in all three experiment 15 arms. Nothing from these arms
  should be quoted as a declared-threshold comparison.

### Missing data and the runs that would fill it

- **Experiment 13, held-out charts at theta = 1.5.** The file stores held-out
  play only at each network's swept theta. Filling this means replaying 11
  networks × 4 arms on the 3 held-out charts (stage 3, 20 notes, 600 ms, seed
  999) at theta = 1.5: 132 network-chart plays, with 11 network builds.
- **Strays per note for experiments 7, 11, 12 and 15.** These were never
  stored, so the stray endpoint can only be audited for experiment 13. Filling
  it means rerunning each experiment's scored charts (2 charts × 20 notes) at
  theta = 1.5 alone: 21 + 11 networks for experiment 7, 21 for experiment 11,
  21 × 3 intervals for experiment 12, and 21 × 3 triggers for experiment 15.
  That is 179 network-condition runs, or 358 chart plays.
- **Any arm flagged "cannot audit" above.** Theta = 1.5 does not give enough
  presses there for a measurement. A like-for-like registered test with more
  notes per chart would be needed; choosing a different threshold is not
  allowed under this declaration.

### Caveats

- The audited values come from the same charts the original sweep was tuned
  on. Only the threshold selection has been removed.
- The p-values are uncorrected and descriptive. The floors are 0.048 for 20
  controls and 0.091 for 10. None of the audited comparisons that favour the
  real network come near either floor.
- Three of the real network's 1.5 entries were seen before the plan was saved
  (see the disclosure above). None of them changes an endpoint's definition.
