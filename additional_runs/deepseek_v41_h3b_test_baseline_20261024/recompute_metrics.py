"""Recompute the GRACE test baseline metrics from evaluated predictions.

Gold labels were joined from the checksummed canonical H3-B test splits after
inference. This program does not train models, select H3-B policies, or call APIs.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def binary_metrics(labels, predictions):
    if len(labels) != len(predictions) or not labels or any(y not in (0, 1) for y in labels):
        raise ValueError("Invalid evaluation cohort")
    pairs = [(y, p) for y, p in zip(labels, predictions) if p in (0, 1)]
    tn = sum(y == 0 and p == 0 for y, p in pairs)
    fp = sum(y == 0 and p == 1 for y, p in pairs)
    fn = sum(y == 1 and p == 0 for y, p in pairs)
    tp = sum(y == 1 and p == 1 for y, p in pairs)
    divide = lambda n, d: n / d if d else 0.0
    precision, recall = divide(tp, tp + fp), divide(tp, tp + fn)
    specificity = divide(tn, tn + fp)
    n, valid = len(labels), len(pairs)
    return {
        "n": n, "valid_n": valid, "invalid_n": n - valid,
        "confusion_matrix_valid_only": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
        "accuracy_all": divide(tn + tp, n),
        "accuracy_valid_only": divide(tn + tp, valid),
        "precision": precision, "recall": recall,
        "f1": divide(2 * precision * recall, precision + recall),
        "mcc": divide(tp * tn - fp * fn, math.sqrt((tp + fp)*(tp + fn)*(tn + fp)*(tn + fn))),
        "specificity": specificity, "balanced_accuracy": (recall + specificity) / 2,
        "invalid_rate": divide(n - valid, n),
        "predicted_positive_rate_all": divide(sum(p == 1 for p in predictions), n),
        "recall_all_positives": divide(tp, sum(y == 1 for y in labels)),
    }


def recompute(root):
    reports = {}
    for dataset in ("devign", "reveal"):
        folder = root / dataset / "abbf356612344183"
        records = [json.loads(line) for line in (folder / "evaluated_predictions.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
        metrics = binary_metrics([r["label"] for r in records], [r["prediction"] for r in records])
        stored = json.loads((folder / "evaluation.json").read_text(encoding="utf-8"))["metrics"]
        if metrics != stored:
            raise ValueError(f"Stored {dataset} metrics differ from evaluated predictions")
        reports[dataset] = metrics
    return reports


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    print(json.dumps(recompute(args.root), ensure_ascii=False, indent=2))
