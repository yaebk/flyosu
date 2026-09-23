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

import glob
import json
import os
import sys
import time
import zipfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flyosu import beatmap, learn as L, model as M, play as P, reservoir as R  # noqa: E402
from flyosu.controller import calibration_states  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(ROOT, "results")
MAPS = os.path.join(ROOT, "osumaps")
PATH = os.path.join(RESULTS, "e20_beatmaps.json")
SHARD = os.environ.get("SHARD")
NSHARD = int(os.environ.get("NSHARD", 1))
SHARD_PATH = PATH if SHARD is None else PATH[:-5] + f"_shard{int(SHARD)}of{NSHARD}.json"

APPROACH_MS = float(os.environ.get("APPROACH_MS", 400.0))   # experiment 18's optimum
THETA = 1.5
NOISE = 0.03
# The winning recipe from experiment 18, verbatim.
FIT = dict(specs=((4, 600.0), (4, 450.0), (4, 350.0), (4, 250.0)), n_charts=16, k=32)
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
    player = P.Player.untrained(fly, theta=THETA, noise=NOISE)
    states = calibration_states(fly, player.r0)
    specs = tuple((s[0], s[1], APPROACH_MS) for s in FIT["specs"])
    rr = R.RidgeReadout(player, n_charts=FIT["n_charts"], n_notes=N_NOTES_FIT,
                        seed=TRAIN_SEED, chart_specs=specs)
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
    print(f"playing {len(rows)} difficulties", flush=True)
    for r in rows:
        if (r["song"], r["version"]) in done:
            continue
        t0 = time.time()
        pr = player.play(r["chart"], seed=4242)
        row = {k: v for k, v in r.items() if k != "chart"}
        row.update({"accuracy": float(pr.accuracy), "hit_rate": float(pr.hit_rate),
                    "n_stray": int(pr.n_stray),
                    "stray_per_note": float(pr.n_stray / max(len(r["chart"]), 1)),
                    "counts": pr.counts,
                    "wall_s": round(time.time() - t0, 1)})
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
