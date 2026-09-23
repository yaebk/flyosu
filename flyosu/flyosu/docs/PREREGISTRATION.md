# Pre-registration — experiment 14

**Written before the controls were generated and before the real network was
measured. Nothing below may be changed once the freeze in §7 is taken; any
deviation goes in §9, with its reason, and stays there.**

Git tag at freeze: `e14-prereg`. The commit that adds this file contains no
results, and the analysis script it names is committed in the same state.

---

## 1. Why this experiment exists

This project has one robust methodological finding and it is entirely
retrospective. Seven times — experiments 5, 6, 7, 8, 10, 11 and the experiment 3
re-run — a gap between the real connectome and its controls shrank, or an
explanation of that gap dissolved, as soon as the comparison was made more
carefully. Four of those seven cost the project a claim it had already written
down.

The mechanism is always the same: a choice **matched as a procedure** — the same
rule applied to every network — can still be **unmatched in outcome**, because it
was developed while looking at the real connectome and happens to suit it.
θ = 1.5 was of this kind. So was the margin wiring rule. Experiment 11 produced
the mirror image, a delay cap that bound on the real network and almost no
control, which shows the effect is not a bias in one direction but in one
*direction of attention*: a choice you never thought of as a parameter gets
tuned by whichever network you were looking at when you made it.

Every one of those seven was caught **after** the fact. That is the weakness.
A pattern of self-caught errors is not evidence that the current numbers are
clean; it is evidence that this class of error is easy to make here and that
nobody has yet run a comparison in which it was impossible.

This experiment is that comparison. Its purpose is not to discover anything new.
It is to produce one number that no later reader has to take on trust.

## 2. Hypothesis

**H1 (primary).** The real FlyWire connectome's four descending channels are
more lane-selective than those of degree-, weight- and sign-matched rewired
controls.

Lane-selectivity is `probes.selectivity(...)["argmax_mean"]`: for each lane, the
fraction of the hit window during which that lane's wired channel is the largest
of the four, averaged over the four lanes. It is label-free, threshold-free,
press-free, and computed from a silent single-note probe. It is the surviving
directional claim with the fewest free parameters attached, which is why it is
the primary endpoint and not one of the several alternatives in §4.

**H0.** The real network's selectivity is a draw from the rewired distribution.

Direction is specified in advance: the test is one-sided, and only a real value
**above** the controls counts as support. A real value below the controls is
recorded as a failure of H1, never reinterpreted as a finding in the other
direction.

## 3. Why this endpoint and not a behavioural one

Every behavioural comparison in the project has now been run under a fair
protocol and none favours the real connectome (`docs/CLAIMS.md`). Pre-registering
another one would be pre-registering a null already obtained.

Selectivity is different in three ways that matter:

- It has **no threshold**, so it cannot inherit experiment 6's error.
- It has **no presses**, so it cannot inherit experiment 7's press-count
  degeneracy, where a ratio over 8 presses was reported as a score of 0.800.
- It has **no chart**, so it does not depend on the note interval that
  experiment 11's explanation turned on.

It currently stands at real 0.79 vs rewired 0.50 ± 0.17, 1/20, p = 0.095
(`docs/RESULTS_E7.md`). At n = 40 the p-floor falls to 0.024, so this design can
either confirm it below 0.05 or refute it. It is the only directional claim in
the project for which that is true at reachable cost.

## 4. What is primary and what is not

**One primary endpoint**: `argmax_mean`, real vs 40 `shuffle_seed` controls.
The project's history is a long argument for not giving oneself a menu.

**Secondary, declared now, reported with an explicit multiplicity warning and
never quoted as though primary:**

- `peak_margin_mean` from the same probe.
- Untrained lane-correctness and untrained accuracy under the experiment 11
  protocol with per-key delays.
- The `retino_seed` family on the primary endpoint, n = 20.

No secondary endpoint may be promoted to primary after the fact for any reason,
including the primary failing.

**Explicitly excluded**: the `channel_seed` family. Shuffling channel labels
changes which descending neurons form each group, and `band_assignment` then
re-derives the lane→channel permutation from the shuffled groups, so this family
is not a clean null for a selectivity measure defined over that permutation. It
is excluded now rather than run and discarded later.

## 5. Protocol, fixed

Every value below is fixed at the freeze. None may be swept, tuned, or chosen
after any real-network number is known.

| parameter | value | where from |
|---|---|---|
| dataset | `flywire` | — |
| regime | `model.build(regime="play")`, floor 30.0 | `docs/CALIBRATION.md` |
| controls | `shuffle_seed` 1..40 | matches experiment 9's n |
| probe | `probes.lane_traces`, `approach_ms=800`, `dt=DT_PLAY=2.0` | e6/e7 default |
| wiring rule | `probes.band_assignment`, `hit_ms=(-160,160)`, `false_scope="window"` | e7's corrected rule |
| endpoint | `probes.selectivity(tr, wiring, hit_ms=(-160,160))["argmax_mean"]` | e7 |
| stimulus noise | none on the probe (silent, deterministic) | e6/e7 |
| p convention | `p = (n_ge + 1) / (n + 1)`, one-sided, floor quoted every time | project-wide |

Wiring is derived **per network from that network's own probe**. No control
inherits the real network's permutation. This is the rule that experiments 6
and 7 were violating.

`fly.stability()` is recorded for every network, real and control, and any
network whose blank field is not a fixed point is reported. Experiment 1 ran
entirely in an unnoticed chaotic regime; the check is now unconditional.

## 6. Analysis, fixed

1. Compute the endpoint for all 40 controls.
2. Compute the control mean, SD, min, max, and the full sorted vector.
3. Compute the endpoint for the real network **once**.
4. `n_ge` = the count of controls whose value ≥ the real network's.
   `p = (n_ge + 1) / 41`. Support for H1 requires **p < 0.05**, i.e. `n_ge = 0`.
5. Report the effect in control SD units, and report the control max, because a
   "0/40" whose largest control sits just under the real value is a weaker
   result than one whose distributions do not approach each other, and the
   difference is invisible in the p-value.

No exclusion of any control for any reason. If a control fails the stability
check it is reported and **kept**; a rule that drops controls is exactly the
kind of choice this document exists to prevent.

No transformation, no outlier rule, no alternative test. The permutation test
above is the whole analysis.

## 7. The freeze — the device that makes this binding

The ordering is the point, and it is what distinguishes this from every earlier
experiment here:

1. This document is committed and tagged.
2. The analysis script is committed **in the same state**, complete, with the
   real network's run guarded behind an explicit flag.
3. **All 40 controls are run and their values committed** as a results file.
4. Only then is the real network run, once.

After step 3 the null distribution is fixed and public. It is not possible to
tune a procedure to favour the real network using a distribution computed before
that network was ever measured — not because anyone promises not to, but because
the numbers that would be needed do not exist yet.

That is the whole methodological content of this experiment, and it is worth
more than its result either way.

## 8. What each outcome licenses

**p < 0.05 with the control max well below the real value.** The real
connectome's channels are more lane-selective than rewired controls', stated
without protocol caveat. This becomes the project's first pre-registered claim
and the only behavioural-adjacent one that survived an adversarial design. It
would sit alongside the two structural claims and would be the first result here
that connects structure to anything the fly does.

**p < 0.05 with the control max close to the real value.** The same claim, with
the closeness reported in the same sentence. Report the distributions, not only
the count.

**p ≥ 0.05.** H1 fails. Claim 4 in `docs/CLAIMS.md` moves from "supported in
direction" to "not supported", and the count in the methodological section goes
from seven to eight. This must be written up as prominently as a positive
result — the project's most-cited property is that it reports retractions in the
same voice as findings, and the first pre-registered result being a null is a
reason to keep doing that, not to soften it.

**The real value falls below the control mean.** Recorded as a failure of H1.
Not reinterpreted, not re-run with a different endpoint, not explained.

## 9. Deviations

None yet. Anything that happens after the freeze goes here, with the date, what
changed, and why — including deviations forced by cost or by bugs. An empty
section at the end is the claim; a populated one is still honest, and a
populated section nobody wrote is the failure mode.

## 10. Known limits of this design

It is worth being clear that a pre-registration fixes one failure mode and not
the others.

- **It does not make the endpoint the right one.** `argmax_mean` was chosen
  because it survived earlier scrutiny, and it survived that scrutiny in
  analyses that looked at the real network. The choice of *what to
  pre-register* is itself downstream of the very process this document
  distrusts. That is a real limit and cannot be fixed from inside the project.
- **One connectome, one task, one control family for the primary.** Nothing here
  generalises to other connectomes or other behaviours.
- **n = 40 gives a p-floor of 0.024.** No outcome can be significant beyond
  that, and the design has no power to distinguish a large effect from an
  enormous one.
- **The model is assumed, not measured.** Neuron dynamics, synaptic strength,
  excitability, how a note becomes light, and how descending neurons map onto
  keys are all modelling choices (`docs/CALIBRATION.md`). A pre-registered
  comparison between a real graph and a rewired one holds all of those fixed and
  is silent about every one of them.
