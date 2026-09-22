"""Recompute probe C for every run in the results file.

Probe C originally started from a zero state, putting a cold-start transient on
its first sample.  Models are cached, so re-running just that probe is cheap.

    python -m experiments.refresh_c
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from experiments.e1_sensorimotor import RESULTS, probe_c_approach  # noqa: E402
from flyosu import model as M  # noqa: E402

KWARG = {"rewired topology": "shuffle_seed",
         "shuffled retinotopy": "retino_seed",
         "shuffled channel labels": "channel_seed"}


def main():
    path = os.path.join(RESULTS, "e1_sensorimotor.json")
    with open(path) as fh:
        res = json.load(fh)
    for run in res["runs"]:
        if run.get("C_approach", {}).get("warmed"):
            continue
        fam = run["family"]
        if fam == "real":
            fly = M.build(verbose=False)
        else:
            seed = int(run["label"].rsplit("#", 1)[1])
            fly = M.build(verbose=False, **{KWARG[fam]: seed})
        run["C_approach"] = probe_c_approach(fly)
        print(f"  {run['label']:<30s} max|corr| = "
              f"{run['C_approach']['max_abs_correlation']:.3f}")
        del fly
    with open(path, "w") as fh:
        json.dump(res, fh, indent=1)
    print("updated", path)


if __name__ == "__main__":
    main()
