# What this project actually shows

One page, kept current, superseding anything older that contradicts it. Nine
experiments, two connectomes, and five occasions on which a result got weaker
once the controls were treated better. Written for someone deciding what to
believe, not what was believed at the time.

Each claim below carries the control family it holds *against*. That
qualification is load-bearing: the project has three control families and they
are not interchangeable.

## The control families, and what each can test

| family | what it scrambles | what it can test |
|---|---|---|
| `shuffle_seed` — rewired topology | the graph, preserving degree, weight and sign multisets | everything; the direct test of "does the wiring matter" |
| `retino_seed` — shuffled retinotopy | which photoreceptor sees which direction; graph untouched | behaviour and dimensionality; **raises** the spectral radius |
| `channel_seed` — shuffled channel labels | which descending neurons form each of the four groups | behaviour only — **cannot move** the radius or the readout dimensionality, by construction |

"Against controls" is never an adequate statement. Name the family.

## Supported

**1. Rewiring the topology collapses the blank-field spectral radius.**
Real 2.283, rewired 0.733 ± 0.089 over 40 seeds, **0/40, p = 0.024**;
replicated on the male CNS (2.055 vs 0.650 ± 0.025, 0/10, p = 0.091).
Distributions do not approach each other — the largest of 40 rewired draws is
1.12. `docs/RESULTS_E9.md`.

**2. Rewiring the topology raises the readout population's dimensionality.**
Real PC1 0.384, rewired 0.144 ± 0.024, **0/40, p = 0.024**; holds identically
on the top-4 fraction and on the gain-invariant participation ratio, so it is
not an artefact of the large gain. Replicated on the male CNS (0/10). On
FlyWire the effect is specific to the *descending-neuron population* — the
whole network, the hidden population, and a size-matched random population show
no separation, and the random one reverses sign. On the male CNS it is
network-wide instead, and that difference is unexplained.
`docs/RESULTS_E9.md`.

**3. Those two are independent properties.** Within every control family on
both datasets the correlation between them is ≈ 0 (radius ~ PC1: +0.08 at
n = 40). The large correlation that appears if families are pooled (+0.74) is a
two-blob artefact and should never be quoted. `docs/RESULTS_E9.md`.

These three are the only results in the project below p = 0.05, and the only
ones that need no behavioural protocol — which is why no procedural correction
has touched them.

## Supported in direction, not significant

**4. The real network's channels are unusually lane-selective.** Real 0.79 vs
rewired 0.50 ± 0.17, 1/20, **p = 0.095**, re-measured under the corrected
wiring rule. `docs/RESULTS_E7.md`.

**5. Untrained lane-correctness.** Real 0.73 vs rewired 0.47 ± 0.14, 1/20,
**p = 0.095**, under the best protocol available (band wiring, every network at
its own best threshold). Direction has been consistent across every version of
this comparison; significance has not been reached under a fair protocol.
`docs/RESULTS_E6.md`, `docs/RESULTS_E7.md`.

**6. Learning, thresholds-only.** Real 0.211 vs rewired 0.101 ± 0.079, 1/8,
p = 0.22. The condition where the wiring does the most work, and the part of
experiment 3 that best survives re-measurement. `docs/RESULTS_E3.md`.

## Not supported

**7. Untrained accuracy.** Real 0.196 vs rewired 0.186 ± 0.075, **8/20,
p = 0.43**. Once the controls get the corrected wiring rule and their own best
threshold, there is no advantage. `docs/RESULTS_E7.md`.

**8. Any advantage at the supervised ceiling.** With the readout fitted in
closed form, the real network is inside the rewired distribution at every
readout size (best 3/10, p = 0.36) — while playing far better in absolute terms
(0.92 accuracy with 68 parameters). `docs/RESULTS_E5.md`.

**9. Recurrent gain as an explanation for behaviour.** Radius does not predict
untrained play across random graphs (ρ = 0.20, p = 0.39).
`docs/RESULTS_E4.md`.

## Retracted

**10. "The real network is the only one admitting a single working threshold
for all four keys" (experiment 6).** Measured under a wiring rule that was not
optimising that band. With each network wired by the rule that does, 5/20
controls match it. `docs/RESULTS_E7.md`.

**11. "The real connectome's spectral radius is unusual."** Retinotopy-shuffled
networks exceed it 20/20 on FlyWire. The correct statement is directional:
rewiring the topology collapses the radius. `docs/RESULTS_E9.md`.

**12. "p = 0.048" as the untrained headline (experiment 4).** Measured at a
fixed θ = 1.5, which is the real network's best value and almost never a
control's. Under a per-network best threshold it is p = 0.095.
`docs/RESULTS_E6.md`.

**13. The clean monotone learning ordering (experiment 3).** Under the
corrected wiring rule it survives on area under the learning curve
(1/8 → 2/8 → 4/8) and breaks on final accuracy (1/8 → 3/8 → 2/8). Quote it with
the metric attached, or not at all. `docs/RESULTS_E3.md`.

## The methodological result

**Five times, a gap shrank as soon as the controls were given a fairer
procedure** — readout fitting (e5), the shared threshold (e6), the wiring rule
(e7), the sensory front end (e8), the learning comparison's starting wiring
(e3 re-run). Twice the thing that shrank was a claim this project had already
written down.

The mechanism was the same each time and is worth naming: a choice that is
*matched as a procedure* — the same rule applied to every network — can still
be *unmatched in outcome*, because it was developed while looking at the real
connectome and happens to suit it. θ = 1.5 and the margin wiring rule were both
of this kind. Neither looked like a degree of freedom at the time.

The practical consequence for anyone extending this: **design the comparison to
be adversarial to the real connectome from the start.** Give every control its
own best operating point on every free parameter, decide the metric before
looking, and treat any procedure tuned on the real network as suspect until it
has been swept per network.

## Absolute performance, separately from any comparison

The best readout reaches **0.92 accuracy** on held-out stage-3 charts with 68
parameters, fitted in closed form, connectome frozen (`docs/RESULTS_E5.md`).
Across the curriculum it presses the right key essentially always
(lane-correct ≥ 0.95) and hardly ever presses an empty lane. What limits it is
timing, and experiment 8 established that ceiling is structural: the spread of
the four channels' peak times is the network's own latency structure, and no
sensory front end removes it. The next lever is per-key delays in the
controller. `docs/RESULTS_E8.md`.
