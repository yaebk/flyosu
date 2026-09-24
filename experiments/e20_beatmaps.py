"""
Experiment 20 -- real beatmaps, at last.

**Engineering, not a comparison.**  Real connectome only, no controls, no
p-values.  Nothing here bears on whether the real wiring beats rewired wiring.

Step 12 of the plan has been "built, not verified" since the beginning: the
parser reads .osu both ways and `play_osu.py` can drive a client, but no real
beatmap had ever been played, so every number this project has produced came
from `stage_chart`.  Three .osz archives are now in `osumaps/`, seventeen 4K
mania difficulties between them, and this plays all of them.

**The gap this is measuring.**  Experiment 18 saturated the synthetic
curriculum: 1.000 up to about three notes a second, 0.988 at four, falling to
0.718 at five.  The *easiest* of these seventeen difficulties is 3.06 notes a
second and the hardest is 16.3.  So this is not expected to go well, and that
is the point -- it converts "the fly plays osu!mania" from a claim about
synthetic charts into a measured statement about real ones.

Three further ways real maps differ from anything tested:

* **Hold notes**, 9% to 67% of the notes depending on difficulty.  These were
  judged head-only until experiment 18 added `release`, which means a run of
  this before that change would have scored nonsense.
* **Same-lane gaps below the refractory.**  Two difficulties reach 76 and 80 ms,
  inside the controller's 150 ms dead time, so the constraint experiment 18
  found unreachable on synthetic charts is reached here.
* **OD 6.0 to 8.0**, so the judgment windows vary between maps; the judge reads
  it from the chart, so this is handled, but it means accuracy is not directly
  comparable across difficulties.

The readout is the best one experiment 18 produced -- pca32, 132 parameters,
fitted on stage-4 charts at 600/450/350/250 ms with a 400 ms approach -- and it
is fitted on *synthetic* charts and then asked to play real ones with nothing
refitted.  That is the honest test and also the only one available: fitting on
the maps being scored would be the threshold-sweep mistake all over again.

    python -m experiments.e20_beatmaps survey
    NSHARD=6 SHARD=0 python -m experiments.e20_beatmaps play
    python -m experiments.e20_beatmaps merge
    python -m experiments.e20_beatmaps report
"""

from __future__ import annotations

import collections
import glob
import json
import os
import sys
import time
import zipfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flyosu import beatmap, encoder as E, learn as L, model as M, play as P, reservoir as R  # noqa: E402
from flyosu.controller import calibration_states  # noqa: E402
from flyosu.mania import ACC_WEIGHT  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(ROOT, "results")
MAPS = os.path.join(ROOT, "osumaps")
APPROACH_MS = float(os.environ.get("APPROACH_MS", 400.0))   # experiment 18's optimum
_DIET = os.environ.get("DIET", "hold")
# Which maps.  The three songs every earlier result was measured on are the
# tuning set: readouts have been chosen by looking at them, so their scores are
# selection-optimistic.  Every other archive in osumaps/ -- six songs added
# after the choice was made, and anything added later -- is held out, scored
# only at milestones and never used to choose between versions.
TUNING_SONGS = ("2298007 ", "2543258 ", "2600298 ")
MAP_SET = os.environ.get("MAP_SET", "tune")                  # tune | holdout
PATH = os.path.join(RESULTS, f"e20_beatmaps{'' if _DIET == 'nohold' else '_' + _DIET}.json")
if APPROACH_MS != 400.0:
    PATH = PATH[:-5] + f"_a{APPROACH_MS:.0f}.json"
if MAP_SET != "tune":
    PATH = PATH[:-5] + f"_{MAP_SET}.json"
SHARD = os.environ.get("SHARD")
NSHARD = int(os.environ.get("NSHARD", 1))
SHARD_PATH = PATH if SHARD is None else PATH[:-5] + f"_shard{int(SHARD)}of{NSHARD}.json"

THETA = 1.5
NOISE = 0.03
# Experiment 18's winning density diet, plus hold charts.  Real maps are 9 to
# 67 per cent hold notes, and the first run of this experiment used a diet with
# none at all -- which was fine as a measurement of the gap and is the wrong
# thing to keep now that the fly can see a hold and the fit can sustain through
# one.  FIT_NOHOLD is the original, kept so the two can be compared.
#
# FIT_BOTH is the generalist: experiment 18's full density ladder down to
# 200 ms *plus* the two hold charts, on a bigger chart budget so that adding
# holds does not cost density.  A real map is 9 to 67 per cent holds at 3 to 16
# events a second, so a specialist in either skill is the wrong shape for it.
FIT_NOHOLD = dict(specs=((4, 600.0), (4, 450.0), (4, 350.0), (4, 250.0)), n_charts=16, k=32)
FIT_HOLD = dict(specs=((4, 600.0), (4, 350.0), (4, 250.0), (7, 600.0), (7, 400.0)),
                n_charts=20, k=32)
FIT_BOTH = dict(specs=((4, 600.0), (4, 450.0), (4, 350.0), (4, 250.0), (4, 200.0),
                       (7, 600.0), (7, 400.0)), n_charts=28, k=32)
# FIT_BOTH_REL adds the per-lane hold-release levels and the re-press rule
# (``Controller.release``): the first run of FIT_BOTH lost the fast maps because
# over half their holds are followed in the same lane within 100 ms.
FIT_BOTH_REL = dict(FIT_BOTH, release=tuple(round(0.05 * i, 2) for i in range(21)))
# ...recorded with the hold oracle (``reservoir.HoldOracle``; without it the fit
# never sees a hold's body after the head), with stage 8 (holds followed
# closely in their own lane) in the diet, optionally with hold bodies drawn on a
# fixed grid (``Encoder.hold_grid``).
FIT_BOTH8_ORC_REL = dict(FIT_BOTH_REL, n_charts=36, oracle=True,
                         specs=FIT_BOTH["specs"] + ((8, 400.0), (8, 300.0)))
FIT_BOTH8_ORC_REL_GRID = dict(FIT_BOTH8_ORC_REL, grid=True)
FIT_BOTH_ORC_REL = dict(FIT_BOTH_REL, oracle=True)          # round 12's both_a300_orc_rel
# round 13's fast_orc_a250_r100: 150 and 125 ms chord charts, 100 ms refractory
# (run with APPROACH_MS=250)
FIT_FAST_ORC_R100 = dict(FIT_BOTH_ORC_REL, n_charts=36, refr=100.0,
                         specs=((4, 600.0), (4, 450.0), (4, 350.0), (4, 250.0), (4, 200.0),
                                (4, 150.0), (4, 125.0), (7, 600.0), (7, 400.0)))
# round 15's fast_sm20_k48, the synthetic best (0.943 over 24): 20 ms smoothing
# and 48 components on round 13's diet (run with APPROACH_MS=250)
FIT_FAST_SM20_K48 = dict(FIT_FAST_ORC_R100, k=48, smooth=20.0)
# round 18's fast_sm20_k48_lh: the same plus 0.8 and 1.2 s hold charts
FIT_FAST_SM20_K48_LH = dict(FIT_FAST_SM20_K48, n_charts=44,
                            specs=FIT_FAST_SM20_K48["specs"] + ((7, 1000.0), (7, 1500.0)))
_DIETS = {"fast_sm20_k48": FIT_FAST_SM20_K48, "fast_sm20_k48_lh": FIT_FAST_SM20_K48_LH,"nohold": FIT_NOHOLD, "hold": FIT_HOLD, "both": FIT_BOTH, "both_rel": FIT_BOTH_REL,
          "both8_orc_rel": FIT_BOTH8_ORC_REL, "both8_orc_rel_grid": FIT_BOTH8_ORC_REL_GRID,
          "both_orc_rel": FIT_BOTH_ORC_REL, "fast_orc_r100": FIT_FAST_ORC_R100}
FIT = _DIETS[_DIET]
TRAIN_SEED = 100
N_NOTES_FIT = 24


def _load(path, default):
    if os.path.exists(path):
        with open(path) as fh:
            return json.load(fh)
    return default


def charts() -> list[dict]:
    """Every 4K mania difficulty in ``osumaps/``, parsed and characterised."""
    out = []
    for f in sorted(glob.glob(os.path.join(MAPS, "*.osz"))):
        tuning = os.path.basename(f).startswith(TUNING_SONGS)
        if tuning != (MAP_SET == "tune"):
            continue
        z = zipfile.ZipFile(f)
        for n in sorted(x for x in z.namelist() if x.lower().endswith(".osu")):
            txt = z.read(n).decode("utf-8-sig", errors="replace")
            meta = {l.split(":", 1)[0]: l.split(":", 1)[1].strip()
                    for l in txt.splitlines() if ":" in l and not l.startswith("[")}
            if meta.get("Mode") != "3" or meta.get("CircleSize", "4").split(".")[0] != "4":
                continue
            c = beatmap.parse(txt, approach_ms=APPROACH_MS)
            out.append({"song": os.path.basename(f), "version": meta.get("Version", "?"),
                        "chart": c, **describe(c)})
    return out


def describe(c) -> dict:
    t, ln = c.times(), c.lanes()
    dur = max((c.end_ms - c.start_ms) / 1000.0, 1e-9)
    uniq, inv = np.unique(t, return_inverse=True)
    gaps = [np.diff(np.sort(t[ln == k])).min() for k in range(4) if (ln == k).sum() > 1]
    return {"notes": len(c), "seconds": round(dur, 1),
            "notes_per_s": round(len(c) / dur, 2),
            # events, not notes: a chord is one event.  This is the quantity
            # comparable to the synthetic "notes/s", which was 1000/interval.
            "events_per_s": round(len(uniq) / dur, 2),
            "chord_frac": round(float((np.bincount(inv) > 1).mean()), 3),
            "hold_frac": round(sum(1 for n in c.notes if n.is_hold) / len(c), 3),
            "jack_frac": round(float(np.mean(np.diff(ln) == 0)) if len(ln) > 1 else 0.0, 3),
            "min_same_lane_gap_ms": round(float(min(gaps)) if gaps else 0.0, 1),
            "od": c.od}


LOSS_KINDS = ("hold", "after_hold", "fast_jack", "chord", "tap")


def loss_breakdown(c, pr) -> dict:
    """Where a map's accuracy went.  Each note gets one kind, first match
    wins: a hold; a tap within 150 ms of a hold's tail in its own lane; a tap
    within 150 ms of the previous note in its own lane (inside the refractory);
    a tap in a chord; any other tap.  Per kind: how many notes, their accuracy,
    and their share of everything the map lost."""
    times = [n.hit_ms for n in c.notes]
    at = collections.Counter(times)
    prev = {}
    kinds = []
    for i in sorted(range(len(c.notes)), key=lambda i: times[i]):
        n = c.notes[i]
        p = prev.get(n.lane)
        if n.is_hold:
            k = "hold"
        elif p is not None and p.is_hold and n.hit_ms - p.end_ms < 150.0:
            k = "after_hold"
        elif p is not None and n.hit_ms - p.hit_ms < 150.0:
            k = "fast_jack"
        elif at[n.hit_ms] > 1:
            k = "chord"
        else:
            k = "tap"
        kinds.append((i, k))
        prev[n.lane] = n
    lost = {k: 0.0 for k in LOSS_KINDS}
    got = {k: [] for k in LOSS_KINDS}
    for i, k in kinds:
        a = ACC_WEIGHT[pr.judgments[i]] / 300.0
        got[k].append(a)
        lost[k] += 1.0 - a
    total = max(sum(lost.values()), 1e-9)
    return {k: {"n": len(got[k]), "acc": round(float(np.mean(got[k])), 3) if got[k] else None,
                "loss_share": round(lost[k] / total, 3)} for k in LOSS_KINDS}


def survey():
    rows = sorted(charts(), key=lambda r: r["events_per_s"])
    print(f"{'song':<16s}{'difficulty':<24s}{'notes':>6s}{'sec':>5s}"
          f"{'note/s':>7s}{'evt/s':>7s}{'chord':>7s}{'hold':>6s}{'jack':>6s}{'gap':>7s}{'OD':>5s}")
    for r in rows:
        print(f"{r['song'][8:24]:<16s}{r['version'][:23]:<24s}{r['notes']:>6d}"
              f"{r['seconds']:>5.0f}{r['notes_per_s']:>7.2f}{r['events_per_s']:>7.2f}"
              f"{r['chord_frac']:>7.2f}{r['hold_frac']:>6.2f}{r['jack_frac']:>6.2f}"
              f"{r['min_same_lane_gap_ms']:>6.0f}m{r['od']:>5.1f}")
    print(f"\n{len(rows)} difficulties, {sum(r['seconds'] for r in rows) / 60:.0f} min of play")
    print(f"events/s spans {rows[0]['events_per_s']:.1f} to {rows[-1]['events_per_s']:.1f}; "
          "experiment 18 saturated at about 3 and fell over at 5")


def fitted_player():
    """The best readout experiment 18 produced, fitted on synthetic charts."""
    fly = M.build(regime="play")
    player = P.Player.untrained(fly, theta=THETA, noise=NOISE,
                                encoder=E.Encoder(fly.ret, hold_grid=bool(FIT.get("grid"))))
    if "refr" in FIT:
        player.controller.refractory_ms = float(FIT["refr"])
    if "smooth" in FIT:
        player.controller.smooth_ms = float(FIT["smooth"])
    states = calibration_states(fly, player.r0)
    specs = tuple((s[0], s[1], APPROACH_MS) + tuple(s[2:]) for s in FIT["specs"])
    rr = R.RidgeReadout(player, n_charts=FIT["n_charts"], n_notes=N_NOTES_FIT,
                        seed=TRAIN_SEED, chart_specs=specs,
                        release_levels=tuple(FIT.get("release", ())),
                        hold_oracle=bool(FIT.get("oracle")))
    rr.features = R.PopulationProjection.fit(fly, player.r0, k=FIT["k"], states=states)
    rr.record()
    rr.solve()
    return player


def play():
    rows = sorted(charts(), key=lambda r: r["events_per_s"])
    if SHARD is not None:
        rows = [r for i, r in enumerate(rows) if i % NSHARD == int(SHARD)]
    res = _load(SHARD_PATH, {"approach_ms": APPROACH_MS, "fit": str(FIT), "runs": []})
    done = {(r["song"], r["version"]) for r in res["runs"]}
    print(f"fitting the experiment 18 readout ({FIT['k']} PCs, "
          f"{FIT['n_charts']} synthetic charts, {APPROACH_MS:.0f} ms approach)", flush=True)
    player = fitted_player()
    todo = [r for r in rows if (r["song"], r["version"]) not in done]
    print(f"playing {len(todo)} difficulties together", flush=True)
    # All of a shard's maps in one batched play (bit-identical to one at a
    # time, and cheaper per map); the price is that a shard checkpoints once,
    # at the end, instead of after every map.
    t0 = time.time()
    results = player.play_many([r["chart"] for r in todo], seeds=[4242] * len(todo))
    wall = time.time() - t0
    for r, pr in zip(todo, results):
        row = {k: v for k, v in r.items() if k != "chart"}
        row.update({"accuracy": float(pr.accuracy), "hit_rate": float(pr.hit_rate),
                    "n_stray": int(pr.n_stray),
                    "stray_per_note": float(pr.n_stray / max(len(r["chart"]), 1)),
                    "counts": pr.counts,
                    "loss": loss_breakdown(r["chart"], pr),
                    "wall_s": round(wall / len(todo), 1)})
        res["runs"].append(row)
        with open(SHARD_PATH, "w") as fh:
            json.dump(res, fh, indent=1)
        print(f"  {row['version'][:22]:<23s} {row['events_per_s']:>5.1f} evt/s  "
              f"acc {row['accuracy']:.3f}  hit {row['hit_rate']:.3f}  "
              f"stray/note {row['stray_per_note']:.2f}  ({row['wall_s']:.0f}s)", flush=True)
    if SHARD is None:
        report(res)


def merge():
    res = _load(PATH, {"approach_ms": APPROACH_MS, "fit": str(FIT), "runs": []})
    seen = {(r["song"], r["version"]) for r in res["runs"]}
    for f in sorted(glob.glob(PATH[:-5] + "_shard*of*.json")):
        got = _load(f, {"runs": []})
        for r in got["runs"]:
            if (r["song"], r["version"]) not in seen:
                res["runs"].append(r); seen.add((r["song"], r["version"]))
    with open(PATH, "w") as fh:
        json.dump(res, fh, indent=1)
    print(f"merged -> {len(res['runs'])} difficulties")
    report(res)


def report(res):
    runs = sorted(res["runs"], key=lambda r: r["events_per_s"])
    if not runs:
        print("nothing played yet"); return
    print(f"\n=== experiment 20: real beatmaps, {res['approach_ms']:.0f} ms approach ===")
    print("  readout fitted on synthetic stage-4 charts; nothing refitted here\n")
    print(f"  {'difficulty':<24s}{'evt/s':>7s}{'hold':>6s}{'OD':>5s}"
          f"{'acc':>8s}{'hit':>7s}{'stray/note':>12s}")
    for r in runs:
        print(f"  {r['version'][:23]:<24s}{r['events_per_s']:>7.2f}{r['hold_frac']:>6.2f}"
              f"{r['od']:>5.1f}{r['accuracy']:>8.3f}{r['hit_rate']:>7.3f}"
              f"{r['stray_per_note']:>12.2f}")
    a = np.array([r["accuracy"] for r in runs])
    e = np.array([r["events_per_s"] for r in runs])
    print(f"\n  best {a.max():.3f} ({runs[int(a.argmax())]['version'][:30]})")
    print(f"  mean {a.mean():.3f} over {len(runs)} difficulties")
    if len(runs) > 2:
        print(f"  accuracy vs events/s: r = {np.corrcoef(e, a)[0, 1]:+.2f}")
    res["summary"] = {"n": len(runs), "best": float(a.max()), "mean": float(a.mean())}
    with open(PATH, "w") as fh:
        json.dump(res, fh, indent=1)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "survey":
        survey()
    elif cmd == "merge":
        merge()
    elif cmd == "report":
        report(_load(PATH, {"approach_ms": APPROACH_MS, "runs": []}))
    else:
        play()
