"""
Experiment 9 -- the two structural claims, measured properly.

Experiments 5, 6 and 7 each shrank a behavioural gap the moment the controls
were given a fairer procedure.  What none of those corrections could touch are
two quantities that need no behavioural protocol at all:

  1. the spectral radius of the blank-field Jacobian (``Fly.stability``), and
  2. how low-dimensional the readout population's response ensemble is
     (``PopulationProjection`` over the 61-stimulus calibration ensemble).

Both were by-products of other experiments -- the radius of experiment 3, the
dimensionality of experiment 5 -- and neither has ever been measured as a claim
in its own right, with seeds in every control family and a stated p-value.
This does that, and asks three further questions:

  * Are they one property or two?  The retinotopy-shuffled family keeps the
    graph and holds the radius high while its PC1 wanders, which suggests two.
    Settled here with Spearman correlations across control networks.
  * Is the dimensionality an artefact of gain?  A network with a large radius
    might look low-dimensional only because one mode dominates.  So the
    participation ratio (sum(lambda))^2 / sum(lambda^2) of the full ensemble
    variance spectrum is reported alongside the PC1 fraction.
  * Do the control families even bear on these quantities?  A shuffled channel
    label changes neither the graph nor the calibration nor the neurons read,
    so it cannot move either number.  Measured anyway, and reported as the
    null control it is.

Nothing here plays the game and nothing is fitted to a chart.  Convention for
p-values is the project's: one-sided permutation, p = (n_extreme + 1)/(n + 1),
counting controls at least as extreme as the real network in the claimed
direction.

    N_REWIRED=20 N_RETINO=10 N_CHANNEL=6 python -m experiments.e9_structure
    DATASET=malecns N_REWIRED=4 N_RETINO=4 N_CHANNEL=0 python -m experiments.e9_structure
    python -m experiments.e9_structure report
"""

from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flyosu import model as M  # noqa: E402
from flyosu import reservoir as R  # noqa: E402
from flyosu.controller import calibration_states  # noqa: E402

RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
PATH = os.path.join(RESULTS, "e9_structure.json")
K_PC = 16

FAMILIES = {"rewired": ("rewired topology", "shuffle_seed"),
            "retino": ("shuffled retinotopy", "retino_seed"),
            "channels": ("shuffled channel labels", "channel_seed")}

# quantity -> (pretty name, direction the real network is claimed to sit)
QUANTITIES = {"spectral_radius": ("spectral radius", "high"),
              "pc1": ("PC1 fraction", "high"),
              "top4": ("top-4 cumulative", "high"),
              "participation_ratio": ("participation ratio", "low"),
              "pr_norm": ("PR / n_modes", "low")}


def spectrum(states, idx):
    """Full ensemble variance spectrum of the population ``idx`` over the
    calibration states, and the dimensionality summaries built from it."""
    X = np.array([s[idx] for s in states], dtype=np.float64)
    X = X - X.mean(0)
    s = np.linalg.svd(X, compute_uv=False)
    lam = s ** 2
    tot = float(lam.sum())
    frac = lam / max(tot, 1e-30)
    pr = float(tot ** 2 / max(float((lam ** 2).sum()), 1e-300))
    n_modes = int(min(X.shape))
    return {"variance_fraction": frac[:K_PC].tolist(),
            "participation_ratio": pr,
            "pr_norm": pr / n_modes,
            "n_modes": n_modes,
            "n_read": int(X.shape[1]),
            "total_variance": tot}


def measure(label, kw, dataset):
    t0 = time.time()
    fly = M.build(regime="play", dataset=dataset, **kw)
    r0 = fly.settle()
    st = fly.stability(r0=r0)
    states = calibration_states(fly, r0)
    proj = R.PopulationProjection.fit(fly, r0, k=K_PC, states=states)
    sp = spectrum(states, fly.readout.dn_local)
    out = {"label": label, "dataset": dataset,
           "spectral_radius": st["spectral_radius"], "max_real": st["max_real"],
           "drift": st["drift"], "fixed_point": bool(st["fixed_point"]),
           "max_gain": st["max_gain"],
           "explained": proj.explained.tolist(),
           "pc1": float(proj.explained[0]),
           "top4": float(proj.explained[:4].sum()),
           "seconds": round(time.time() - t0, 1)}
    out.update(sp)
    print(f"  {label:<28s} radius {out['spectral_radius']:.2f}  fp {out['fixed_point']}  "
          f"PC1 {out['pc1']:.3f}  top4 {out['top4']:.3f}  PR {out['participation_ratio']:.2f}"
          f"/{out['n_modes']}  ({out['seconds']:.0f}s)", flush=True)
    return out


def load():
    if os.path.exists(PATH):
        with open(PATH, encoding="utf-8") as fh:
            return json.load(fh)
    return {"k_pc": K_PC, "runs": []}


def save(results):
    with open(PATH, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=1)


def main():
    dataset = os.environ.get("DATASET", "flywire")
    counts = {"rewired": int(os.environ.get("N_REWIRED", 20)),
              "retino": int(os.environ.get("N_RETINO", 10)),
              "channels": int(os.environ.get("N_CHANNEL", 6))}
    results = load()
    done = {(r["label"], r["dataset"]) for r in results["runs"]}
    plan = [("real connectome", "real", {})]
    for f, (fam, kwarg) in FAMILIES.items():
        for s in range(1, counts[f] + 1):
            plan.append((f"{fam} #{s}", fam, {kwarg: s}))
    print(f"--- {dataset}: {len(plan)} networks planned ---", flush=True)
    for label, fam, kw in plan:
        if (label, dataset) in done:
            continue
        out = measure(label, kw, dataset)
        out["family"] = fam
        results = load()                    # other runs may have appended
        results["runs"].append(out)
        save(results)                       # resumable: one network at a time
    report(results)


# -- reporting -------------------------------------------------------------

def pval(real, ctrl, direction):
    """One-sided permutation p, project convention (n_extreme + 1)/(n + 1)."""
    ctrl = np.asarray(ctrl, dtype=float)
    n_ext = int((ctrl >= real).sum() if direction == "high" else (ctrl <= real).sum())
    return n_ext, len(ctrl), (n_ext + 1) / (len(ctrl) + 1)


def table(runs, dataset, quantity):
    name, direction = QUANTITIES[quantity]
    rows = [r for r in runs if r["dataset"] == dataset]
    real = [r for r in rows if r["family"] == "real"]
    if not real:
        return []
    rv = real[0][quantity]
    out = [{"family": "real", "n": 1, "mean": rv, "sd": 0.0, "min": rv, "max": rv,
            "n_extreme": None, "p": None, "degenerate": False}]
    for f, (fam, _) in FAMILIES.items():
        v = np.array([r[quantity] for r in rows if r["family"] == fam], dtype=float)
        if not len(v):
            continue
        n_ext, n, p = pval(rv, v, direction)
        # a family whose every member equals the real network on this quantity
        # is not a control for it; the p it produces is an artefact of ties
        # (and, for the radius, of ARPACK's last digit).
        deg = bool(np.allclose(v, rv, rtol=1e-6, atol=1e-9))
        out.append({"family": fam, "n": n, "mean": float(v.mean()),
                    "sd": float(v.std(ddof=1)) if n > 1 else 0.0,
                    "min": float(v.min()), "max": float(v.max()),
                    "n_extreme": n_ext, "p": None if deg else p, "degenerate": deg})
    deg_fams = {r["family"] for r in out if r.get("degenerate")}
    for name, drop in [("controls pooled, informative", deg_fams),
                       ("controls pooled, all", set())]:
        v = np.array([r[quantity] for r in rows
                      if r["family"] != "real" and r["family"] not in drop], dtype=float)
        if len(v) > 1:
            n_ext, n, p = pval(rv, v, direction)
            out.append({"family": name, "n": n, "mean": float(v.mean()),
                        "sd": float(v.std(ddof=1)), "min": float(v.min()),
                        "max": float(v.max()), "n_extreme": n_ext, "p": p,
                        "degenerate": False})
    return out


def print_table(runs, dataset, quantity):
    name, direction = QUANTITIES[quantity]
    rows = table(runs, dataset, quantity)
    if not rows:
        return
    print(f"\n{name} -- {dataset}  (real claimed {direction})")
    print(f"  {'family':<28s} {'n':>3s}  {'mean +- sd':>16s}  {'min':>7s} {'max':>7s}  "
          f"{'n_ext':>6s}  {'p':>6s}")
    for r in rows:
        ms = f"{r['mean']:.3f} +- {r['sd']:.3f}"
        ext = "-" if r["n_extreme"] is None else f"{r['n_extreme']}/{r['n']}"
        p = ("identical to real" if r.get("degenerate") else
             "-" if r["p"] is None else f"{r['p']:.3f}")
        print(f"  {r['family']:<28s} {r['n']:>3d}  {ms:>16s}  {r['min']:>7.3f} {r['max']:>7.3f}  "
              f"{ext:>6s}  {p:>6s}")


def spearman(runs, dataset, a, b, families=None, within=False):
    """Spearman across control networks.

    ``families`` restricts to a list of family names.  ``within`` ranks inside
    each family before pooling, which is the honest pooled statistic here: the
    families sit in separate blobs of the radius axis, so a raw pooled rho
    mostly reports the between-family offset, not a relationship any single
    family shows.
    """
    from scipy import stats
    rows = [r for r in runs if r["dataset"] == dataset and r["family"] != "real"]
    if families:
        rows = [r for r in rows if r["family"] in families]
    if within:
        xs, ys = [], []
        for fam in sorted({r["family"] for r in rows}):
            g = [r for r in rows if r["family"] == fam]
            gx = np.array([r[a] for r in g], dtype=float)
            gy = np.array([r[b] for r in g], dtype=float)
            if len(g) < 3 or np.ptp(gx) == 0 or np.ptp(gy) == 0:
                continue           # a family that cannot vary carries no signal
            xs.append(stats.rankdata(gx) / (len(g) + 1.0))
            ys.append(stats.rankdata(gy) / (len(g) + 1.0))
        if not xs:
            return {"n": 0, "rho": None, "p": None}
        x, y = np.concatenate(xs), np.concatenate(ys)
    else:
        x = np.array([r[a] for r in rows], dtype=float)
        y = np.array([r[b] for r in rows], dtype=float)
    if len(x) < 5 or np.ptp(x) == 0 or np.ptp(y) == 0:
        return {"n": int(len(x)), "rho": None, "p": None}
    rho, p = stats.spearmanr(x, y)
    # Fisher-z interval (Bonett-Wright se for Spearman).  A rho near zero only
    # means "independent" if this interval is narrow, so it is always printed.
    se = 1.06 / np.sqrt(len(x) - 3)
    z = np.arctanh(np.clip(rho, -0.999999, 0.999999))
    lo, hi = np.tanh(z - 1.96 * se), np.tanh(z + 1.96 * se)
    return {"n": int(len(x)), "rho": float(rho), "p": float(p),
            "ci": [float(lo), float(hi)]}


def report(results=None):
    results = load() if results is None else results
    runs = results["runs"]
    summary = {}
    for dataset in ("flywire", "malecns"):
        if not any(r["dataset"] == dataset for r in runs):
            continue
        print(f"\n================ {dataset} ================")
        summary[dataset] = {q: table(runs, dataset, q) for q in QUANTITIES}
        for q in QUANTITIES:
            print_table(runs, dataset, q)
        # size of the population read, and how many networks actually settled:
        # a smaller readout population would cap the participation ratio for
        # trivial reasons, so it is worth seeing that it does not vary.
        print(f"\nsanity -- {dataset}")
        sizes = {}
        for fam in ["real"] + [f for f, _ in FAMILIES.values()]:
            g = [r for r in runs if r["dataset"] == dataset and r["family"] == fam]
            if not g:
                continue
            nr = [r["n_read"] for r in g]
            fp = sum(bool(r["fixed_point"]) for r in g)
            sizes[fam] = {"n": len(g), "n_read_min": min(nr), "n_read_max": max(nr),
                          "fixed_points": fp}
            print(f"  {fam:<28s} n={len(g):>2d}  readout population {min(nr)}-{max(nr)} "
                  f"neurons  fixed point {fp}/{len(g)}")
        summary[dataset]["sanity"] = sizes
        print(f"\nSpearman across control networks -- {dataset}")
        # "pooled (raw)" mixes families that sit in different parts of the
        # radius axis, so it is reported but not leaned on; "pooled (within)"
        # is the family-ranked version and is the one that answers the question.
        groups = [("rewired topology", ["rewired topology"], False),
                  ("shuffled retinotopy", ["shuffled retinotopy"], False),
                  ("pooled raw, no channels", ["rewired topology", "shuffled retinotopy"], False),
                  ("pooled within-family", None, True),
                  ("pooled raw, all families", None, False)]
        corr = {}
        for pair in [("spectral_radius", "pc1"), ("spectral_radius", "top4"),
                     ("spectral_radius", "participation_ratio"),
                     ("pc1", "participation_ratio")]:
            for gname, fams, within in groups:
                key = f"{pair[0]}~{pair[1]} | {gname}"
                c = spearman(runs, dataset, pair[0], pair[1], fams, within)
                corr[key] = c
                if c["rho"] is not None:
                    print(f"  {key:<60s} n={c['n']:>2d}  rho {c['rho']:+.3f}  p {c['p']:.3f}"
                          f"  95% CI [{c['ci'][0]:+.2f}, {c['ci'][1]:+.2f}]")
        summary[dataset]["spearman"] = corr
    results["summary"] = summary
    save(results)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "report":
        report()
    else:
        main()
