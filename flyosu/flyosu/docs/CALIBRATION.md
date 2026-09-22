# Making a wiring diagram run

The FlyWire connectome is an anatomical measurement: which neuron contacts which,
how many synapses, and a predicted neurotransmitter for each cell. It is not a
set of differential equations. Everything below is a decision this project had to
make that the data does not contain, recorded here so the result can be read with
the right amount of scepticism.

## What the data gives, exactly

| Given by the connectome | Chosen by this model |
|---|---|
| 139,262 neurons, 15,091,983 directed edges, 54.5M synapses | neuron dynamics |
| synapse count on every edge | absolute synaptic strength |
| excitatory / inhibitory per edge (NT prediction) | each cell's excitability and gain |
| cell type, super-class, hemisphere, soma position | which cells count as "visual input" |
| — | how a note on a screen becomes light on the eye |
| — | how descending neurons group into four keys |

Edge signs use the FlyWire neurotransmitter predictions: acetylcholine excitatory,
GABA and glutamate inhibitory. 60.0% of edges are excitatory.

## What failed first

Three dynamical models were tried before the one in `sim.py`. The failures are
informative, so they are kept in the code (`Network`, the LIF engine) and here.

**1. Published LIF parameters, raw weights.** Shiu, Sterne et al. (2024) fitted a
whole-brain Drosophila LIF model to this same dataset: rest/reset −52 mV,
threshold −45 mV, τ_m 20 ms, refractory 2.2 ms, 0.275 mV per synapse. Reproducing
that here gave a network with no usable operating point. Driving a *single*
photoreceptor at 150 Hz produced nothing at all; driving *twenty* produced 36 Hz
mean firing across 44,000 neurons — the refractory ceiling, brain-wide. The
transition between the two is essentially a step.

The arithmetic says why. The mean neuron receives 391 synapses of input. At
0.275 mV each that is 108 mV of drive against a 7 mV distance to threshold. Any
coherent volley fires everything downstream of it.

**2. LIF plus spike-frequency adaptation.** Adding an adaptive threshold
(τ 150 ms, +1.2 mV per spike) removed the runaway and produced plausible mean
rates (7 Hz at gain 0.5). But the activity it produced was not *specific*:
stimuli at azimuth −60° and +60° gave descending-neuron patterns correlated at
0.94. The network had one global ignition mode and the stimulus only decided
whether it fired. Worse, it was bistable — −20° and +20° produced silence while
−60° and +60° produced full ignition.

**3. Rate model, rectifying-saturating unit, normalised weights.** Normalising
each neuron's input weights to sum to 1 fixed the specificity: stimuli at −60°
and +60° now gave descending patterns correlated at 0.02, with nearby stimuli
still similar (−60° vs −20°: 0.78). That is exactly the structure a retinotopic
map should produce.

It had no amplitude. With normalised weights a neuron's drive is the weighted
*mean* of its presynaptic rates, so a stimulus that activates 3% of
photoreceptors loses about an order of magnitude per synaptic layer. By the
descending neurons, seven layers down, the signal was ~10⁻⁶. The pattern was
right and unusable.

## What the model does instead

Every neuron gets two scalars, set by measurement rather than by hand:

```
x_i       = Σ_j w_ij r_j                       normalised connectome weights
z_i       = slope · (x_i − μ_i) / σ_i + offset
τ dr_i/dt = −r_i + logistic(z_i)
```

`μ_i` and `σ_i` are the mean and spread of the synaptic input neuron *i* receives
across a representative ensemble of stimuli (a 15 × 4 grid of point sources over
the visual field, plus a blank field), measured by `RateNetwork.calibrate` and
iterated with damping because changing the operating point changes the rates
being measured.

In plain terms: each cell's excitability is set so that it is neither silent nor
saturated given the input it actually receives, and the part of its input that
*varies with the stimulus* is the part that drives it. This is what intrinsic
homeostatic plasticity does in real neurons, and it is the minimum needed to make
the wiring diagram run.

Photoreceptors are clamped to the stimulus rather than integrated — they are the
input layer.

### What this preserves and what it costs

Preserved exactly: the graph, the relative weight of every input to every neuron,
and every excitatory/inhibitory sign. Two neurons with different input patterns
still respond differently, and that difference is entirely the connectome's
doing.

Given up: spike timing, absolute firing rates, and any claim that a neuron's
measured excitability matches the real cell's. The calibration ensemble also
biases the model toward the stimuli it was calibrated on — a fly calibrated on
point sources is not calibrated for wide-field motion.

**The honest framing: this is a connectome-*derived* network, not a simulated
fly.** The topology is measured; the dynamics are assumed.

### Why the calibration is not smuggled-in training

The calibration is stimulus-ensemble-wide and label-free. It never sees which
lane a stimulus came from, never sees a motor output, and is applied identically
to the real network and to every control. Two neurons that end up responding
differently to lane D vs lane K do so because the connectome wires them
differently — the calibration gave them the same treatment.

The controls are the actual check on this. `model.build(shuffle_seed=…)`,
`retino_seed=…` and `channel_seed=…` each destroy one thing while keeping the
neuron count, degree sequence, weight and sign multiset, calibration procedure
and channel-definition procedure the same. If the calibration were doing the
work, the controls would score the same.

Two places where the matching is close rather than exact, both checked by
`tests/test_pipeline.py`: rewiring merges about 1.3% of edges that land on a
pair that already exists, and channel sizes are re-derived from each network's
own connectivity so they land within about 10% of the real network's. Forcing
either to match exactly would mean copying part of the real network's structure
into the control.

## Other choices worth knowing about

**The retina is R1-6 only.** Their annotation points lie in the lamina and form a
clean retinotopic sheet (a shallow cap, 300 × 170 × 40 µm, nearest-neighbour
angular spacing 1.5° against 48° for random pairs). R7/R8 terminate at several
medulla depths, so projecting them radially onto the same shell gives angles that
span the whole sphere — meaningless. R1-6 is also the achromatic motion channel,
which is the relevant one here. R7/R8 remain in the network and receive no light.

**The visual field map is calibrated, not measured.** The lamina shell's centre
of curvature is not the eye's optical centre, so the raw radial map is correctly
*ordered* but spans only ~80° of azimuth instead of ~150°. An affine per-eye
rescaling fixes scale and offset; it is monotone, so neighbouring ommatidia stay
neighbours. It does not reproduce the frontal acute zone's magnification.

**The playfield is a cylindrical arena.** Lanes sit at azimuth −60°, −20°, +20°,
+60° rather than in a narrow frontal window. A fly's eyes are lateral and its
frontal binocular field is thinly sampled: with lanes at ±30° the four stimuli
were nearly indistinguishable. Wrapping the playfield around the fly is also the
standard geometry for real Drosophila visual experiments, where LED arenas span
about 270°.

**The subgraph is 19,367 of 139,262 neurons.** Ranked by the product of forward
influence from the retina and backward influence onto descending neurons
(`subgraph.py`). It keeps all 8,452 photoreceptors, all 1,303 descending neurons,
1,260 visual projection neurons and 1,566 central-brain neurons. Whole-brain runs
are supported and give the same qualitative result more slowly.

**The four channels are defined without looking at the stimulus.** Hemisphere
from the FlyWire `side` annotation, then k-means (k=2) on the descending neurons'
input weight vectors within each hemisphere. Clustering them by their *responses*
to the four lanes would have guaranteed the result.

**T1L/T2L/T1R/T2R are nicknames.** FlyWire covers the brain only. These four
groups are descending neurons grouped by hemisphere and input connectivity, not
cells whose ventral-nerve-cord leg targets are known — that would need MANC,
which is a separate dataset.

## Ongoing activity, and the play regime

*Added when the game was built (steps 5–8). This section changes how the
experiment-1 numbers should be read.*

Experiment 1 measured every response the same way: reset the network to zero,
present a stimulus, read out at 300 ms. That protocol never asks whether the
network has a resting state. The game does — notes fall continuously and the
network runs for minutes without a reset — and the answer is no.

**The calibrated network is chaotic.** With a blank visual field it never
settles. Channel activity fluctuates with sd ≈ 0.01–0.02 and an autocorrelation
time of ~70–130 ms, individual neurons flip between 0 and 1, and this persists
at dt = 0.1 ms, so it is a property of the continuous-time model, not of the
integrator. The blank-field Jacobian has spectral radius 15 and per-neuron gains
up to 400. Meanwhile a note at the judgment line moves the pooled channels by
0.001–0.02 — the same size as the fluctuation or smaller. In continuous play
the untrained policy fell from 0.57 (experiment 1) to 0.35–0.45, and no amount
of temporal smoothing, common-mode rejection, or projecting out the dominant
blank-field modes recovered it: the ongoing activity is high-dimensional (30
principal components for 92% of it).

The cause is the calibration itself. `z_i = slope · (x_i − μ_i)/σ_i` makes
every neuron's output vary O(1) across the stimulus ensemble. With normalised
weights the median neuron's input varies by only 0.02, so the median gain is
~30 and neurons whose input barely varies get gains in the hundreds. In a
recurrent network that is a loop gain far above one. And it is
**self-consistent**: lowering `slope` shrinks the fluctuations, which shrinks
the measured σ_i, which restores the gain — the effective operating point is
invariant to `slope` (checked at 1.0, 1.5, 2.0, 2.5). The calibration
homeostatically parks the network deep in the chaotic regime whatever gain is
asked for. Attempt 3 above (gain ≈ 1, signal decaying 10× per layer) was the
other side of the same trade-off.

**What experiment 1 actually measured.** Reproducible transients: the same
deterministic start, the same 300 ms, so the same point on the chaotic
trajectory for every trial. That is a legitimate measurement of how the
stimulus shapes the trajectory, and the real-vs-control comparisons stand —
the controls got the identical protocol. But the phrase "settled response" in
experiment 1 should be read as "response at t = 300 ms from rest".

### The play regime

The one knob that breaks the self-consistency loop is the floor on σ_i. The
`"play"` regime (`model.build(regime="play")`) sets `sigma_floor = 30`: every
neuron's calibrated input spread is at least 30× the median. In practice that
is every neuron, so the per-neuron sensitivity normalisation collapses to
**per-neuron bias homeostasis (μ_i) plus one global gain** — fewer assumptions
than the experiment-1 regime, not more. Floors of 0.3, 1, 3, 10, 15 and 20 were
tried; the network becomes a fixed point between 20 and 25 at slope 2.5, and 30
leaves margin for the controls.

| | experiment-1 regime | play regime |
|---|---|---|
| blank field | chaotic (drift 0.99/100 ms) | fixed point (drift 0) |
| spectral radius at blank | 15.5 | **2.28** (max Re 0.16) |
| max per-neuron gain | 421 | 3.5 |
| note at the line, channel delta | 10⁻³–10⁻² | 10⁻⁴–10⁻³ |
| static probe B, untrained argmax | 0.567 | **0.567** |
| static probe B, 4-channel decoder | 0.721 | **0.917** |
| continuous play, untrained argmax | 0.35–0.45 | 0.60–0.80 |

The stimulus response is ten times smaller in absolute terms and perfectly
readable, because there is nothing to hide it behind: a deterministic network
at a fixed point reproduces a 10⁻⁴ deflection to float precision. Static lane
separation is as good or better than in experiment 1.

**A new fact about the wiring falls out.** Rewired controls in the play regime
have spectral radius 0.7. The real connectome has 2.3. Same neurons, same
degree sequence, same weights, same gain cap — the real optic lobe contains
structured recurrent loops that a degree-preserving rewiring destroys. The real
network sits near the edge of stability; random wiring sits deep inside it. That
is exactly the kind of property the project exists to find, and it is now a
measured metric (`Fly.stability()`) reported per network in experiment 2.

### Integration step

The oscillatory modes at radius ~2.3 are badly under-damped by forward Euler at
dt = 5 ms (multiplier 0.98 per step where the true decay is 0.82). The game and
everything built on it integrate at **dt = 2 ms** (`model.DT_PLAY`), where the
two agree to within 3%. Experiment 1's dt = 5 ms is left as it was.

### What this does to the rest of the project

- Every number in experiment 2 is in the play regime. It is a different model
  from experiment 1 in one documented parameter, and part A0 of experiment 2
  records both regimes' stability so the change is measured, not asserted.
- The chaotic regime is kept as the default of `model.build()` so experiment 1
  stays exactly reproducible. It is not used for anything else.
- Photoreceptor noise is now the *only* noise in the system. Experiment 1's
  0.03 per receptor per trial is used where noise is wanted; the untrained-play
  numbers are reported noise-free and are deterministic.
