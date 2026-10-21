def parse_prediction(raw: str) -> int | None:
    lines = [line.strip() for line in str(raw).splitlines() if line.strip()]
    if not lines or lines[-1] not in {"0", "1"}:
        return None
    return int(lines[-1])

def ratio(num: int, den: int) -> float | None:
    return None if den == 0 else num / den

def evaluate(response_path: Path, labels_path: Path, output: Path) -> dict[str, Any]:
    labels = {row["record_id"]: int(row["sealed_label"]) for row in read_jsonl(labels_path)}
    responses = read_jsonl(response_path)
    predictions: list[dict[str, Any]] = []
    valid = []
    invalid = 0
    for row in responses:
        if row["record_id"] not in labels:
            raise ValueError(f"Response has no sealed label: {row['record_id']}")
        prediction = parse_prediction(row.get("raw_response", ""))
        item = {"record_id": row["record_id"], "sealed_label": labels[row["record_id"]], "prediction": prediction, "raw_response": row.get("raw_response", ""), "request_status": row.get("request_status")}
        predictions.append(item)
        if prediction is None:
            invalid += 1
        else:
            valid.append(item)
    def score(items):
        tp = sum(item["prediction"] == 1 and item["sealed_label"] == 1 for item in items)
        tn = sum(item["prediction"] == 0 and item["sealed_label"] == 0 for item in items)
        fp = sum(item["prediction"] == 1 and item["sealed_label"] == 0 for item in items)
        fn = sum(item["prediction"] == 0 and item["sealed_label"] == 1 for item in items)
        recall = ratio(tp, tp + fn)
        specificity = ratio(tn, tn + fp)
        denominator = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
        # Undefined precision/F1/MCC are zero for a nonempty population;
        # an empty population has no metrics. Missing-class recall/BA stay null.
        return {
            "n": len(items),
            "confusion_matrix": {"tp": tp, "tn": tn, "fp": fp, "fn": fn},
            "accuracy_valid": ratio(tp + tn, len(items)),
            "precision": (ratio(tp, tp + fp) if tp + fp else (0.0 if items else None)),
            "recall": recall,
            "f1": (ratio(2 * tp, 2 * tp + fp + fn) if 2 * tp + fp + fn else (0.0 if items else None)),
            "balanced_accuracy": None if recall is None or specificity is None else (recall + specificity) / 2,
            "mcc": (tp * tn - fp * fn) / denominator if denominator else (0.0 if items else None),
            "predicted_vulnerable_rate_valid": ratio(tp + fp, len(items)),
        }

    observed = score(valid)
    baselines = {
        "always_vulnerable": score([{**item, "prediction": 1} for item in valid]),
        "always_non_vulnerable": score([{**item, "prediction": 0} for item in valid]),
    }
    comparison_keys = ("accuracy_valid", "precision", "recall", "f1", "mcc", "balanced_accuracy")
    metrics = {
        **observed,
        "n_responses": len(responses), "n_valid": len(valid), "n_invalid": invalid,
        "invalid_rate": ratio(invalid, len(responses)),
        "metric_population": "valid_predictions_only",
        "coverage": ratio(len(valid), len(responses)),
        "undefined_metric_policy": "nonempty: undefined precision/F1/MCC=0; missing-class recall/balanced_accuracy=null; empty: all metrics=null",
        **baselines,
        "delta_vs_trivial_baselines": {
            name: {key: None if observed[key] is None or baseline[key] is None else observed[key] - baseline[key]
                   for key in comparison_keys}
            for name, baseline in baselines.items()
        },
    }
    write_jsonl(output / "predictions.jsonl", predictions)
    write_json(output / "evaluation.json", metrics)
    return metrics