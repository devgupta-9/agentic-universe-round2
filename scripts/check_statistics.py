"""Seeded per-look null calibration; not a substitute for a field experiment."""
import json
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from controller.evidence import compare


def main():
    rng = np.random.default_rng(20261108)
    trials, comparisons = 20000, 144
    connected = rng.binomial(2000, .25, size=(trials, 2))
    engaged = rng.binomial(connected, .5)
    winners = 0
    for index in range(trials):
        arms = [{"dials": 2000, "connected": int(connected[index, j]), "engaged": int(engaged[index, j])} for j in range(2)]
        winners += int(compare(arms[0], arms[1], "engagement_rate", .02, comparisons)["winner"])
    report = {"seed": 20261108, "null_trials": trials, "comparisons_budget": comparisons,
              "false_winners": winners, "observed_per_look_false_winner_rate": winners / trials,
              "zero_event_95_percent_upper_bound": 1 - .05 ** (1 / trials) if winners == 0 else None,
              "limitation": "Independent fixed-look null pairs, not a full sequential or heterogeneous production calibration"}
    destination = ROOT / "reports" / "statistics-check.json"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
