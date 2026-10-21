"""Refresh all 36 ledger rows from saved per-sample predictions; no LLM calls.

Usage: python tools/update_run_benchmark_metrics.py
Uses the frozen standard evaluator without changing run artifacts or their hashes.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVALUATOR = ROOT / "provenance/invalid_rerun_context8192_20261021/standard_evaluator.py"
SUMMARY = "provenance/benchmark_metrics_20261021.json"
KEYS = ("accuracy_valid", "precision", "recall", "f1", "mcc", "balanced_accuracy")
START = "<!-- benchmark-metrics:start -->"
END = "<!-- benchmark-metrics:end -->"
COLUMNS = ["Coverage (%)", "CM: TN / FP / FN / TP", "Accuracy (%) M / V / N",
           "Precision (%) M / V / N", "Recall (%) M / V / N", "F1 (%) M / V / N",
           "MCC M / V / N", "Balanced Acc (%) M / V / N", "ΔF1 (điểm %) vs V / N"]


def dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def fmt(value: float | None, *, mcc: bool = False, signed: bool = False) -> str:
    if value is None:
        return "N/A"
    if not mcc:
        value *= 100
    return format(value, ("+" if signed else "") + (".4f" if mcc else ".2f"))


def main() -> None:
    ledger_path = ROOT / "bang_quan_ly_run.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    assert len(ledger) == 36 and len({r["run_id"] for r in ledger}) == 36
    details = []
    normalized_zero_metrics = []
    for run in ledger:
        prediction_path = ROOT / run["paths"]["predictions"]
        data = prediction_path.read_bytes()
        rows = [json.loads(line) for line in data.decode("utf-8-sig").splitlines() if line.strip()]
        ids = [r["record_id"] for r in rows]
        assert len(set(ids)) == len(ids), run["run_id"]
        assert len(rows) == run["n_total"], run["run_id"]
        assert all(type(r["sealed_label"]) is int and r["sealed_label"] in (0, 1) for r in rows)
        assert sum(r["sealed_label"] == 0 for r in rows) == run["n_non_vulnerable"]
        assert sum(r["sealed_label"] == 1 for r in rows) == run["n_vulnerable"]
        generated = {}

        def capture_predictions(path, predictions):
            assert len(predictions) == len(rows)
            for source, parsed in zip(rows, predictions):
                for key in ("record_id", "sealed_label", "prediction"):
                    assert source[key] == parsed[key], (run["run_id"], source["record_id"], key)

        namespace = {"math": math, "Path": Path, "Any": Any,
                     "read_jsonl": lambda path: rows,
                     "write_jsonl": capture_predictions,
                     "write_json": lambda path, obj: generated.update(obj)}
        exec(compile(EVALUATOR.read_text(encoding="utf-8"), str(EVALUATOR), "exec"), namespace)
        metrics = namespace["evaluate"](prediction_path, prediction_path, ROOT / "unused")
        assert generated == metrics
        assert metrics["n_valid"] == run["n_valid"]
        assert metrics["n_invalid"] == run["n_invalid"]
        previous = json.loads((ROOT / run["paths"]["metrics"]).read_text(encoding="utf-8"))
        assert previous["confusion_matrix"] == metrics["confusion_matrix"], run["run_id"]
        for key in KEYS:
            a, b = previous.get(key), metrics[key]
            if a is None and b == 0 and key in ("precision", "f1", "mcc"):
                normalized_zero_metrics.append({"run_id": run["run_id"], "metric": key})
            else:
                assert a == b or (a is not None and b is not None and math.isclose(a, b, abs_tol=1e-12)), (run["run_id"], key, a, b)
        for name in ("always_vulnerable", "always_non_vulnerable", "delta_vs_trivial_baselines"):
            if name in previous:
                assert previous[name] == metrics[name], (run["run_id"], name)
        valid = [r for r in rows if r["prediction"] in (0, 1)]
        positives = sum(r["sealed_label"] for r in valid)
        negatives = len(valid) - positives
        assert metrics["always_vulnerable"]["confusion_matrix"] == {"tp": positives, "tn": 0, "fp": negatives, "fn": 0}
        assert metrics["always_non_vulnerable"]["confusion_matrix"] == {"tp": 0, "tn": negatives, "fp": 0, "fn": positives}
        if valid:
            assert metrics["always_vulnerable"]["accuracy_valid"] == positives / len(valid)
            assert metrics["always_non_vulnerable"]["accuracy_valid"] == negatives / len(valid)
        record = {"run_id": run["run_id"], "prediction_path": run["paths"]["predictions"],
                  "prediction_sha256": hashlib.sha256(data).hexdigest(),
                  "valid_record_ids_sha256": hashlib.sha256("\n".join(sorted(r["record_id"] for r in valid)).encode()).hexdigest(),
                  "n_non_vulnerable_valid": negatives, "n_vulnerable_valid": positives,
                  "metrics": metrics}
        run["benchmark"] = record
        details.append(record)

    # Keep every original metadata/link cell; replace only generated metric columns.
    md_path = ROOT / "bang_quan_ly_run.md"
    md = md_path.read_text(encoding="utf-8")
    lookup = {r["run_id"]: r for r in details}
    output = []
    in_table = False
    seen = set()
    for line in md.splitlines():
        if line.startswith("| Run ID |"):
            cells = [c.strip() for c in line.split("|")[1:-1]][:11]
            assert cells[10] == "Manifest"
            output.append("| " + " | ".join(cells + COLUMNS) + " |")
            in_table = True
        elif in_table and line.startswith("|---"):
            output.append("|" + "|".join(["---"] * (11 + len(COLUMNS))) + "|")
        elif in_table and line.startswith("| "):
            cells = [c.strip() for c in line.split("|")[1:-1]][:11]
            run_id = cells[0]
            record = lookup[run_id]
            metrics = record["metrics"]
            cm = metrics["confusion_matrix"]
            extra = [fmt(metrics["coverage"]), " / ".join(str(cm[k]) for k in ("tn", "fp", "fn", "tp"))]
            for key in KEYS:
                extra.append(" / ".join(fmt(m[key], mcc=key == "mcc") for m in
                                          (metrics, metrics["always_vulnerable"], metrics["always_non_vulnerable"])))
            extra.append(" / ".join(fmt(metrics["delta_vs_trivial_baselines"][name]["f1"], signed=True)
                                    for name in ("always_vulnerable", "always_non_vulnerable")))
            output.append("| " + " | ".join(cells + extra) + " |")
            seen.add(run_id)
        else:
            if in_table:
                in_table = False
            output.append(line)
    assert seen == set(lookup)
    md = "\n".join(output) + "\n"
    note = f"""{START}
Cách đọc các cột benchmark: **M / V / N** lần lượt là **run hiện tại / luôn đoán vulnerable (1) / luôn đoán non-vulnerable (0)**. Accuracy, Precision, Recall, F1, Balanced Accuracy và Coverage tính theo **%**; MCC từ -1 đến 1. CM của run theo thứ tự **TN / FP / FN / TP**. ΔF1 = F1 của run trừ F1 đối chứng, đơn vị **điểm phần trăm**; số dương là cao hơn đối chứng. Lớp dương là vulnerable (1).

Metric được tính lại từ prediction theo từng mẫu bằng [script cập nhật bảng](tools/update_run_benchmark_metrics.py), sử dụng trực tiếp [evaluator chuẩn đã lưu](provenance/invalid_rerun_context8192_20261021/standard_evaluator.py). Cả hai đối chứng dùng **đúng cùng các ID hợp lệ của từng run**. Invalid không vào confusion matrix hoặc mẫu số metric; Coverage = valid / tổng số mẫu. Số lớp trên tập valid, confusion matrix đầy đủ của hai đối chứng, metric chưa làm tròn và mọi chênh lệch nằm trong [JSON benchmark](provenance/benchmark_metrics_20261021.json) và trường benchmark của [JSON quản lý run](bang_quan_ly_run.json).

Tập valid có thể khác giữa các run; bảng này chưa chứng minh cải tiến giữa các cấu hình hoặc ý nghĩa thống kê. Khi xác nhận một cặp, phải chốt cùng ID, backbone và điều kiện so sánh rồi tính CI ghép cặp/McNemar cho cặp đó. Sáu nhánh ghép hai model vẫn giữ ghi chú ở trên.
{END}
"""
    if START in md:
        start, tail = md.split(START, 1)
        _, tail = tail.split(END, 1)
        md = start + note.rstrip("\n") + tail
    else:
        md = md.replace("| Run ID |", note + "\n| Run ID |", 1)
    table = [line for line in md.splitlines() if line.startswith("|")]
    assert len(table) == 38
    assert all(len(line.split("|")) == 11 + len(COLUMNS) + 2 for line in table)
    summary = {"generated_on": "2026-10-21", "source": "saved_per_sample_predictions",
               "evaluator_path": EVALUATOR.relative_to(ROOT).as_posix(),
               "evaluator_sha256": hashlib.sha256(EVALUATOR.read_bytes()).hexdigest(),
               "metric_population": "valid_predictions_only_same_ids_for_both_baselines",
               "valid_id_hash_encoding": "UTF-8 of lexicographically sorted IDs joined by LF; no trailing LF",
               "run_count": len(details), "n_total": sum(r["n_total"] for r in ledger),
               "n_valid": sum(r["n_valid"] for r in ledger),
               "n_invalid": sum(r["n_invalid"] for r in ledger),
               "validation": {"unique_ids_labels_and_counts": "passed",
                              "stored_predictions_match_standard_parser": "passed",
                              "confusion_matrices_match_existing_evaluations": "passed",
                              "existing_baselines_match": "passed",
                              "analytic_baseline_checks": "passed",
                              "legacy_undefined_metrics_normalized_to_zero": normalized_zero_metrics},
               "runs": details}
    dump(ROOT / SUMMARY, summary)
    dump(ledger_path, ledger)
    md_path.write_bytes(md.encode("utf-8"))
    manifest_path = ROOT / "copy_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for path in (SUMMARY, "tools/update_run_benchmark_metrics.py"):
        if path not in manifest["generated_files"]:
            manifest["generated_files"].append(path)
    manifest["benchmark_update"] = {"generated_on": "2026-10-21", "summary": SUMMARY,
                                     "script": "tools/update_run_benchmark_metrics.py",
                                     "run_artifacts_modified": False}
    dump(manifest_path, manifest)
    print(json.dumps({"runs": len(details), "n_total": summary["n_total"],
                      "n_valid": summary["n_valid"], "n_invalid": summary["n_invalid"],
                      "legacy_zero_normalizations": len(normalized_zero_metrics)}, indent=2))


if __name__ == "__main__":
    main()
