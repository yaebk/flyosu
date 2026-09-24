"""
Audit of experiments 7, 11, 12, 13 and 15 under the declared threshold.

Those experiments read every network at its own best threshold, swept on the
charts being scored.  Accuracy cannot see stray presses, so the sweep selects
for mashing (experiments 16 and 17).  This script reads each network's stored
value at theta = 1.5 -- Player.untrained's default, never fitted -- from the
stored sweep grids and repeats the real-vs-rewired comparison there.  Nothing is
rerun.  The plan was declared first in docs/AUDIT_DECLARED_THRESHOLD.md.

    python -m experiments.audit_declared
"""

import json
import os

import numpy as np

RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
THETA = 1.5
GUARD = 20                  # every audited experiment's own MIN_COUNTED
REAL = "real connectome"


def load(name):
    with open(os.path.join(RESULTS, name)) as fh:
        return json.load(fh)


def split(runs):
    real = [r for r in runs if r["label"] == REAL]
    assert len(real) == 1, "expected exactly one real network"
    return real[0], [r for r in runs if r["label"] != REAL]


def rank(real, ctrl, higher=True):
    """Project convention: p = (n_ge + 1)/(n + 1), ties against the real network."""
    ctrl = np.asarray(ctrl, dtype=float)
    n_ge = int((ctrl >= real).sum() if higher else (ctrl <= real).sum())
    return n_ge, len(ctrl), (n_ge + 1) / (len(ctrl) + 1)


def line(tag, real, ctrl, higher=True, note=""):
    ctrl = np.asarray(ctrl, dtype=float)
    n_ge, n, p = rank(real, ctrl, higher)
    sd = ctrl.std(ddof=1) if len(ctrl) > 1 else float("nan")
    print(f"  {tag:<34s} real {real:7.3f}  ctrl {ctrl.mean():.3f} +- {sd:.3f}  "
          f"n_ge {n_ge:2d}/{n:<2d}  p {p:.3f}  {note}")


def audit_grid(tag, recs, theta_grid, metrics, counted_key="n_counted"):
    """recs: list of (label, dict holding per-theta lists).  metrics: (key, name, higher)."""
    i = [float(t) for t in theta_grid].index(THETA)
    real = next(d for lbl, d in recs if lbl == REAL)
    ctrl = [(lbl, d) for lbl, d in recs if lbl != REAL]
    n_real = real[counted_key][i]
    below = [lbl for lbl, d in ctrl if d[counted_key][i] < GUARD]
    print(f"[{tag}] theta {THETA}: real counted presses {n_real}"
          f"{' (BELOW GUARD)' if n_real < GUARD else ''}; "
          f"controls below {GUARD}: {len(below)}/{len(ctrl)}"
          + (f" ({', '.join(b.replace('rewired ', '') for b in below)})" if below else ""))
    for key, name, higher in metrics:
        if key == "lane_correct":
            if n_real < GUARD:
                print(f"  {name + ' (guarded)':<34s} cannot audit: real network below guard")
                continue
            ok = [d[key][i] for lbl, d in ctrl if d[counted_key][i] >= GUARD]
            line(name + " (guarded)", real[key][i], ok, higher)
        else:
            line(name, real[key][i], [d[key][i] for _, d in ctrl], higher)


def swept(tag, real, ctrl, higher=True):
    line("swept: " + tag, real, ctrl, higher, "(original)")


def e7():
    for fname, ds in (("e7_wiring.json", "FlyWire"), ("e7_wiring_malecns.json", "male CNS")):
        d = load(fname)
        real, ctrl = split(d["runs"])
        print(f"\n=== experiment 7, {ds}, band-rule wiring, 600 ms ===")
        swept("accuracy", real["band"]["best_accuracy"], [r["band"]["best_accuracy"] for r in ctrl])
        swept("lane-correct", real["band"]["best_lane_correct"],
              [r["band"]["best_lane_correct"] for r in ctrl])
        audit_grid("e7 " + ds, [(r["label"], r["band"]) for r in d["runs"]], d["theta"],
                   [("accuracy", "accuracy", True), ("lane_correct", "lane-correct", True)])


def e11_like(fname, tag):
    d = load(fname)
    real, ctrl = split(d["runs"])
    swept("accuracy", real["best_accuracy"], [r["best_accuracy"] for r in ctrl])
    swept("lane-correct", real["best_lane_correct"], [r["best_lane_correct"] for r in ctrl])
    audit_grid(tag, [(r["label"], r) for r in d["runs"]], d["theta"],
               [("accuracy", "accuracy (delays)", True), ("lane_correct", "lane-correct", True)])


def e11():
    print("\n=== experiment 11, per-key delays, 600 ms, cap 1000 ms (reported run) ===")
    e11_like("e11_delays_cap1000.json", "e11 cap1000")
    print("\n--- experiment 11, superseded cap 600 ms run (context only) ---")
    e11_like("e11_delays_cap600.json", "e11 cap600")


def e12():
    for iv in (450, 1000, 1400):
        print(f"\n=== experiment 12, per-key delays, interval {iv} ms ===")
        e11_like(f"e11_delays_cap1000_interval{iv}.json", f"e12 {iv}")


def e13():
    d = load("e13_readout_malecns.json")
    real, ctrl = split(d["runs"])
    print(f"\n=== experiment 13, male CNS readouts, tuning charts (primary arm "
          f"{d['summary']['primary_arm']}) ===")
    for arm in ("channels", "channels_signed", "pc4", "pc8"):
        print(f"-- arm {arm}")
        ra, ca = real["arms"][arm], [r["arms"][arm] for r in ctrl]
        swept("accuracy", ra["accuracy_at_best"], [c["accuracy_at_best"] for c in ca])
        swept("score", ra["best_score"], [c["best_score"] for c in ca])
        swept("strays/note", ra["stray_at_best"], [c["stray_at_best"] for c in ca], higher=False)
        audit_grid("e13 " + arm, [(r["label"], r["arms"][arm]) for r in d["runs"]], ra["theta"],
                   [("accuracy", "accuracy", True), ("stray_per_note", "strays/note", False),
                    ("score", "score", True), ("lane_correct", "lane-correct", True)])
        ho = [h for h in d["held_out"] if h["label"] == REAL][0]["arms"][arm]
        print(f"  held-out charts stored only at the swept theta ({ho['theta']}): not auditable")


def e15():
    d = load("e15_trigger_interval1400.json")
    real, ctrl = split(d["runs"])
    for arm in ("cross", "peak", "fall"):
        print(f"\n=== experiment 15, trigger '{arm}', 1400 ms ===")
        ra, ca = real["arms"][arm], [r["arms"][arm] for r in ctrl]
        swept("accuracy", ra["best_accuracy"], [c["best_accuracy"] for c in ca])
        audit_grid("e15 " + arm, [(r["label"], r["arms"][arm]) for r in d["runs"]], d["theta"],
                   [("accuracy", "accuracy", True), ("lane_correct", "lane-correct", True)])


if __name__ == "__main__":
    e7()
    e11()
    e12()
    e13()
    e15()
