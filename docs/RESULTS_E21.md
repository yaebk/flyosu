# Experiment 21 — does the trained fly's play depend on the wiring?

**Comparison thread, pre-registered** ([`PREREGISTRATION_E21.md`](PREREGISTRATION_E21.md),
tag `e21-prereg`).

**Short answer: no, and the wiring does not help.** Given the same recipe, 19
of 20 rewired networks play the held-out maps better than the real connectome.
The real network is at 0.876 against 0.911 ± 0.016 for the controls,
p = 0.952. H1 is not supported, and the real network is 2.2 control SDs *below*
the control mean. This happened with a recipe developed entirely on the real
network, which favoured it.

## What was run

Round 23's recipe, applied to each network on its own: the real FlyWire
connectome and 20 degree-, weight- and sign-preserving rewired controls
(`shuffle_seed` 1–20). Each network got its own calibration ensemble,
48-component projection, ridge readout, timing offsets and release levels.
All were fitted on the same 36 synthetic charts and 102 tuning-map clips. Each
network then played the 30 held-out 4K difficulties once (46,649 notes). The
controls were committed (`a69a373`) before the real network was measured, once.
Script: `experiments/e21_trained_wiring.py`; results:
`results/e21_trained_wiring.json`.

## Result

| | mean held-out accuracy | strays per note |
|---|---|---|
| real connectome | **0.876** | 0.0024 |
| rewired, 20 | 0.911 ± 0.016 (min 0.868, max 0.934) | 0.0049 ± 0.0016 |

n_ge = 19/20, **p = 0.952** (support required 0/20, p = 0.048). Effect −2.19
control SD. Sorted controls: 0.868 0.883 0.899 0.900 0.901 0.904 0.906 0.908
0.909 0.911 0.912 0.915 0.918 0.921 0.922 0.925 0.925 0.925 0.929 0.934. All
21 networks were fitted at k = 48 and all were at a fixed point. None was
excluded.

The registered value equals the capability milestone's 0.876, despite the
different recording path. The real network is below the control median on 27
of the 30 maps.

### Secondary, descriptive only

| | controls (20) | real | controls ≥ real |
|---|---|---|---|
| tap | 0.961 ± 0.015 | 0.940 | 18 |
| chord | 0.957 ± 0.023 | 0.938 | 18 |
| hold | 0.737 ± 0.028 | 0.619 | **20** |
| note after a hold | 0.754 ± 0.101 | 0.704 | 12 |
| fast jack | 0.378 ± 0.087 | 0.153 | **20** |
| ≤ 5.5 events/s | 0.945 ± 0.010 | 0.933 | 19 |
| 5.5 – 8.5 | 0.928 ± 0.016 | 0.891 | 19 |
| > 8.5 | 0.786 ± 0.038 | 0.707 | 19 |

The gap is largest on the two kinds of note that need a lane's activity to die
away fast: fast jacks, where every control beats the real network (0.378
against 0.153), and holds (all twenty). The real network makes fewer stray
presses than all twenty controls. The registered stray rule does not apply,
because it only covers a real-network win on accuracy.

## What it means

The capability recipe works on any wiring that keeps the connectome's
degrees, weights and signs, and **the real connectome's particular
arrangement is a disadvantage for it, not an advantage**. That is the outcome
the pre-registration marked as licensing "no advantage from the real
connectome's arrangement". The declared biases make it stronger rather than
weaker. The recipe was tuned for 23 rounds on the real network alone, and
the rewired networks still beat it without any tuning of their own.

A likely mechanism, not tested here: the real connectome's recurrent gain.
Its spectral radius is 2.283 against the controls' 0.736 ± 0.117 (recorded by
this run, and the project's surviving structural finding). Higher recurrent
gain makes activity linger, so two notes in one lane 100–150 ms apart blur into
one pulse, and the end of a hold is signalled late. That matches the two note
kinds where the gap is widest. Testing it would need its own registration, for
example scaling each network's recurrent gain to a common radius.

For the capability thread this also means a rewired fly is the better player:
the best control scores 0.934 on the held-out maps against the real
connectome's 0.876. The capability documents report the real connectome only,
by design.

## Deviations

Three, all logged in the registration before the real network produced a
value: a name clash that crashed every shard at its first network (fixed and
smoke-tested on an unregistered network), shards relaunched in different
groupings for memory, and two aborted real-network launches, one an import
error and one a machine restart, neither of which produced a value.
