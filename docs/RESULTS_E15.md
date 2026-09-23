# Experiment 15 — a free firing edge fixes the timing and buys nothing

**Short answer: no. Changing which edge of the drive fires the key does not
favour the real connectome on any arm — 11/20 on the upward crossing, 11/20 on
the falling edge, 20/20 on the peak — and none of the free triggers comes close
to what the four declared per-key delays achieve (controls 0.196 against 0.736).
The falling edge does fix the timing almost completely, from a median 610 ms
early to 86 ms, and that improvement does not convert into accuracy. The
controller is not what has been holding the real network back.**

Raw numbers: `results/e15_trigger_interval1400.json`, `results/e15_sh*.log`.

## What was asked, and the premise that turned out to be wrong

This experiment was built on an observation from experiment 12 that **was an
artefact**: that at wide note intervals the real connectome's no-delay
lane-correctness is 1.000, so it picks the right key almost every time and
merely presses too early. That 1.000 was the press-guard fallback on 9 presses
and has been retracted — see `docs/RESULTS_E12.md`, "An oddity that turned out
to be the press guard again".

The question survives the premise, in reduced form. Experiment 8 established
that every network's channels peak 200–600 ms before the note and that no
sensory front end removes it. Experiment 11 fixed that with per-key delays,
which cost four declared numbers read off a silent probe — the most expensive
thing the untrained policy declares. This asks whether the same fix is available
for **free**, by changing which edge of the drive fires the key rather than
adding a wait:

| arm | when the key fires | extra declared parameters |
|---|---|---|
| `cross` | drive crosses threshold upward | 0 (every prior experiment) |
| `peak` | drive turns over while still above | 0 |
| `fall` | drive falls back below threshold | 0 |
| *(per-key delays, experiment 11)* | *a fixed wait after the crossing* | *4* |

## The timing is genuinely fixed

Replayed offline on one recorded drive trace, so the three rules see identical
frames, the lag from each press to the nearest same-lane note:

| trigger | presses | within 160 ms of a note | median lag |
|---|---|---|---|
| `cross` | 17 | 2 | **+610 ms** early |
| `peak` | 21 | 2 | +390 ms early |
| `fall` | 17 | **5** | **+86 ms** |

So the falling edge removes about 86% of the timing error at no declared cost.
That much works exactly as hoped.

## And it buys nothing

Untrained accuracy, each network at its own best threshold, 1400 ms interval,
20 rewired controls:

| arm | real | rewired ×20 | n ≥ real | p |
|---|---|---|---|---|
| `cross` | 0.175 | 0.187 ± 0.137 | 11/20 | 0.571 |
| `peak` | **0.000** | 0.190 ± 0.131 | **20/20** | 1.000 |
| `fall` | 0.158 | 0.196 ± 0.164 | 11/20 | 0.571 |
| *per-key delays (e11/e12)* | *0.454* | *0.736 ± 0.187* | *19/20* | *0.952* |

Three things fall out, and none of them is the hoped-for one.

**No firing edge favours the real connectome.** It is level on `cross` and
`fall` and last on `peak`. Whatever separates it from the controls is not the
edge the key fires on. The floor here is 0.048 and the three-arm Bonferroni
floor 0.143, so nothing could have been significant anyway, but the direction is
not there either.

**Free is much worse than paid.** The best free trigger gets the controls to
0.196; four declared delay numbers get them to 0.736. Fixing the *median* lag is
not the same as fixing the timing — the falling edge lands near the note on
average and with a spread far wider than the ±160 ms hit window, whereas a
per-key delay fitted to that key's own latency lands consistently. The four
numbers are buying consistency, not offset, and that is worth 0.54 of accuracy.

**`peak` fails outright on the real network**, scoring 0.000 at every threshold.
It is not broken — it fires 21 times in the trace above and does move the press
later — but with noise the drive turns over almost immediately after crossing
and the 150 ms refractory then blocks the true peak. Making it robust needs a
margin parameter, which would cost it the property that made it interesting.
**A "parameter-free" rule that needs a smoothing parameter to work is not
parameter-free**, and it is recorded here as a failed idea rather than tuned
until it passes.

## The press guard, doing its job this time

Sixteen network/arm combinations never reach 20 counted presses at any
threshold, including **real/`cross`** and **real/`peak`**, so lane-correctness is
undefined for them and is reported as `-`. The guard now returns `None` and names
every offender, after the fallback it replaced produced phantom numbers three
times in this project (`docs/RESULTS_E12.md`).

That is also why the only lane-correct row here is `fall`: real 0.500 against
controls' 0.482, 8/17, p = 0.500, with three controls dropped. Level, on the one
arm where the question can be asked at all.

## What this closes

Experiment 12's write-up called the controller the last place a behavioural
advantage could plausibly be hiding, on the strength of an observation that has
since been retracted. With that observation gone and this experiment run anyway,
**the controller is now tested and excluded.** Across the project the untrained
policy has been varied in every way anyone has thought of — shared threshold
(e6), wiring rule (e7), sensory front end (e8), per-key delays (e11), note
interval (e12), readout (e13) and now firing edge (e15) — and none of them
produces a behavioural comparison favouring the real connectome.

## Honest caveats

- **One interval (1400 ms), one stage, two 20-note charts per network.**
- **Threshold chosen on the charts being scored**, with no held-out arm.
  Experiment 13 showed that costs the real network more than its controls.
- The offline lag table is a single trace replayed open-loop; because a judged
  note leaves the playfield, the closed-loop trajectories differ between arms,
  so it diagnoses timing rather than predicting score.
- Rewired topology only.
- Three arms, Bonferroni floor 0.143; nothing here could have reached 0.05.

## What this licenses

- **Use the falling edge if you want better timing for nothing**, but do not
  expect accuracy from it; use per-key delays if you want the score.
- Do not describe `peak` as a parameter-free trigger. It needs a margin to
  survive noise and was not pursued.
- Stop looking for the behavioural advantage in the controller. Seven distinct
  parts of the untrained policy have now been varied and none of them is where
  it lives — which is consistent with it not being there.
