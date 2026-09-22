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
