# Experiment 9 — the two structural claims, measured properly

**Short answer: both survive, both are real, and both were being stated too
broadly. Rewiring the topology collapses the spectral radius (FlyWire
**0/40, p = 0.024**; male CNS 0/10, p = 0.091) and raises the readout
population's dimensionality (same 0/40 and 0/10, on three different measures of
it). At n = 40 these are the only results in the project below p = 0.05, and
unlike the behavioural ones they carry no protocol caveat. They
are two independent properties, not one restated twice (ρ ≈ 0 within every
family). But neither claim holds against the *other* control families — the
retinotopy shuffles have a **higher** radius than the real network (20/20 on
FlyWire), and the channel-label family cannot move either number at all. From
here these must be stated as "against degree- and weight-preserving rewiring",
never "against controls".**

72 networks, both datasets. Raw numbers: `results/e9_structure.json`,
`results/e9.log`.

## Why this was run

Experiments 5–8 progressively dismantled the project's behavioural claims —
every time the controls were given a fairer procedure, the gap shrank. What
survived was two measurements that need no behavioural protocol at all, and
which had therefore never been touched by any of those corrections. They had
also never been measured as claims in their own right: the radius at n = 6 per
family, and the dimensionality only as a by-product of experiment 5. This gives
both a proper treatment.

## 1. Spectral radius

Real FlyWire 2.283, real male CNS 2.055. One-sided permutation,
p = (n_ge + 1)/(n + 1).

| dataset | family | n | mean ± sd | range | n ≥ real | p |
|---|---|---|---|---|---|---|
| FlyWire | rewired topology | **40** | 0.733 ± 0.089 | 0.63–1.12 | **0/40** | **0.024** |
| FlyWire | shuffled retinotopy | 20 | 3.055 ± 0.142 | 2.66–3.27 | 20/20 | 1.000 |
| FlyWire | shuffled channel labels | 10 | 2.283 ± 0.000 | — | degenerate | — |
| male CNS | rewired topology | 10 | 0.650 ± 0.025 | 0.63–0.72 | **0/10** | **0.091** |
| male CNS | shuffled retinotopy | 10 | 2.662 ± 0.483 | 2.05–3.66 | 9/10 | 0.909 |

## 2. Dimensionality of the readout population

Over the same 61-stimulus calibration ensemble everything else is fitted on.
Real FlyWire: PC1 0.384, top-4 0.820, participation ratio 4.37 of 61 modes.
Real male CNS: PC1 0.627, top-4 0.979, PR 2.09.

| dataset | family | n | PC1 | top-4 | PR | p (all three) |
|---|---|---|---|---|---|---|
| FlyWire | rewired | **40** | 0.144 ± 0.024 | 0.409 ± 0.031 | 15.80 ± 1.73 | **0.024** (0/40) |
| FlyWire | retino | 20 | 0.400 ± 0.144 | 0.749 ± 0.086 | 5.06 ± 2.00 | 0.14–0.62 |
| FlyWire | channels | 10 | identical to real | identical | identical | degenerate |
| male CNS | rewired | 10 | 0.196 ± 0.065 | 0.485 ± 0.095 | 12.62 ± 3.96 | **0.091** (0/10) |
| male CNS | retino | 10 | 0.551 ± 0.190 | 0.835 ± 0.095 | 3.38 ± 1.88 | 0.18–0.36 |

**The participation-ratio cross-check passes.** PR is scale- and
gain-invariant, and it separates real from rewired exactly as hard as PC1 does
— same 0/40 and 0/10. So this is not "one mode dominates because the gain is
large", which was the obvious artefact to worry about given that the same
networks also have a high spectral radius.

## 3. Three things that deflate the framing

**(a) The channel-label family is not a control for either quantity, by
construction.** `channel_seed` permutes which descending neurons belong to
which of the four groups. It does not touch the graph, so the Jacobian and its
radius are untouched; and the population projection reads
`readout.dn_local`, which is the same set of neurons regardless of how they are
grouped. All ten controls return the real network's numbers to the last digit.
This family is a real control for *behavioural* claims and a no-op for these
two. Reporting it as "n = 10, no control reaches the real network" would be
meaningless, so it is suppressed.

**(b) The real network does not have the highest radius.** Retinotopy-shuffled
controls exceed it 20/20 on FlyWire and 9/10 on the male CNS. The surviving
claim is directional and narrower than what this project has been saying:
*rewiring the graph collapses the radius; scrambling the eye map raises it.*
"The real connectome sits at an unusual radius" is false as stated. "The real
topology is what puts it above 1" is what the data support.

A caveat that has to travel with that family: only **6 of 20** FlyWire
retinotopy networks reach a blank-field fixed point (drift up to 0.59; male CNS
9/10). `max_real` stays below 1 everywhere, so this is slow settling rather
than linear instability, but those radii are evaluated at a state that has not
finished settling. Experiment 3 saw the same thing at n = 6 and flagged it;
this confirms it at n = 20.

**(c) On FlyWire the dimensionality is a property of the descending-neuron
population, not of the network.** Measuring the participation ratio over the
same calibration states for four different populations:

| FlyWire | readout (1,303) | whole network | hidden | random 1,303 of hidden |
|---|---|---|---|---|
| real | **4.37** | 27.8 | 21.3 | 20.5 |
| rewired ×6 | 13.1–19.0 | 28.5 | 18.6–21.0 | 13.4–17.5 |

The whole network and the hidden population show **no** real-vs-rewired
separation, and a size-matched random population of hidden neurons reverses the
sign — the real network is *more* high-dimensional there. So the effect is
specific to the anatomical readout. That is a sharper claim than "the real
network is low-dimensional", and it rules out a global-gain artefact a second
time, independently of the PR check.

On the male CNS the locus is different: real hidden PR 15.2 vs rewired
22.3–25.7, and random 7.1 vs 9.7–12.8, so there the low dimensionality is
network-wide. **The two datasets agree on the readout and disagree on the
locus**, which is worth flagging as unexplained rather than smoothing over.

## 4. Are they one property or two? — Two

Spearman across control networks, computed **within** family:

| | radius ~ PC1 | radius ~ top-4 | radius ~ PR |
|---|---|---|---|
| FlyWire rewired (**n=40**) | +0.08, p 0.62 | −0.13, p 0.44 | +0.07, p 0.68 |
| FlyWire retino (n=20) | −0.14, p 0.55 | +0.11, p 0.64 | +0.04, p 0.87 |
| male CNS rewired (n=10) | +0.20, p 0.58 | +0.32, p 0.37 | −0.19, p 0.60 |
| male CNS retino (n=10) | +0.08, p 0.83 | +0.30, p 0.41 | −0.12, p 0.75 |

Inside every family the two are uncorrelated. The retinotopy family makes the
point concretely: the graph is untouched, the radius is pinned in a 0.6-wide
band, and PC1 ranges over 0.21–0.82 with no relation to where in that band a
network sits.

**A trap worth recording.** Pooling families produces ρ = +0.74 (FlyWire) and
+0.77 (male CNS), both p < 0.001 — entirely an artefact of two blobs. Rewired
sits at low radius *and* low PC1, retino at high radius *and* high PC1, so
pooling manufactures a slope that no family shows. Do not quote the pooled
number.

## What is solid, and at what n

- **Rewiring the topology collapses the spectral radius.** FlyWire **0/40,
  p = 0.024**; male CNS 0/10, p = 0.091. Effect ~3×, distributions
  non-overlapping (rewired max 1.12 against real 2.28). Replicated on two
  independent connectomes.
- **Rewiring the topology raises the readout population's dimensionality.**
  Same **0/40**, on PC1, top-4 and the gain-invariant participation ratio
  alike, and on FlyWire it is specific to the descending population.
- **These are two properties, not one.** ρ ≈ 0 within every family on both
  datasets. The project has two independent structural claims, not one stated
  twice.
- **Neither holds against the other two families.** From now on: "against
  degree- and weight-preserving rewiring", never "against controls".

## Honest caveats

- **p = 0.024 at n = 40 is still the floor the convention allows**, not a
  measure of effect size. The effect size is the thing to quote: the rewired
  radius maxes out at 1.12 against the real network's 2.28, and rewired PC1
  maxes out well below the real 0.384. More seeds would lower p further
  without telling anyone anything new.
- **The male CNS family is still n = 10** (p = 0.091), so the replication is
  directionally clear but not independently significant.
- **Even at n = 40 the confidence interval on a null correlation is about
  ±0.31**, so section 4 establishes "no strong shared driver", not "exactly
  independent". Separating ρ = 0.3 from 0 would need ~80 seeds per family.
- **The retinotopy radii are measured at a non-stationary state** for 14 of 20
  FlyWire networks. They are reported because the direction is unambiguous, not
  because the value is precise.
- The male CNS retinotopy is a geometric reconstruction (`docs/MALECNS.md`),
  not a measured eye map, so that family carries the same caveat it always has.

## What this licenses

- State both claims with the family named. Drop "vs controls" wherever it
  appears for these two quantities — `docs/RESULTS_E7.md` and the README have
  been corrected.
- Stop calling the radius "unusual". Say that rewiring collapses it.
- Treat the readout-population locus on FlyWire as the most interesting single
  result here, and the dataset disagreement about that locus as open.
