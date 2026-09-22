# Male CNS v1.0: loader and feasibility

Can the project move from FlyWire v783 (female brain, no ventral nerve cord) to
the male CNS v1.0 (brain + optic lobes + VNC), so that the four keys become
four real leg motor pools? This document records what `flyosu/malecns.py`
builds, every decision the data did not make, and the measurements that say
whether the existing pipeline survives the move. Nothing here has been
simulated: no `model.build()`, no calibration. Everything is graph analysis on
the cached edge arrays.

Reproduce: `python -m flyosu.malecns` (17 s, peak 0.96 GB), then
`python -m tests.test_malecns` (41 checks, 11 s). The scratch scripts that
produced the numbers are `scratch/mcns_*.py`.

## What the loader builds

`malecns.load()` returns the same `Connectome` dataclass as `connectome.load()`:
`root_id` (bodyId, sorted), `ann` row-aligned to neuron index, `pre/post/syn/
sign`. The rest of the code can be pointed at either.

| | FlyWire v783 | male CNS v1.0 (`min_weight=2`) |
|---|---|---|
| neurons | 139,262 | **166,700** |
| edges | 15,091,983 | **15,283,237** |
| synapses | 54.5 M | **113.9 M** |
| excitatory edges | 60.0% | **61.9%** |
| descending neurons | 1,303 | **1,314** |
| motor neurons in the data | 110 (brain only) | 107 brain + **708 VNC** |
| R1-R6 photoreceptors | 8,452 | **3,377** |

### Neuron universe: the 166,700 bodies with a `superclass`

The raw weights file connects 1.8 M bodies. Only 211,577 are in the annotation
table, and only 166,700 of those have a `superclass`; the other 44,877 are
glia (11,864), orphan fragments (15,866), "unimportant" (10,751) and
out-of-scope bodies. Edges touching a fragment are 83% of the raw edge list by
count, so the universe is the 166,700 annotated neurons. That drops 1.7% of
the edges between annotated bodies (glia and orphan endpoints). Unlike
`connectome.py` there is no union with edge endpoints: every row of `ann` is a
real neuron and none is NaN-filled. There are no duplicate body ids, no
duplicate (pre, post) pairs, and 70 self-loops (443 synapses).

### Edge threshold: `weight >= 2`, measured

The weights file is sorted by weight descending (verified across all 2,318
batches), so a threshold is a prefix of batches and the loader stops reading
when it reaches it. One full streaming pass (14 s) gave:

| `weight >=` | all edges | synapses | edges, both ends annotated | edges, both ends in universe | synapses (universe) |
|---|---|---|---|---|---|
| 1 | 151,856,684 | 311.8 M | 26,028,386 | 25,582,938 | 124.2 M |
| **2** | 57,670,765 | 217.6 M | 15,514,634 | **15,283,237** | **113.9 M** |
| 3 | 23,014,406 | 148.3 M | 10,653,945 | 10,520,431 | 104.4 M |
| 4 | 11,791,751 | 114.7 M | 7,984,278 | 7,899,203 | 96.5 M |
| 5 | 7,622,864 | 98.0 M | 6,300,108 | 6,242,118 | 89.9 M |
| 10 | 2,799,910 | 67.9 M | 2,769,379 | 2,753,975 | 67.3 M |

`weight >= 2` gives the same edge count as FlyWire (15.28 M vs 15.09 M) and
twice the synapses; that is the default. `load(min_weight=k)` builds a
separate cache per threshold. Weight-1 edges are 40% of the universe's edges
and 8% of its synapses.

### Sign: one transmitter per body

The neurotransmitter file has exactly one row per body (1,835,518 rows because
it covers every segment, not just neurons); no tie-breaking was needed.
`top_nt = consensus_nt` (ground truth where known, else the cell-type
prediction, else the per-body prediction — it agrees with ground truth on all
81,000 bodies that have one). Then:

| transmitter | bodies | edges | synapses | sign |
|---|---|---|---|---|
| acetylcholine | 103,720 | 8,987,824 | 67.7 M | +1 |
| GABA | 22,069 | 2,977,101 | 23.8 M | −1 |
| glutamate | 29,302 | 2,779,895 | 19.0 M | −1 |
| histamine | 7,891 | 61,690 | 0.66 M | **−1** |
| dopamine | 392 | 103,162 | 0.44 M | +1 |
| octopamine | 101 | 73,006 | 0.39 M | +1 |
| serotonin | 48 | 18,299 | 0.11 M | +1 |
| unknown (`unclear` / no row) | 3,177 | 282,260 | 1.74 M | +1 |

Dopamine, octopamine and serotonin are +1 because that is what the FlyWire
`Excitatory` column does (checked: 656k/656k dopamine edges are +1 there).
Histamine is the one place the datasets disagree: FlyWire has no histamine
class and signed 81% of R1-6 output edges +1; here all 6,091 photoreceptors
are histaminergic and their output (61,690 edges) is −1, which is the biology
(histamine-gated chloride channels on L1/L2). **The first visual synapse flips
sign between the two datasets.** The calibration is per-neuron and largely
sign-agnostic, but the L1/L2 response to light will be a decrease, not an
increase. The 3,177 unknown bodies are mostly VNC motor neurons (390 — the
readout, whose output sign is irrelevant) and central neurons (798).

### `super_class` mapping

FlyWire names where an equivalent exists, new names where it does not; the
original `superclass` column is kept. `_tbc` ("to be confirmed") classes keep
the suffix so the confident counts are exact.

| male CNS `superclass` | `super_class` | n |
|---|---|---|
| ol_intrinsic | optic | 89,403 |
| cb_intrinsic | central | 32,164 |
| ol_sensory, cb_sensory, vnc_sensory | sensory | 17,336 |
| vnc_intrinsic | **vnc_intrinsic** (no FlyWire equivalent) | 13,161 |
| visual_projection | visual_projection | 9,201 |
| ascending_neuron | ascending | 1,846 |
| descending_neuron | descending | 1,314 |
| vnc_motor | **vnc_motor** (kept apart from `motor` = brain motor neurons) | 708 |
| visual_centrifugal | visual_centrifugal | 563 |
| sensory_ascending | sensory_ascending | 537 |
| cb_efferent, vnc_efferent, efferent_ascending, efferent_descending | efferent | 110 |
| cb_motor | motor | 107 |
| cb_endocrine, vnc_endocrine | endocrine | 94 |
| ENS | ens | 50 |
| sensory_descending | sensory_descending | 12 |
| *_tbc | base name + `_tbc` | 94 |

Extra columns FlyWire does not have: `region` (optic_lobe 105,267 / brain
37,229 / vnc 20,429 / neck 3,725), `neuromere`, `nerve` (exit), `entry_nerve`,
`hex1`/`hex2`, `instance`, `status`, `flywire_type`, `manc_type`,
`side_source`, `nt_predicted`, `nt_confidence`, `nt_sign`.

### Side and position

`side` comes from `somaSide` (148,697), then `rootSide` (17,453), then the
`_L`/`_R` suffix of `instance` (2); 548 neurons have none (427 sensory, 49
ENS, 35 vnc_intrinsic_tbc). `M` maps to FlyWire's `center` (392 bodies, 10 of
them descending neurons). **Left is at high x here** (mean soma x: left 72,338
vox, right 24,741) — the mirror of FAFB, where right is +x.

`pos_*` = `soma_*` = `somaLocation`, a [x, y, z] triple in 8 nm isotropic
voxels (male-cns.janelia.org/download). 27,038 neurons have none: all 17,306
sensory neurons (their somata are outside the CNS), 8,348 optic neurons
(lamina cells whose cortex is cut, see below), 537 sensory_ascending, 432
vnc_intrinsic. The head frame recovered from landmarks (ocellar neurons
dorsal vs proboscis motor neurons ventral; antennal-lobe PNs anterior vs
Kenyon cells posterior) is, in voxel axes: **right = −x, dorsal = −y,
anterior = −z**.

## Feasibility 1: photoreceptors and the retinotopy

| | count |
|---|---|
| R1-R6 | 3,377 (right 2,265, left 1,112) |
| R7 (y/p/d/unclear) | 1,300 |
| R8 (y/p/d/unclear) | 1,329 |
| R7R8_unclear | 85 |
| R1-R6 with a soma position | **13** |
| R1-R6 with `somaSide` | 13; all 3,377 have `rootSide` (= the `instance` suffix) |
| R1-R6 status | 1,982 "Out of scope", 1,351 Reviewed, 38 Leaves |

**The retina and most of the lamina cortex are outside the imaged volume.**
R1-R6 are axon stubs entering the lamina: they have a side but no soma, so
`retina.py`'s sphere fit to R1-6 annotation points cannot be reused as is.
The 3,377 is 40% of FlyWire's 8,452, and 2:1 right:left.

There is a better route than soma positions. Fifteen columnar optic-lobe types
(L1, L2, L5, C3, T1, Mi1, Mi4, Mi9, Tm1, Tm2, Tm9, Tm20 on both eyes; L3, C2
and Tm4 on the right only) carry `assignedOlHex1/2`, a per-eye hexagonal column lattice: 879
columns on the left, 892 on the right, one L1 per column. R1-R6 output is
95% onto L1/L2/L3 by synapse count (86% onto L1/L2), and **3,335 of 3,377 R1-R6 have a hex-carrying target;
for every one of them the modal column receives 100% of its hex-target
synapses** (median 32 synapses to the best L1/L2). So each R1-R6 can be placed
on its lamina column with no ambiguity, and the column lattice is the
retinotopy — no sphere fit to the photoreceptors is needed.

Coverage is the problem. The columns that receive any R1-R6 input:

| eye | columns with R1-R6 | of | R1-R6 per column (median / max) | columns with exactly 6 |
|---|---|---|---|---|
| left | 300 | 879 | 3 / 10 | 76 |
| right | 525 | 892 | 5 / 11 | 163 |

(Columns with >6 — 12 left, 27 right — are neighbouring-cartridge
misassignments or split bodies; small.)

To place the covered patch on the eye, I fitted `retina._fit_sphere` to the
per-column mean soma of the medulla-cortex columnar cells (Mi1, Tm1, Tm2, Mi4,
Mi9, Tm9, Tm20, C3, T1; 15,608 somata), because the lamina cortex itself is
mostly cut (only 203/254 columns per eye have an L1/L2/L5 soma). That sheet is
as clean as FlyWire's lamina: radius 146/143 µm, residual sd 11.8/12.2 µm,
principal spans ~355 × 255 × 95 µm, hex-neighbour spacing median 10.9 µm with
p95 26.7 µm (a jumbled lattice would show p95 ≫ median). Raw radial angles
about the shell centre, in the recovered head frame (raw, not rescaled —
`retina.py` found raw spans undershoot the true ~150° field):

| eye | all columns az (p2–p98) | el | R1-R6 columns az | el | frontal half covered | lateral half | dorsal half | ventral half |
|---|---|---|---|---|---|---|---|---|
| left | −95 … +22 | −75 … +60 | −86 … +11 | **−30 … +64** | 43% | 25% | 60% | **8%** |
| right | −27 … +105 | −78 … +60 | −24 … +99 | −75 … +62 | 79% | 39% | 68% | 50% |

The right eye is reasonably covered, frontal more than lateral. **The left eye
has photoreceptors almost only in its dorsal half.** The project's lanes sit
at elevation −25°, i.e. in the ventral field, at azimuths −60/−20/+20/+60: the
D and F lanes fall where the left retina is essentially absent. The hex axes
are oblique to the head frame (az ≈ −4.2·hex1 + 3.4·hex2, el ≈ 2.0·hex1 +
2.7·hex2 deg per step on the left; mirrored on the right).

Verdict: a retinotopy for the male CNS is feasible and would be *more* solid
than FlyWire's (a real column lattice rather than a fitted shell), but it
should be built on the **lamina monopolar cells L1/L2 (1,767 each, one per
column, both eyes complete)** as the input layer, not on the R1-R6 stubs. That
keeps the full field in both eyes, sidesteps the histamine sign flip (drive
L1/L2 directly with the sign the encoder chooses), and costs one synapse of
biological fidelity. If the R1-R6 must be the input, the left-ventral hole
has to be declared and the lanes re-placed.

## Feasibility 2: descending → motor

| | |
|---|---|
| descending neurons | 1,314 (left 656, right 648, center 10; 480 types; 1,308 with soma) |
| VNC motor neurons | 708 (left 355, right 353; 142 types; 703 with soma; every one has a side) |
| leg motor neurons (soma in T1/T2/T3) | **500** (T1 173, T2 175, T3 152) — 87 types |
| abdominal/other MNs (A1–A10, 1 unassigned) | 208 |
| MN exit nerves | ProLN 81 / MesoLN 116 / MetaLN 122 (the leg nerves), plus ADMN, DProN, VProN, ProAN, MesoAN, AbN1–4, AbNT, PDMN, CvN, DMetaN |
| MN subclass (MANC vocabulary) | fl 135, ml 116, hl 130 (front/middle/hind leg), ad 214, wm 67 (wing), nm 24 (neck), hm 16, xm 6 |
| MN transmitter | glutamate 302, unknown 390, ACh 14, GABA 2 |
| MNs with direct DN input | **686 / 708** (leg: 480 / 500) |
| DN → MN edges / synapses | **13,448 / 225,368** (leg: 172,634) |
| DNs with direct MN output | 1,028 / 1,314 |
| MNs reachable in exactly 2 hops via vnc_intrinsic | 706 / 708 |
| synapses onto MNs by source | vnc_intrinsic 2,173,648 · descending 225,368 · ascending 133,249 · sensory 55,572 · vnc_motor 6,396 · central 79 |

Descending neurons supply 8.6% of motor-neuron input by synapse count; the VNC
intrinsic neurons supply 83%. The DN → MN pathway is direct and dense, but the
motor output will be shaped mostly by VNC premotor circuits the FlyWire model
never had.

Per (neuromere, side) cell — count of motor neurons, how many get direct DN
input, and the DN → MN synapses:

| neuromere | side | MNs | with DN input | DN→MN synapses | DN→MN edges |
|---|---|---|---|---|---|
| T1 | left | 87 | 84 | 39,506 | 2,188 |
| T1 | right | 86 | 79 | 33,998 | 1,871 |
| T2 | left | 87 | 85 | 33,832 | 1,944 |
| T2 | right | 88 | 85 | 30,117 | 1,951 |
| T3 | left | 77 | 74 | 16,883 | 954 |
| T3 | right | 75 | 73 | 18,298 | 1,072 |
| A1 | left / right | 28 / 28 | 28 / 28 | 12,096 / 11,894 | 793 / 797 |
| A2–A10 | left / right | 76 / 75 | 74 / 75 | 14,862 / 13,811 | 939 / 927 |
| NA | right | 1 | 1 | 71 | 12 |

**The project's T1L / T2L / T1R / T2R framing is available literally**: front
and middle leg motor pools by side are 87 / 87 / 86 / 88 neurons, each with
30–40k direct DN synapses. Hind legs (T3) and the abdomen are left over and can
stay in the network unread. The leg MNs come with a real muscle-level `type`
(`Ti flexor MN`, `Tr extensor MN`, `Sternal posterior rotator MN`, ...), so a
"key press" can eventually mean a specific muscle group rather than a mean
over a pool.

Top DN types by synapses onto leg MNs: DNg105 (9,435), DNge079 (7,151), DNg93
(6,704), DNg74_b (4,287), DNp31 (3,987), DNge125 (3,744), DNg108 (3,477),
DNge002 (3,453), DNg49 (3,173), DNg74_a (2,875).

One warning for `outputs.py`: **only 42% of DN → leg-MN synapses are
ipsilateral to the DN's soma.** Grouping descending neurons by soma side, as
the FlyWire readout does, does not lateralise the motor output. With the male
CNS the grouping should be by *motor neuron* side, which is unambiguous (every
MN has a side and its exit nerve).

## Feasibility 3: hops from photoreceptors to motor neurons

Directed BFS on the magnitude graph (any edge with weight ≥ 2) from the 3,377
R1-R6:

| population | reached | hops (min / median / max) |
|---|---|---|
| optic | 89,386 / 89,403 | 1 / 3 / 5 |
| visual_projection | 9,200 / 9,201 | 2 / 3 / 4 |
| central | 32,163 / 32,164 | 3 / 4 / 5 |
| descending | 1,314 / 1,314 | 2 / 4 / 5 (289 at 3 hops, 1,014 at 4) |
| vnc_intrinsic | 13,152 / 13,161 | 3 / 4 / 6 |
| vnc_motor | 708 / 708 | 3 / 4 / 5 (620 at 4 hops, 86 at 5) |
| leg MNs | 500 / 500 | 4 / 4 / 5 (419 at 4, 81 at 5) |

656 neurons are unreachable (isolated sensory stubs, ENS). Photoreceptor →
lamina → visual projection → descending → motor neuron is four synapses; the
FlyWire pipeline's retina → descending path was three. The subgraph ranking in
`subgraph.py` (signal-flow cascade from the retina to the descending neurons)
just needs its sink moved from `descending` to `vnc_motor`.

## Things that would break the existing pipeline

1. **`retina.build()` returns nothing** — it selects `super_class="sensory",
   cell_class="visual"` (6,091 cells here, fine) and then drops every cell
   without `pos_*` — all but 13. The retinotopy must come from the hex lattice
   (above), which is a new builder, not a change to `retina.py`.
2. **The first synapse is inhibitory** (histamine → −1). The rate model's
   L1/L2 will go *down* with light. Probably harmless after calibration, but
   it is a real difference from FlyWire and should be reported, not hidden.
3. **Left/right is mirrored in voxel space** (right = −x). Anything that
   inferred side from `pos_x` would flip; `side` itself is fine.
4. **`outputs.py` groups descending neurons by soma side**, which is only
   42% ipsilateral at the leg motor neurons. With real MNs, group by MN side.
5. **`super_class="motor"` is brain motor neurons only** (107); the leg pools
   are `vnc_motor`. `where(super_class="vnc_motor", neuromere=["T1","T2"])`
   gives the four pools.
6. **Ten descending neurons have `side="center"`** and 548 neurons have no
   side; `outputs.build()` silently labels them group 0.
7. **The synapse count is twice FlyWire's** for the same edge count, and
   weight-1 edges (40% of edges) are gone. `sim.normalise_input` normalises
   per postsynaptic neuron so absolute counts wash out, but the *in-degree
   distribution* differs and the calibration regime (`sigma_floor=30`) was
   tuned on FlyWire and must be re-checked with `Fly.stability()`.
8. **`vnc_intrinsic` is 13,161 neurons with no FlyWire analogue**; the
   pathway subgraph will grow (FlyWire's was 19,367 neurons), and the VNC
   premotor circuits supply 83% of MN input — the motor output is no longer
   a direct read of the descending neurons.
9. **Memory**: the loader peaks at 0.96 GB; the scratch analysis with a
   dense-ish 2-hop product peaked at 2.05 GB. Keep `signed_matrix()` calls
   sliced.

## What was not measured

No calibration, no dynamics, no spectral radius, no control networks. The
minimum-weight default was chosen by edge count only; whether the discarded
weight-1 edges matter for the pathway is unknown. The hex → angle mapping is
a raw radial map about the medulla-cortex shell in a landmark-derived head
frame; the published eye map (column → viewing direction) would replace it.
Whether `Out of scope` R1-R6 stubs (1,982 of 3,377) are complete enough that
their 3–4 synapses per body are representative is not known.

## Recommended first modelling step

Build `flyosu/retina_hex.py` (new file): input layer = L1 + L2 (3,534 cells,
one pair per column, both eyes complete), viewing direction from
(side, hex1, hex2) through the medulla-cortex sphere fit and the same affine
rescaling `retina.py` uses. Then run `subgraph.build(cx, l1l2_idx, vnc_motor
T1/T2 idx)` on the male CNS `Connectome`, read out the four leg pools by
(neuromere, MN side), and repeat experiment 1's static lane probe with
`Fly.stability()` reported, before touching the game. The result to look for
first is the untrained lane-decoding accuracy at the *motor neurons*, real vs
rewired — the measurement the project could not make on FlyWire.
