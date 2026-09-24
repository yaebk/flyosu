"""Experiment 21 (pre-registered, docs/PREREGISTRATION_E21.md): does the
trained fly's play depend on the wiring?

**Comparison thread.**  Every network -- the real FlyWire connectome and 20
degree-, weight- and sign-preserving rewired controls -- gets round 23's
recipe applied to itself: its own calibration ensemble, its own 48-component
projection, its own ridge readout, timing offsets and release levels fitted on
the same 36 synthetic charts plus the same 102 tuning-map clips.  Each then
plays the 30 held-out 4K difficulties once.  Primary endpoint: mean accuracy
over those 30.

The freeze: controls first, committed; the real network only after, once.

    SHARD=i NSHARD=n python experiments/e21_trained_wiring.py controls
    python experiments/e21_trained_wiring.py merge
    python experiments/e21_trained_wiring.py real      # refuses until 20/20
    python experiments/e21_trained_wiring.py report
"""
from __future__ import annotations

import glob
import json
import os
import sys
import time

os.environ["DIET"] = "fast_sm20_k48"
os.environ["APPROACH_MS"] = "250"

import numpy as np  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import e20_beatmaps as B  # noqa: E402
import e20_realfit as RF  # noqa: E402

from flyosu import encoder as E, model as M, play as P, reservoir as R  # noqa: E402
from flyosu.controller import calibration_states  # noqa: E402

PATH = os.path.join(B.RESULTS, "e21_trained_wiring.json")
SHARD = os.environ.get("SHARD")
NSHARD = int(os.environ.get("NSHARD", 1))
SHARD_PATH = PATH if SHARD is None else PATH[:-5] + f"_shard{int(SHARD)}of{NSHARD}.json"

N_CONTROLS = 20
K = 48
RECIPE = dict(diet="fast_sm20_k48", approach_ms=250.0, refractory_ms=100.0, smooth_ms=20.0,
              k=K, n_syn=36, per_map=6, clip_s=RF.CLIP_S, hold_oracle=True,
              tail_lead_ms=130.0, release_levels=list(B.FIT["release"]),
              project_on_record=True, theta=B.THETA, noise=B.NOISE,
              train_seed=B.TRAIN_SEED, play_seed=4242)


def _p(n_ge, n):
    return (n_ge + 1) / (n + 1)


_MAPS = {}


def maps():
    """(training clips, held-out rows), loaded once per process.  The map set
    is chosen explicitly each time: ``B.charts`` reads a module global, and a
    shard measures several networks in one process."""
    if not _MAPS:
        B.MAP_SET = "tune"
        train, _ = RF.pools()
        _MAPS["train"] = tuple(c for _, ev in train for c in RF.pick(ev, RECIPE["per_map"]))
        B.MAP_SET = "holdout"
        _MAPS["held"] = sorted(B.charts(), key=lambda r: r["events_per_s"])
        B.MAP_SET = "tune"
        if any(r["song"].startswith(B.TUNING_SONGS) for r in _MAPS["held"]):
            raise SystemExit("a tuning song is in the held-out set")
    return _MAPS["train"], _MAPS["held"]


def measure(label: str, kw: dict) -> dict:
    t0 = time.time()
    fly = M.build(regime="play", **kw)
    player = P.Player.untrained(fly, theta=B.THETA, noise=B.NOISE, encoder=E.Encoder(fly.ret))
    player.controller.refractory_ms = RECIPE["refractory_ms"]
    player.controller.smooth_ms = RECIPE["smooth_ms"]
    stab = {k: (bool(v) if isinstance(v, (bool, np.bool_)) else float(v))
            for k, v in fly.stability(player.r0).items()}
    states = calibration_states(fly, player.r0)
    # Declared: a network whose calibration ensemble has rank below 48 is
    # fitted at its rank, flagged, and kept.
    try:
        feats = R.PopulationProjection.fit(fly, player.r0, k=K, states=states)
    except ValueError:
        X = np.array([s[fly.readout.dn_local] for s in states], dtype=np.float64)
        S = np.linalg.svd(X - X.mean(0), compute_uv=False)
        rank = int((S > S[0] * 1e-9).sum())
        feats = R.PopulationProjection.fit(fly, player.r0, k=rank, states=states)
    extra, rows = maps()
    specs = tuple((s[0], s[1], RECIPE["approach_ms"]) + tuple(s[2:]) for s in B.FIT["specs"])
    rr = R.RidgeReadout(player, n_charts=RECIPE["n_syn"], n_notes=B.N_NOTES_FIT,
                        seed=B.TRAIN_SEED, chart_specs=specs, extra_charts=extra,
                        release_levels=tuple(RECIPE["release_levels"]), hold_oracle=True,
                        tail_lead_ms=RECIPE["tail_lead_ms"], project_on_record=True)
    rr.features = feats
    rr.record()
    diag = rr.solve()
    t_fit = time.time() - t0
    results = player.play_many([r["chart"] for r in rows], seeds=[RECIPE["play_seed"]] * len(rows))
    maps = []
    for r, pr in zip(rows, results):
        maps.append({"song": r["song"], "version": r["version"],
                     "events_per_s": r["events_per_s"], "notes": len(r["chart"]),
                     "accuracy": float(pr.accuracy), "n_stray": int(pr.n_stray),
                     "loss": B.loss_breakdown(r["chart"], pr)})
    acc = float(np.mean([m["accuracy"] for m in maps]))
    notes = sum(m["notes"] for m in maps)
    out = {"label": label, "k": int(feats.k), "rank_flag": bool(feats.k < K),
           "stability": stab, "train_reward": diag["train_reward"],
           "lanes": diag["lanes"], "accuracy": acc,
           "stray_per_note": sum(m["n_stray"] for m in maps) / notes,
           "maps": maps, "seconds_fit": round(t_fit, 1),
           "seconds": round(time.time() - t0, 1)}
    print(f"  {label:<18s} held-out accuracy {acc:.3f}  stray/note "
          f"{out['stray_per_note']:.4f}  k {feats.k}  ({out['seconds']:.0f}s)", flush=True)
    return out


def _fresh():
    return {"recipe": RECIPE, "n_controls": N_CONTROLS, "runs": []}


def run_controls():
    res = B._load(SHARD_PATH, _fresh())
    done = {r["label"] for r in res["runs"]}
    if SHARD is not None:
        done |= {r["label"] for r in B._load(PATH, {"runs": []})["runs"]}
    plan = [(f"rewired #{s}", {"shuffle_seed": s}) for s in range(1, N_CONTROLS + 1)]
    if SHARD is not None:
        plan = [pk for i, pk in enumerate(plan) if i % NSHARD == int(SHARD)]
    print(f"controls -> {os.path.basename(SHARD_PATH)} ({len(done)} done, {len(plan)} planned)",
          flush=True)
    for label, kw in plan:
        if label in done:
            continue
        res["runs"].append(measure(label, kw))
        with open(SHARD_PATH, "w") as fh:
            json.dump(res, fh, indent=1)


def run_real():
    res = B._load(PATH, None)
    ctl = [] if res is None else [r for r in res["runs"] if r["label"].startswith("rewired")]
    if len(ctl) < N_CONTROLS:
        raise SystemExit(f"the freeze: {len(ctl)}/{N_CONTROLS} controls measured; "
                         "finish and commit the controls before the real network")
    if any(r["label"] == "real connectome" for r in res["runs"]):
        raise SystemExit("the real network is already measured; refusing to overwrite")
    res["runs"].append(measure("real connectome", {}))
    with open(PATH, "w") as fh:
        json.dump(res, fh, indent=1)
    report(res)


def merge():
    res = B._load(PATH, _fresh())
    seen = {r["label"] for r in res["runs"]}
    for f in sorted(glob.glob(PATH[:-5] + "_shard*of*.json")):
        got = B._load(f, {"runs": []})
        if got.get("recipe") != RECIPE:
            raise SystemExit(f"{f} holds a different recipe; refusing to merge")
        for r in got["runs"]:
            if r["label"] not in seen:
                res["runs"].append(r); seen.add(r["label"])
    with open(PATH, "w") as fh:
        json.dump(res, fh, indent=1)
    n = len([r for r in res["runs"] if r["label"].startswith("rewired")])
    print(f"merged -> {n}/{N_CONTROLS} controls")


def report(res):
    ctl = np.array([r["accuracy"] for r in res["runs"] if r["label"].startswith("rewired")])
    print(f"controls ({len(ctl)}): mean {ctl.mean():.3f} +- {ctl.std(ddof=1):.3f}, "
          f"min {ctl.min():.3f}, max {ctl.max():.3f}")
    print("  sorted: " + " ".join(f"{x:.3f}" for x in np.sort(ctl)))
    flagged = [r["label"] for r in res["runs"] if r["rank_flag"]]
    if flagged:
        print(f"  fitted below k = {K}: {', '.join(flagged)}")
    real = [r for r in res["runs"] if r["label"] == "real connectome"]
    if real:
        a = real[0]["accuracy"]
        n_ge = int((ctl >= a).sum())
        print(f"real {a:.3f}: n_ge {n_ge}/{len(ctl)}, p = {_p(n_ge, len(ctl)):.3f}, "
              f"effect {(a - ctl.mean()) / ctl.std(ddof=1):+.2f} control SD")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "controls":
        run_controls()
    elif cmd == "real":
        run_real()
    elif cmd == "merge":
        merge()
    elif cmd == "report":
        report(B._load(PATH, _fresh()))
    else:
        raise SystemExit(__doc__)
