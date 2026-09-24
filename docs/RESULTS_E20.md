# Experiment 20 — the fly plays real beatmaps

**Capability thread: real connectome only, no controls, no p-values.** Nothing
here bears on whether the real wiring beats rewired wiring; the recipe would
very likely work on a rewired control too.

**Current best: 0.862 mean accuracy on 30 held-out 4K difficulties** that no
readout choice ever looked at, up from 0.576 for the best readout when real
maps were first played. The readout is fitted on synthetic charts only
([`RESULTS_E18.md`](RESULTS_E18.md), round 15); nothing is fitted on maps.

## Maps, and the tuning / held-out split

`osumaps/` holds nine songs; their 4K mania difficulties are played (5K–9K
are skipped). Rates are chord-events per second, a chord counting once, which
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
| **round 15** (+ dense charts, 250 ms, 100 ms refractory, 20 ms smoothing, 48 PCs) | **0.862** | **0.935** | **0.871** | **0.677** | **30 of 30** |

Best 0.984 (The Empress, EZ, 1.9 events/s); worst 0.492 (Jepetski's Empress,
12.9 events/s). The largest gains were on the hardest maps: Hesperides Master
0.513 → 0.870, The Empress SC (a 13.7 events/s stream) 0.540 → 0.720. Stray
presses: 0.0035 per note.

By kind of note (each note gets one kind, first match wins: hold; note within
150 ms of a hold's tail in its lane; note within 150 ms of the previous note in
its lane, a "fast jack"; chord note; tap):

| kind | notes | specialist | round 12 | round 15 | share of round 15's loss |
|---|---|---|---|---|---|
| tap | 19,066 | 0.611 | 0.733 | **0.922** | 20 % |
| chord | 19,433 | 0.585 | 0.761 | **0.922** | 21 % |
| hold | 5,225 | 0.241 | 0.474 | 0.599 | 28 % |
| after a hold | 282 | 0.256 | 0.367 | 0.589 | 2 % |
| fast jack | 2,643 | 0.024 | 0.022 | 0.156 | 30 % |

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

On the tuning maps holds are 70 % of what round 15 loses; on the held-out maps,
which are lighter on holds and full of fast jacks, it is 28 % against 30 % for
jacks.

## What is still weak

- **Fast jacks** (0.156). Most notes 100–150 ms apart in one lane are still
  missed, though the 100 ms refractory now allows them, and the training diet
  has never contained a jack chart. **Round 21**, jack charts in the diet, is
  in flight.
- **Holds** (0.599) and the note after one (0.589). On the replay maps 17–60 %
  of holds in each length band are released more than 60 ms before the tail,
  almost none late. The 130 ms tail lead was tuned when releases ran late.
  Round 22 retuned it to 80 ms: holds rose slightly (0.518 → 0.533 on the
  tuning maps) but taps and chords fell, 0.770 → 0.751 overall, so it was
  rejected. Round 21's jack charts were rejected the same way (0.741).
- **Maps above 8.5 events/s** (0.677). Synthetic chords at 8 and 10 events/s
  are 0.81 and 0.71.
- **Unexplained misses on the Easy tuning map** (read note by note from the
  replay, `02a2ba1`): chords on the two outer lanes 0 and 3 where one key fires
  and the other's drive peaks just under threshold; lane-0 hold heads pressed
  about 170 ms late; hold chords pressed about 55 ms early. The long early
  releases on the same map were a diet gap (training holds stopped at 480 ms).

## Tooling

- **Held-out split**: `MAP_SET=tune | holdout` (`aaa5b3a`).
- **Per-note loss breakdown**: each run records count, accuracy and loss share
  per kind of note (`b41a0af`).
- **Batched play**: `Player.play_many` steps several charts through one sparse
  product and the retina caches blobs by position, 1.6× faster (a fit's
  recording 40.4 → 23.5 s). Checked bit-identical to the previous code side by
  side on judgments, press and release times, recorded activity, fitted weights
  and experiment 19's measurement path; a test pins it (`07f000a`).
- **Replay page**: `demo/index.html` replays the round-15 fly on six map clips
  from five songs, each marked tuning or held-out, with the song, hit sounds,
  per-key drive traces and a view of 2,138 neurons at their FlyWire positions.
  `python experiments/demo_replay.py` fits the readout and writes
  `demo/replay_data.json` and the brain files; `python experiments/demo_replay.py audio`
  rebuilds the gitignored audio from the archives. Clip scores are single
  90-second runs; quote the full-map numbers above instead.

## History

The first run (`79f56dc`) played the tuning maps with experiment 18's density
specialist: best 0.853, mean 0.576, zero stray presses. A regression put the
losses on density and hold fraction independently (R² = 0.83 over 17 maps).
Holds were drawn as their head only, so the fly could not see them at all.
Drawing hold bodies, and then recording hold charts as a perfect player would
see them (`04b7c33`), is what made a single generalist beat the specialist in
every band (`0b8364a`).
