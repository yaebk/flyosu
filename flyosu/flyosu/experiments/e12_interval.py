"""
Experiment 12 -- does the note interval explain why delays do not help the
real connectome?

Experiment 11 gave the untrained controller per-key delays: a threshold
crossing schedules a press ``delay_ms[k]`` later instead of pressing at once.
It nearly tripled the rewired controls' untrained accuracy (0.186 -> 0.539) and
moved the real connectome almost not at all (0.196 -> 0.242), so 19 of 20
controls now beat it.  The explanation offered there was arithmetic: the real
network's channels cross so early that three of its four keys want to wait
630-652 ms, while the gap between notes in these charts is 600 ms, so the press
it schedules for one note lands while the next note is on screen.  Only 1 of 20
controls is in that position.

That was labelled a candidate, not a finding, and the control data pointed the
other way -- across the twenty controls longer delays went with *larger* gains
(rho = +0.39, p = 0.088).  This experiment runs the test experiment 11 named:
vary the note interval.  The delays are read from an 800 ms silent probe and do
not move with the interval; only the gap between notes does.

**Prediction, stated before the numbers were looked at.**  If the explanation
is right then widening the interval past ~650 ms rescues the real network
specifically:

  1. its accuracy rank among the controls improves on 19/20 at 600 ms;
  2. its gain from delays grows with interval, from +0.046 at 600 ms;
  3. at 450 ms, where its delays overrun the gap by even more, it should be no
     better and probably worse, while the controls (mean delay 242 ms) hold up;
  4. within the controls, the +0.39 correlation between mean delay and gain
     should turn negative at 450 ms, where many control delays overrun the gap
     too, and weaken at 1400 ms, where none do.

Metrics are experiment 11's, unchanged: untrained accuracy at each network's
own best theta as the primary, lane-correctness at its own best eligible theta
as the secondary, and p = (n_ge + 1) / (n + 1).  Gain from delays is the
within-network difference against the paired no-delay arm at the same interval
(experiment 7 supplies it at 600 ms).

This module is analysis only; the runs come from ``experiments.e11_delays``
with ``INTERVAL_MS`` set.

    INTERVAL_MS=1400 N_SEEDS=10 python -m experiments.e11_delays
    python -m experiments.e12_interval
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
OUT = os.path.join(RESULTS, "e12_interval.json")
E7 = os.path.join(RESULTS, "e7_wiring.json")
INTERVALS = (450.0, 600.0, 1000.0, 1400.0)
REAL = "real connectome"
APPROACH_MS = 800.0          # a note is visible this long; it does not move


def path_for(interval: float, cap: int = 1000) -> str:
    tag = "" if interval == 600.0 else f"_interval{int(interval)}"
    return os.path.join(RESULTS, f"e11_delays_cap{cap}{tag}.json")


def load(interval: float) -> dict | None:
    """Runs at one interval as ``{label: {delay arm, no-delay arm, delays}}``."""
    p = path_for(interval)
    if not os.path.exists(p):
        return None
    with open(p) as fh:
        raw = json.load(fh)
    stored = float(raw.get("interval_ms", 600.0))
    if stored != interval:
        raise SystemExit(f"{p} says interval {stored} ms, expected {interval} ms")
    base = {}
    if interval == 600.0:
        # experiment 11's published run predates the paired arm; experiment 7
        # is the same protocol without delays at the same interval, and the arm
        # reproduces it to four decimals where both exist.
        with open(E7) as fh:
            base = {r["label"]: r["band"] for r in json.load(fh)["runs"]}
    out = {}
    for r in raw["runs"]:
        nd = base.get(r["label"])
        if nd is None and "nodelay_best_accuracy" in r:
            nd = {"best_accuracy": r["nodelay_best_accuracy"],
                  "best_lane_correct": r["nodelay_best_lane_correct"]}
        if nd is None:
            continue
        out[r["label"]] = {
            "accuracy": float(r["best_accuracy"]),
            "lane_correct": float(r["best_lane_correct"]),
            "nodelay_accuracy": float(nd["best_accuracy"]),
            "nodelay_lane_correct": float(nd["best_lane_correct"]),
            "delays": list(map(float, r["delays_at_best"])),
            "max_delay": float(np.max(r["delays"])),
            "theta": float(r["best_theta"]),
        }
    return out


def controls(runs: dict, n_ctrl: int) -> list[str]:
    """The first ``n_ctrl`` rewired seeds, in seed order, so every interval is
    compared against the same control family however many finished."""
    got = [f"rewired #{s}" for s in range(1, n_ctrl + 1)]
    return [g for g in got if g in runs]


def perm_p(real: float, ctrl: np.ndarray) -> tuple[int, float]:
    n_ge = int((ctrl >= real).sum())
    return n_ge, (n_ge + 1) / (len(ctrl) + 1)


def summarise(interval: float, runs: dict, n_ctrl: int) -> dict | None:
    if REAL not in runs:
        return None
    labels = controls(runs, n_ctrl)
    if len(labels) < 3:
        return None
    r = runs[REAL]
    c = [runs[k] for k in labels]
    row = {"interval_ms": interval, "n": len(labels),
           "p_floor": 1.0 / (len(labels) + 1)}
    for key in ("accuracy", "lane_correct"):
        rv, cv = r[key], np.array([x[key] for x in c])
        n_ge, p = perm_p(rv, cv)
        gr = rv - r["nodelay_" + key]
        gc = cv - np.array([x["nodelay_" + key] for x in c])
        g_ge, gp = perm_p(gr, gc)
        row[key] = {
            "real": rv, "ctrl_mean": float(cv.mean()), "ctrl_sd": float(cv.std()),
            "n_ge": n_ge, "p": p,
            "real_nodelay": r["nodelay_" + key],
            "ctrl_nodelay_mean": float(np.mean([x["nodelay_" + key] for x in c])),
            "real_gain": float(gr), "ctrl_gain_mean": float(gc.mean()),
            "gain_n_ge": g_ge, "gain_p": gp,
        }
    # how much of each network's delay budget overruns the gap between notes
    def over(x):
        return float(np.mean(np.array(x["delays"]) > interval))
    row["delays"] = {
        "real": [round(v) for v in r["delays"]],
        "real_mean": float(np.mean(r["delays"])),
        "real_frac_over_interval": over(r),
        "ctrl_mean": float(np.mean([np.mean(x["delays"]) for x in c])),
        "ctrl_frac_over_interval": float(np.mean([over(x) for x in c])),
        "ctrl_n_any_over": int(sum(over(x) > 0 for x in c)),
        "max_delay_any": float(max([r["max_delay"]] + [x["max_delay"] for x in c])),
    }
    # Within the controls only: does wanting a longer delay predict a bigger
    # gain?  The predictor experiment 11 quoted (rho = +0.39, p = 0.088) is the
    # fraction of a network's lanes whose delay overruns the gap; the mean
    # delay is carried alongside because the overrun fraction is identically
    # zero for every network once the interval passes the 800 ms probe, and a
    # constant predictor has no correlation to report.
    from scipy.stats import spearmanr
    y = np.array([v["accuracy"] - v["nodelay_accuracy"] for v in c])
    row["ctrl_delay_vs_gain"] = {}
    for name, x in (("frac_over_interval", np.array([over(v) for v in c])),
                    ("mean_delay", np.array([np.mean(v["delays"]) for v in c]))):
        if np.ptp(x) == 0:
            row["ctrl_delay_vs_gain"][name] = {"spearman": None, "p": None,
                                               "n": len(c), "constant": float(x[0])}
        else:
            rho, pv = spearmanr(x, y)
            row["ctrl_delay_vs_gain"][name] = {"spearman": float(rho), "p": float(pv),
                                               "n": len(c), "constant": None}
    return row


def main():
    n_ctrl = int(os.environ.get("N_CTRL", 10))
    rows, missing = [], []
    for iv in INTERVALS:
        runs = load(iv)
        if runs is None:
            missing.append(iv)
            continue
        s = summarise(iv, runs, n_ctrl)
        if s is None:
            missing.append(iv)
        else:
            rows.append(s)
    if missing:
        print("no usable results yet at: " + ", ".join(f"{m:.0f} ms" for m in missing))
    if not rows:
        return

    print(f"\n=== experiment 12: per-key delays against the note interval "
          f"(n = {n_ctrl} rewired controls) ===")
    print("\n  accuracy at each network's own best theta, with delays")
    print("   interval    real   rewired mean       n>=real      p")
    for s in rows:
        a = s["accuracy"]
        print(f"   {s['interval_ms']:6.0f}    {a['real']:.3f}   {a['ctrl_mean']:.3f} "
              f"+- {a['ctrl_sd']:.3f}    {a['n_ge']:2d}/{s['n']:<2d}   {a['p']:.3f}")
    print("\n  gain from delays (with minus paired no-delay arm), accuracy")
    print("   interval    real   rewired mean   n>=real      p")
    for s in rows:
        a = s["accuracy"]
        print(f"   {s['interval_ms']:6.0f}   {a['real_gain']:+.3f}   {a['ctrl_gain_mean']:+.3f}"
              f"          {a['gain_n_ge']:2d}/{s['n']:<2d}   {a['gain_p']:.3f}")
    print("\n  lane-correctness at each network's own best eligible theta")
    print("   interval    real   rewired mean       n>=real      p     real gain")
    for s in rows:
        l = s["lane_correct"]
        print(f"   {s['interval_ms']:6.0f}    {l['real']:.3f}   {l['ctrl_mean']:.3f} "
              f"+- {l['ctrl_sd']:.3f}    {l['n_ge']:2d}/{s['n']:<2d}   {l['p']:.3f}   "
              f"{l['real_gain']:+.3f}")
    print("\n  delays wanted, and how often they overrun the gap between notes")
    print("   interval   real delays (ms)            over gap   rewired mean   over gap")
    for s in rows:
        d = s["delays"]
        print(f"   {s['interval_ms']:6.0f}   {str(d['real']):<26s} "
              f"{d['real_frac_over_interval']*100:3.0f}%       {d['ctrl_mean']:5.0f} ms"
              f"        {d['ctrl_frac_over_interval']*100:3.0f}%")
    cap = max(s["delays"]["max_delay_any"] for s in rows)
    print(f"\n  largest delay any network asked for at any theta or interval: "
          f"{cap:.0f} ms (cap 1000 ms, probe length {APPROACH_MS:.0f} ms) -- "
          f"{'non-binding' if cap < 1000 else 'BINDING'}")
    print("\n  within the controls: does wanting longer delays predict a bigger gain?")
    print("   interval   lanes over gap vs gain     mean delay vs gain")
    for s in rows:
        cells = []
        for name in ("frac_over_interval", "mean_delay"):
            c = s["ctrl_delay_vs_gain"][name]
            cells.append(f"rho {c['spearman']:+.2f}  p {c['p']:.3f}"
                         if c["spearman"] is not None
                         else f"no variance (all {c['constant']:.2f})")
        print(f"   {s['interval_ms']:6.0f}   {cells[0]:<25s}  {cells[1]}")
    print(f"\n  permutation p floor at n = {rows[0]['n']}: "
          f"{rows[0]['p_floor']:.3f}")

    with open(OUT, "w") as fh:
        json.dump({"n_ctrl": n_ctrl, "approach_ms": APPROACH_MS, "rows": rows}, fh, indent=1)
    print(f"\n  wrote {os.path.relpath(OUT, os.path.dirname(RESULTS))}")


if __name__ == "__main__":
    main()
