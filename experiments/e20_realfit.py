"""Experiment 20, round 23: fit the readout on real-map clips as well.

**Capability thread: real connectome only, no controls.**

Rounds 17, 21 and 22 each fixed a little of what they targeted on synthetic
charts and lost on the tuning maps, because every change to the synthetic diet
moves the one shared readout.  This round fits on clips of the tuning maps
themselves, next to (or instead of) round 15's synthetic diet.

The split, so the tuning maps can still decide: every tuning difficulty is cut
into ``CLIP_S``-second segments by note head; even-numbered segments are the
training pool, odd-numbered ones the decision set.  Every arm, round 15
included, is scored on the same decision clips, played one clip at a time with
the clip moved to start at 1 s.  The held-out maps are not touched here.

    ARM=syn|mix|real python experiments/e20_realfit.py
    python experiments/e20_realfit.py report
"""
from __future__ import annotations

import json
import os
import sys
import time

os.environ.setdefault("DIET", "fast_sm20_k48")
os.environ.setdefault("APPROACH_MS", "250")
os.environ["MAP_SET"] = "tune"

import numpy as np  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import e20_beatmaps as B  # noqa: E402

from flyosu import encoder as E, model as M, play as P, reservoir as R  # noqa: E402
from flyosu.controller import calibration_states  # noqa: E402
from flyosu.mania import Chart, Note  # noqa: E402

CLIP_S = float(os.environ.get("CLIP_S", 6.0))
MIN_NOTES = 4
LEAD_IN_MS = 1000.0
DECIDE_SEED = 4242

# n_syn: how many of round 15's synthetic charts; per_map: training clips per
# difficulty (None = the whole even pool), taken evenly spaced through the map.
ARMS = {
    "syn": dict(n_syn=36, per_map=0),
    "mix": dict(n_syn=36, per_map=6),
    "mix_all": dict(n_syn=36, per_map=None),
    "real": dict(n_syn=0, per_map=None),
}
ARM = os.environ.get("ARM", "syn")
PATH = os.path.join(B.RESULTS, f"e20_realfit_{ARM}.json")


def segments(c: Chart) -> list[Chart]:
    """``c`` cut by note head into CLIP_S windows, each shifted to start at
    LEAD_IN_MS.  Holds keep their full length; a window with fewer than
    MIN_NOTES notes becomes an empty placeholder so segment parity is fixed by
    time alone."""
    seg = CLIP_S * 1000.0
    t0 = min(n.hit_ms for n in c.notes)
    n_seg = int((max(n.hit_ms for n in c.notes) - t0) // seg) + 1
    bins = [[] for _ in range(n_seg)]
    for n in c.notes:
        bins[int((n.hit_ms - t0) // seg)].append(n)
    out = []
    for i, ns in enumerate(bins):
        if len(ns) < MIN_NOTES:
            out.append(None)
            continue
        d = t0 + i * seg - LEAD_IN_MS
        out.append(Chart([Note(n.lane, n.hit_ms - d, None if n.end_ms is None else n.end_ms - d)
                          for n in ns], approach_ms=c.approach_ms, od=c.od,
                         name=f"{c.name} seg{i}"))
    return out


def pools():
    """(train clips, decision rows) over every tuning difficulty."""
    train, decide = [], []
    for r in B.charts():
        segs = segments(r["chart"])
        ev = [s for s in segs[0::2] if s is not None]
        od = [s for s in segs[1::2] if s is not None]
        train.append((r, ev))
        decide += [{"song": r["song"], "version": r["version"], "clip": j, "chart": s}
                   for j, s in enumerate(od)]
    return train, decide


def pick(ev: list, n) -> list:
    if n is None or len(ev) <= n:
        return list(ev)
    return [ev[int(i)] for i in np.linspace(0, len(ev) - 1, n).round()]


def fitted_player(cfg, train):
    F = B.FIT
    fly = M.build(regime="play")
    player = P.Player.untrained(fly, theta=B.THETA, noise=B.NOISE, encoder=E.Encoder(fly.ret))
    player.controller.refractory_ms = float(F["refr"])
    player.controller.smooth_ms = float(F["smooth"])
    states = calibration_states(fly, player.r0)
    specs = tuple((s[0], s[1], B.APPROACH_MS) + tuple(s[2:]) for s in F["specs"])
    extra = tuple(c for _, ev in train for c in pick(ev, cfg["per_map"])) if cfg["per_map"] != 0 else ()
    rr = R.RidgeReadout(player, n_charts=cfg["n_syn"], n_notes=B.N_NOTES_FIT,
                        seed=B.TRAIN_SEED, chart_specs=specs, extra_charts=extra,
                        release_levels=tuple(F["release"]), hold_oracle=True,
                        tail_lead_ms=float(F.get("tail_lead", 130.0)))
    rr.features = R.PopulationProjection.fit(fly, player.r0, k=F["k"], states=states)
    t0 = time.time()
    rr.record()
    t_rec = time.time() - t0
    diag = rr.solve()
    diag.update(seconds_record=round(t_rec, 1), n_real=len(extra),
                real_notes=int(sum(len(c) for c in extra)))
    return player, diag


def run():
    cfg = ARMS[ARM]
    train, decide = pools()
    print(f"arm {ARM}: {cfg}; {sum(len(e) for _, e in train)} train clips in the pool, "
          f"{len(decide)} decision clips", flush=True)
    player, diag = fitted_player(cfg, train)
    print(f"fitted on {diag['n_real']} real clips ({diag['real_notes']} notes) + "
          f"{cfg['n_syn']} synthetic; record {diag['seconds_record']} s", flush=True)
    t0 = time.time()
    results = player.play_many([d["chart"] for d in decide], seeds=[DECIDE_SEED] * len(decide))
    rows = []
    for d, pr in zip(decide, results):
        rows.append({"song": d["song"], "version": d["version"], "clip": d["clip"],
                     "notes": len(d["chart"]), "accuracy": float(pr.accuracy),
                     "n_stray": int(pr.n_stray), "loss": B.loss_breakdown(d["chart"], pr)})
    res = {"arm": ARM, "cfg": {k: v for k, v in cfg.items()}, "clip_s": CLIP_S,
           "fit": {k: v for k, v in diag.items() if k != "lanes"}, "lanes": diag["lanes"],
           "play_s": round(time.time() - t0, 1), "clips": rows}
    with open(PATH, "w") as fh:
        json.dump(res, fh, indent=1)
    summarize(res)


def per_map(res) -> dict:
    """Note-weighted accuracy per difficulty over its decision clips."""
    by = {}
    for r in res["clips"]:
        k = (r["song"], r["version"])
        n, s = by.get(k, (0, 0.0))
        by[k] = (n + r["notes"], s + r["accuracy"] * r["notes"])
    return {k: s / n for k, (n, s) in by.items()}


def kinds(res) -> dict:
    out = {}
    for kind in B.LOSS_KINDS:
        n = sum(r["loss"][kind]["n"] for r in res["clips"])
        s = sum(r["loss"][kind]["n"] * (r["loss"][kind]["acc"] or 0.0) for r in res["clips"])
        out[kind] = (n, s / n if n else float("nan"))
    return out


def summarize(res, base=None):
    m = per_map(res)
    line = f"{res['arm']:<8s} decision mean over {len(m)} difficulties {np.mean(list(m.values())):.3f}"
    if base is not None:
        b = per_map(base)
        better = sum(m[k] > b[k] for k in m)
        line += f"  (syn {np.mean(list(b.values())):.3f}; better on {better} of {len(m)})"
    print(line)
    print("   " + "  ".join(f"{k} {a:.3f} (n={n})" for k, (n, a) in kinds(res).items()))


def report():
    base = B._load(os.path.join(B.RESULTS, "e20_realfit_syn.json"), None)
    for arm in ARMS:
        r = B._load(os.path.join(B.RESULTS, f"e20_realfit_{arm}.json"), None)
        if r is not None:
            summarize(r, None if arm == "syn" else base)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "report":
        report()
    elif len(sys.argv) > 1 and sys.argv[1] == "pools":
        tr, de = pools()
        print(f"train pool {sum(len(e) for _, e in tr)} clips, "
              f"{sum(len(c) for _, e in tr for c in e)} notes, "
              f"{sum((c.end_ms - c.start_ms) / 1000 + 1.5 for _, e in tr for c in e):.0f} s; "
              f"decision {len(de)} clips, {sum(len(d['chart']) for d in de)} notes")
    else:
        run()
