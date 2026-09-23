# Experiment 10 — chords, fitted on chords

**Short answer: the hypothesis this project had on record is wrong. Experiment
5 found the real connectome transferring to chords worse than its rewired
controls and blamed its amplified common mode responding to both lanes at once.
Measured directly, *every* network — real and rewired — responds to a two-note
chord as almost exactly the sum of the two single notes (additivity 0.97–1.01),
and the real one shows **less** cross-talk than the controls, not more. What is
actually wrong at the `pca8` readout is a fitting pathology: refit on stage 4
and the real network is last of thirteen on chords *and equally last on single
notes*, which no chord-specific limitation can explain.**

Control family: **rewired topology, 12 seeds** (10 shared with experiment 5, so
the deficit is differenced per network). Raw numbers: `results/e10_chords.json`,
`results/e10.log`.

## Fit on stage 4, evaluate on stage 4

Identical to experiment 5 except the training stage.

| readout | real | rewired ×12 | n ≥ real | p |
|---|---|---|---|---|
| channels (20) | 0.263 | 0.236 ± 0.104 | 5/12 | 0.462 |
| pca4 (20) | 0.058 | 0.189 ± 0.126 | 9/12 | 0.769 |
| pca8 (36) | 0.050 | 0.358 ± 0.119 | **12/12** | 1.000 |
| pca16 (68) | 0.667 | 0.702 ± 0.108 | 8/12 | 0.692 |

Experiment 5's fit-on-3 → stage-4 numbers were 8/10, 9/10, 10/10, 8/10. So
refitting on chords **fixes** the `channels` deficit, leaves `pca4` and `pca16`
about where they were, and leaves `pca8` at the very bottom.

## The load-bearing table: fit on stage 4, evaluate on stage 3

| readout | real | rewired ×12 | n ≥ real | p |
|---|---|---|---|---|
| channels | 0.233 | 0.224 ± 0.079 | 5/12 | 0.462 |
| pca4 | 0.178 | 0.214 ± 0.137 | 8/12 | 0.692 |
| pca8 | 0.150 | 0.373 ± 0.105 | **12/12** | 1.000 |
| pca16 | 0.750 | 0.598 ± 0.083 | 1/12 | 0.154 |

**A network that could not represent chords would fail stage 4 and keep stage
3.** This one fails both, identically. Once fitted on stage 4, the real
network's `pca8` readout is 12/12 on chords *and* 12/12 on single notes. The
deficit is not about two notes being on screen.

What the switch costs each network in held-out stage-3 accuracy (experiment 5's
fit-on-3 against this experiment's fit-on-4):

| readout | real | rewired ×10 |
|---|---|---|
| channels | 0.414 → 0.233 (−0.181) | 0.446 → 0.232 (−0.215) |
| pca4 | 0.258 → 0.178 (−0.081) | 0.366 → 0.251 (−0.115) |
| pca8 | 0.631 → 0.150 (**−0.481**) | 0.566 → 0.391 (−0.176) |
| pca16 | 0.917 → 0.750 (−0.167) | 0.868 → 0.606 (−0.262) |

At three of four readouts the real network loses *less* than the controls.
At `pca8` it loses nearly three times as much, and the failure mode is
under-firing rather than confusion — hit rate 0.12, lane-correct 1.00, zero
strays. The offset search installed a threshold the readout almost never
crosses.

## Chord additivity, measured directly

With A the chord response, S the sum of the two single-note responses and M
their pointwise max, α = ⟨A−M, S−M⟩ / ⟨S−M, S−M⟩, so 1 is perfectly additive,
0 is saturating to the stronger input, negative is suppressive.

| | real | rewired ×12 |
|---|---|---|
| α, full trace | 0.985 | 0.990 ± 0.010 (9/12) |
| α, at the response peak | 0.679 | 0.321 ± 0.188 (0/12, p 0.077) |
| common-mode gain | 0.954 | 1.002 ± 0.011 (12/12 above) |
| uninvolved channels during a chord | **−0.11 z** | +0.64 ± 0.56 (11/12 above) |

**All thirteen networks are additive to within 3–4% of the sum.** A
2.28-radius recurrent network and a 0.63-radius one are equally linear about
chords. The recorded hypothesis — that the real network's amplified common
mode responds to both lanes together — is not supported in any form: its
common-mode gain is slightly *sub*-additive, the opposite direction, and during
a chord its two uninvolved channels stay at baseline while most controls' rise.

The one place the real network differs directionally is at the response peak,
where controls partially saturate toward the max and it keeps summing
(0.679 vs 0.321, 0/12, p = 0.077). That is one of nine additivity statistics
computed at n = 12, and it points the opposite way from the hypothesis. Not
banked.

## The correlation this experiment was built for

Additivity against each network's chord-transfer deficit, across the ten
controls present in both experiments:

| readout | ρ vs α (full) | ρ vs α (peak) |
|---|---|---|
| channels | −0.49, p 0.16 | −0.55, p 0.10 |
| pca4 | +0.06, p 0.89 | −0.13, p 0.73 |
| pca8 | +0.52, p 0.13 | +0.30, p 0.40 |
| pca16 | +0.01, p 1.00 | −0.04, p 0.92 |
| pooled | **+0.25, p 0.49** | — |

**No relationship.** It is negative at `channels` (the direction the hypothesis
predicts), flips positive at `pca8`, and vanishes elsewhere. The real network
does not sit on the `channels` trend either — it has the highest peak
additivity of the thirteen *and* the largest positive deficit.

## Verdict

1. **Not a pure transfer artefact.** Refitting recovers the real network only
   at `channels`, where it is the one network of eleven that gains (p = 0.091).
2. **Not a chord representation limit.** Under a stage-4 fit it is equally bad
   on single notes, and the direct measurement finds it *more* linear and
   *less* cross-talking than the controls.
3. **A fitting pathology.** Chord frames make the four lanes' target windows
   co-occur, and at the top-8-PC level the ridge fit on the real network cannot
   separate them. That is a hypothesis for a further experiment, not a result
   here.

Experiment 5's sentence "the real connectome transfers to chords worse than the
rewired controls" should be qualified: worse at `channels` because of a
transfer failure that refitting fixes, and worse at `pca8` for a reason that
has nothing to do with chords being on screen.

## Honest caveats

- **Rewired topology only.** The retinotopy and channel-label families were not
  re-run; these claims hold against that family and nothing else.
- `α` at the peak and the cross-talk contrast were two of nine additivity
  statistics; at n = 12 one p = 0.077 is unsurprising.
- The correlation uses the 10 seeds shared with experiment 5; the play tables
  use all 12.
- This is the sixth occasion on which treating a comparison more carefully made
  a real-connectome effect look less special rather than more.
