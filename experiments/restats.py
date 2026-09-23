"""Recompute the summary and permutation statistics from a saved results file.

    python -m experiments.restats
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from experiments.e1_sensorimotor import RESULTS, _report

with open(os.path.join(RESULTS, "e1_sensorimotor.json")) as fh:
    _report(json.load(fh))
