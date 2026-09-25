# Experiment 20 — the fly plays real beatmaps

**Capability thread: real connectome only, no controls, no p-values.** Nothing
here bears on whether the real wiring beats rewired wiring. Experiment 21
tested that with the round-23 recipe: 19 of 20 rewired controls play these
held-out maps better (0.911 ± 0.016 against 0.876, `RESULTS_E21.md`).

**Current best: 0.876 mean accuracy on 30 held-out 4K
difficulties** that no readout choice ever looked at, up from 0.576 for the
best readout when real maps were first played and 0.862 for the best fitted on
synthetic charts alone ([`RESULTS_E18.md`](RESULTS_E18.md), round 15). Round 23
adds clips of the tuning maps to the training charts; the held-out songs are
never fitted on.

## Maps, and the tuning / held-out split

`osumaps/` holds nine songs; their 4K mania difficulties are played (5K–9K
are skipped). The archives are not committed, because they contain the songs;
[`osumaps/README.md`](../osumaps/README.md) lists the sets to download. Rates are chord-events per second, a chord counting once, which
is the quantity comparable to the synthetic charts.

| set | songs | difficulties | events/s | hold share | role |
|---|---|---|---|---|---|
| tuning | 3 | 17 | 2.5 – 10.2 | 10 – 67 %, mean 36 % | every readout choice looked at these |
| held-out | 6 | 30 | 1.7 – 13.7 | 1 – 30 %, mean 13 % | scored only at milestones, never used to choose |

Tuning-set numbers are selection-optimistic, because versions were picked
partly by reading them. The held-out set is what to quote. The two means are
not comparable with each other: the held-out maps are easier on average and far
lighter on holds. Songs added to `osumaps/` later are held out by default
(`TUNING_SONGS` in `experiments/e20_beatmaps.py`).

Run: `DIET=<diet> APPROACH_MS=<ms> MAP_SET=holdout python experiments/e20_beatmaps.py`
(the current best is `DIET=fast_sm20_k48 APPROACH_MS=250`). Results:
`results/e20_beatmaps_<diet>_a<ms>[_holdout].json`; the density specialist's
are `e20_beatmaps.json` and `e20_beatmaps_holdout.json`.

## Held-out results

| readout | mean | ≤ 5.5 ev/s (11) | 5.5 – 8.5 (14) | > 8.5 (5) | better than the row above |
|---|---|---|---|---|---|
| density specialist (no holds in diet, 400 ms approach) | 0.576 | 0.760 | 0.521 | 0.327 | |
| round 12 (hold recording fix, release levels, 300 ms) | 0.721 | 0.866 | 0.694 | 0.477 | 29 of 30 |
| round 15 (+ dense charts, 250 ms, 100 ms refractory, 20 ms smoothing, 48 PCs) | 0.862 | 0.935 | 0.871 | 0.677 | 30 of 30 |
| **round 23** (+ 102 tuning-map clips in the fit) | **0.876** | 0.933 | **0.891** | **0.707** | **22 of 30** |

Round 23's gains are in the middle and top bands: Ruby My Dear Cruel
0.821 → 0.872, Grotesque 0.665 → 0.723, Boulafacet SHD 0.668 → 0.734. Its eight
losses are all easy maps, by at most 0.015 (Hesperides Standard 0.936 → 0.921).
Worst map is still Jepetski's Empress (12.9 events/s), 0.492 → 0.512. Stray
presses per note fall from 0.0035 to 0.0024. Results:
`results/e20_realfit_mix_holdout.json`. The round-15 figures that follow:

Best 0.984 (The Empress, EZ, 1.9 events/s); worst 0.492 (Jepetski's Empress,
12.9 events/s). The largest gains were on the hardest maps: Hesperides Master
0.513 → 0.870, The Empress SC (a 13.7 events/s stream) 0.540 → 0.720. Stray
presses: 0.0035 per note.

By kind of note (each note gets one kind, first match wins: hold; note within
150 ms of a hold's tail in its lane; note within 150 ms of the previous note in
its lane, a "fast jack"; chord note; tap):

| kind | notes | specialist | round 12 | round 15 | round 23 | share of round 23's loss |
|---|---|---|---|---|---|---|
| tap | 19,066 | 0.611 | 0.733 | 0.922 | **0.940** | 17 % |
| chord | 19,433 | 0.585 | 0.761 | 0.922 | **0.938** | 18 % |
| hold | 5,225 | 0.241 | 0.474 | 0.599 | **0.619** | 30 % |
| after a hold | 282 | 0.256 | 0.367 | 0.589 | **0.704** | 1 % |
| fast jack | 2,643 | 0.024 | 0.022 | 0.156 | 0.153 | 34 % |

## Tuning-set results, and what they decided

| readout | mean | ≤ 5.5 (7) | 5.5 – 8.5 (4) | > 8.5 (6) | verdict |
|---|---|---|---|---|---|
| density specialist | 0.576 | 0.707 | 0.506 | 0.470 | the starting point |
| hold-only diet | 0.487 | 0.726 | 0.351 | 0.300 | holds displace density |
| generalist, before the recording fix (`both_a300`) | 0.567 | 0.815 | 0.445 | 0.359 | sustains through the note after each hold |
| round 12 (`both_orc_rel`) | 0.636 | 0.818 | 0.556 | 0.477 | ahead in every band; the new base |
| round 12 + stage-8 charts | 0.635 | 0.811 | 0.553 | 0.484 | no gain |
| round 12 + grid hold rendering | 0.600 | 0.789 | 0.504 | 0.441 | worse |
| round 13 (`fast_orc_r100`) | 0.673 | 0.852 | 0.587 | 0.521 | kept |
| **round 15** (`fast_sm20_k48`) | **0.770** | 0.896 | **0.711** | **0.663** | **current base**, better than round 13 on all 17 |
| round 15 + long-hold charts (`fast_sm20_k48_lh`) | 0.759 | **0.905** | 0.695 | 0.632 | better on only 6 of 17; not adopted |

The long-hold charts fix 1.2 s holds on synthetic charts but barely move
real-map holds (0.518 → 0.521), because real holds are mostly short, and they
cost density everywhere above 5.5 events/s.

### Round 23: fitting on the tuning maps themselves

Rounds 17, 21 and 22 each changed the synthetic diet, won or tied on synthetic
charts, and lost here. So round 23 fits on the real maps too. To keep the
tuning maps able to decide, each tuning difficulty is cut into 6-second
segments by note head. Even-numbered segments form the training pool (170
clips), odd-numbered ones the decision set (153 clips, 8,658 notes) that no
fit sees. Every arm, round 15 included, is scored on the same decision clips,
each played alone from a 1 s lead-in (`experiments/e20_realfit.py`).

| arm | training charts | decision mean | better than round 15 |
|---|---|---|---|
| round 15 | 36 synthetic | 0.772 | |
| 3 clips per map | + 51 real | 0.809 | 12 of 17 |
| **6 clips per map** | **+ 102 real** | **0.815** | **11 of 17** |
| 10 clips per map | + 152 real | 0.809 | 12 of 17 |
| the whole pool | + 170 real | 0.798 | 11 of 17 |
| real clips only | 102 real, no synthetic | 0.803 | 9 of 17 |

Six per map was frozen. It improves every kind of note on the decision
clips: holds 0.529 → 0.613, the note after a hold 0.474 → 0.598, taps
0.902 → 0.938, chords 0.921 → 0.935. The gains are on the hard, hold-heavy
maps (+0.06 to +0.14); the six difficulties it loses are easy ones already
above 0.88, by at most 0.018. More real data plateaus and then slightly hurts.
Dropping the synthetic charts costs 0.012, so they still earn their place.

On the tuning maps holds are 70 % of what round 15 loses; on the held-out maps,
which are lighter on holds and full of fast jacks, it is 28 % against 30 % for
jacks.

## What is still weak

Held-out figures are round 23's.

- **Fast jacks** (0.153, 34 % of the loss). Most notes 100–150 ms apart in one
  lane are still missed, though the 100 ms refractory now allows them. Real
  clips did not move them either. Jack charts in the synthetic diet (round 21)
  lost on the tuning maps, and the tuning maps hold only 69 fast jacks, so no
  fix for them can be chosen there.
- **Holds** (0.619, 30 %). The note after a hold is largely fixed by real clips
  (0.589 → 0.704). With round 15, on the replay maps, 17–60 % of holds in each
  length band were released more than 60 ms before the tail, almost none late.
  The 130 ms tail lead was tuned when releases ran late.
  Round 22 retuned it to 80 ms: holds rose slightly (0.518 → 0.533 on the
  tuning maps) but taps and chords fell, 0.770 → 0.751 overall, so it was
  rejected. Round 21's jack charts were rejected the same way (0.741).
- **Maps above 8.5 events/s** (0.707). Synthetic chords at 8 and 10 events/s
  are 0.81 and 0.71.
- **Unexplained misses on the Easy tuning map** (read note by note from round
  15's replay, `47d7acf`; not re-read with round 23): chords on the two outer lanes 0 and 3 where one key fires
  and the other's drive peaks just under threshold; lane-0 hold heads pressed
  about 170 ms late; hold chords pressed about 55 ms early. The long early
  releases on the same map were a diet gap (training holds stopped at 480 ms).

## Tooling

- **Held-out split**: `MAP_SET=tune | holdout` (`d872e7c`).
- **Per-note loss breakdown**: each run records count, accuracy and loss share
  per kind of note (`8a21e14`).
- **Real clips in the fit**: `RidgeReadout(extra_charts=...)` fits ready-made
  charts next to the generated diet (`996808e`).
- **Projecting while recording**: `RidgeReadout(project_on_record=True)` keeps
  only the 48 features, about 14× less memory per fit. It is not bit-identical
  (features move by about 1e-13), so it is opt-in. In a side-by-side fit it
  changed no press (`38ddd06`).
- **Batched play**: `Player.play_many` steps several charts through one sparse
  product and the retina caches blobs by position, 1.6× faster (a fit's
  recording 40.4 → 23.5 s). Checked bit-identical to the previous code side by
  side on judgments, press and release times, recorded activity, fitted weights
  and experiment 19's measurement path; a test pins it (`12f51f8`).
- **Replay page**: `demo/index.html` replays the round-23 fly on all 47 4K
  difficulties from the nine songs, one 60-second window per song shared by
  its difficulties (`aec1cc0`). Each difficulty is listed with its official
  osu! star rating (`results/star_ratings.json`, from the osu! website), the
  fly's accuracy and its grade, and is marked tuning or held-out. The replay
  is an osu!mania-style stage with the song, hit sounds, combo, classic-formula
  score and a hit-error meter, plus per-key drive traces and about 1,100
  neurons at their FlyWire positions. `python experiments/demo_replay.py` fits
  the readout and writes `demo/replays.json`, `demo/replays/` and `demo/brain/`;
  `python experiments/demo_replay.py audio` rebuilds the gitignored audio from
  the archives. Replay scores are single 60-second runs, and tuning-song
  replays include sections the fly was fitted on; quote the full-map numbers
  above instead.

## History

The first run (`870f39d`) played the tuning maps with experiment 18's density
specialist: best 0.853, mean 0.576, zero stray presses. A regression put the
losses on density and hold fraction independently (R² = 0.83 over 17 maps).
Holds were drawn as their head only, so the fly could not see them at all.
Drawing hold bodies, and then recording hold charts as a perfect player would
see them (`bddd1c9`), is what made a single generalist beat the specialist in
every band (`c7b9ed9`).
