# Experiment 20 — the fly plays real beatmaps

**Short answer: it works. On seventeen real 4K mania difficulties from three
downloaded maps, with a readout fitted on synthetic charts and nothing
refitted, the fly scores 0.853 on the easiest and 0.576 on average, and makes
**zero stray presses on every single map**. Two things cost it accuracy, and
they are independent: note density (partial r = −0.78) and **hold notes**
(partial r = −0.77). A regression on just those two explains 83% of the
variance across seventeen difficulties. The hold penalty has a concrete cause
that is fixable: the encoder draws a hold note as a single point at its head,
so **the fly cannot see that a note is a hold at all**, and has no information
with which to time a release.**

**Engineering, not a comparison.** Real connectome only, no controls, no
p-values. Nothing here bears on whether the real wiring beats rewired wiring.

Raw numbers: `results/e20_beatmaps.json`, `results/e20_sh*.log`. Maps in
`osumaps/`.

## What was played

Step 12 has been "built, not verified" since the beginning — the parser reads
`.osu` both ways and `play_osu.py` can drive a client, but no real beatmap had
ever been played. Every number this project has produced came from
`stage_chart`. Three `.osz` archives now supply seventeen 4K mania
difficulties, from Easy to Insane, OD 6.0 to 8.0.

The readout is experiment 18's best — pca32, 132 parameters, fitted on
synthetic stage-4 charts at 600/450/350/250 ms with a 400 ms approach — applied
to real maps with **nothing refitted**. Fitting on the maps being scored would
be the threshold-sweep mistake of experiments 16 and 17 all over again.

Rates are quoted as **chord-events per second**, not notes per second, because a
chord is one event and that is the quantity comparable to the synthetic charts,
whose rate was one over the interval.

## Results

| difficulty | events/s | holds | OD | accuracy | hit rate | strays/note |
|---|---|---|---|---|---|---|
| Easy | 2.47 | 0.15 | 6.0 | **0.853** | 0.853 | 0.00 |
| Amasugi's BASIC | 2.66 | 0.27 | 6.0 | 0.715 | 0.715 | 0.00 |
| LINQAQ's ADVANCED | 4.31 | 0.27 | 6.5 | 0.706 | 0.797 | 0.00 |
| mirac1e's EXPERT | 4.87 | 0.30 | 7.0 | 0.638 | 0.732 | 0.00 |
| Normal | 5.12 | 0.24 | 6.2 | 0.717 | 0.778 | 0.00 |
| MASTER | 5.35 | 0.39 | 7.2 | 0.493 | 0.601 | 0.00 |
| **Advanced** | 5.43 | **0.11** | 7.0 | **0.829** | 0.861 | 0.00 |
| LUNATIC | 5.98 | 0.57 | 7.4 | 0.485 | 0.616 | 0.00 |
| Spark the Flame of Hope | 6.52 | 0.64 | 7.6 | 0.404 | 0.546 | 0.00 |
| Hard | 6.52 | 0.23 | 6.4 | 0.602 | 0.703 | 0.00 |
| Muses' Hyper | 7.51 | 0.46 | 6.6 | 0.533 | 0.630 | 0.00 |
| **Hyper** | 8.54 | **0.10** | 7.5 | **0.625** | 0.707 | 0.00 |
| Gsun's Insane | 9.01 | 0.51 | 6.8 | 0.536 | 0.677 | 0.00 |
| winter's Expert | 9.04 | 0.58 | 7.0 | 0.441 | 0.626 | 0.00 |
| Insane | 9.70 | 0.15 | 8.0 | 0.490 | 0.587 | 0.00 |
| Sweetie | 9.72 | 0.67 | 7.2 | 0.379 | 0.511 | 0.00 |
| Lavender | 10.18 | 0.41 | 8.0 | 0.349 | 0.463 | 0.00 |

Best 0.853, mean 0.576 over seventeen.

## Zero strays, everywhere

Not rounded to zero — **not one stray press on any of the seventeen maps**, over
17,600 notes and 32 minutes of play. That is the property experiment 16 found
the real connectome had and the rewired controls did not, holding up on charts
nothing in this project was designed around. Whatever else the fly is bad at, it
does not mash.

## Two independent problems

| | simple r with accuracy | partial r (controlling the other) |
|---|---|---|
| events per second | −0.76 | **−0.78** |
| hold-note fraction | −0.75 | **−0.77** |
| chord fraction | −0.14 | — |

Density and holds are each strongly damaging and neither explains the other.
Together:

    accuracy  ~  0.960  −  0.0347 x events/s  −  0.432 x hold_fraction        R2 = 0.83

Read literally: a chart of nothing but hold notes costs **0.43 of accuracy**, and
each extra event per second costs 0.035. Matched for density, the difference is
plain in the table — `Advanced` at 5.43 events/s with 11% holds scores 0.829,
while `MASTER` at almost the same 5.35 with 39% holds scores 0.493. `Hyper` at
8.54 events/s with 10% holds still manages 0.625, beating five easier maps that
carry more holds.

Grouped:

| | holds < 30% | holds ≥ 30% |
|---|---|---|
| under 6 events/s | 0.764 (n=5) | 0.539 (n=3) |
| 6–11 events/s | 0.572 (n=3) | 0.440 (n=6) |

## Why holds cost so much, and it is not the controller

Hit rate exceeds accuracy on 15 of the 17 maps, by 0.095 on average: the fly is
*reaching* notes it then scores badly. For a hold that is exactly the signature
of a good head and a bad tail, since a hold earns the worse of the two.

The cause is in the encoder, not the controller. `Encoder.targets` renders one
point per visible note, at that note's lane azimuth and an elevation from its
progress. A hold note is drawn as **its head and nothing else** — no body, no
tail. So the fly has no way to know that a note is a hold, how long it lasts, or
when to let go. The release policy it does have (a key stays down while its
drive is above threshold) is not tracking the tail because it *cannot*; the
drive falls when the note passes the judgment line, which has nothing to do with
where the tail is.

**This is a sensory gap, not a control failure**, and it is the single largest
identified lever left: 0.432 of accuracy on a fully-held chart, and 9% to 67% of
the notes on these maps.

## In osu! terms

`Easy` at 0.853 and `Advanced` at 0.829 are real scores on real maps — roughly a
B rank. The hardest, `Lavender` at 10.2 events/s, scores 0.349. The fly is
genuinely playing the bottom of the ladder and genuinely failing at the top,
which is a far more useful position than the project was in yesterday, when it
had never seen a real map at all.

## Honest caveats

- **Three songs.** Seventeen difficulties, but only three pieces of music, and
  mapping style is correlated within a set.
- **OD varies 6.0 to 8.0**, so accuracy is not directly comparable between rows;
  the judge reads OD from each chart, which is correct, but a map at OD 8 is
  scored on tighter windows than one at OD 6. OD correlates −0.70 with accuracy
  here and is partly confounded with difficulty.
- **One approach window (400 ms)** — experiment 18's synthetic optimum, not
  re-optimised for real maps, where the density is far higher and a shorter
  window may well be better.
- The readout was fitted on synthetic charts with no hold notes at all, so its
  poor hold performance is partly unfamiliarity as well as blindness. Those two
  cannot be separated until the encoder renders holds.
- Regression on 17 points with 2 predictors; the coefficients are indicative,
  not precise.

## What this licenses

- **Say the fly plays real osu!mania beatmaps**, best 0.853, mean 0.576 over
  seventeen difficulties, with the readout fitted on synthetic charts.
- **Quote the stray count.** Zero on every map is the most robust behavioural
  property this project has.
- **Render hold bodies in the encoder before doing anything else about holds.**
  Tuning the release policy against an input that cannot see the tail is
  pointless.
- Report events per second, not notes per second, when comparing to any
  synthetic result here.
