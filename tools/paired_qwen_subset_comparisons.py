"""Re-score mixed-provider ablations and both controls on one shared cohort.

The Qwen cohort comes from raw requests whose publisher model ID is Qwen and
whose recorded prompt context limit is 8192. Each pair is then scored only on
IDs where the arm, GRACE baseline, and full-improvement predictions are all
valid binary labels, so all three scores and both trivial controls share one
exact metric population.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
METRIC_PATH = ROOT / "metric_vertex_qwen_context8192.md"
OUT_PATH = ROOT / "provenance" / "qwen_subset_paired_comparisons_20261023.json"
QWEN_MODEL = "publishers/qwen/models/qwen3-coder-480b-a35b-instruct-maas"
MIX_RUNS = [
    "Devign/Ablations/Plus-C8-mmr-selection/test_v2",
    "Reveal/Ablations/No-C2-stratified-demo-selection/test_v2",
    "Reveal/Ablations/No-C3-GEPA-prompt-optimization/test_v2",
    "Reveal/Ablations/No-C5-graph-verbalization/test_v2",
    "Reveal/Ablations/Plus-C1-tri-signal-retrieval/test_v2",
    "Reveal/Ablations/Plus-C7-security-cot/test_v2",
]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def prediction_map(run_path: str) -> dict[str, dict[str, Any]]:
    path = ROOT / "runs" / run_path / "evaluation" / "predictions.jsonl"
    rows = read_jsonl(path)
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        rid = str(row["record_id"])
        if rid in result:
            raise ValueError(f"Duplicate prediction record_id in {path}: {rid}")
        result[rid] = row
    return result


def valid_label(row: dict[str, Any] | None) -> int | None:
    if row is None:
        return None
    value = row.get("prediction")
    return value if type(value) is int and value in (0, 1) else None


def scores(rows: list[tuple[int, int]]) -> dict[str, Any]:
    tn = sum(y == 0 and p == 0 for y, p in rows)
    fp = sum(y == 0 and p == 1 for y, p in rows)
    fn = sum(y == 1 and p == 0 for y, p in rows)
    tp = sum(y == 1 and p == 1 for y, p in rows)
    n = len(rows)
    div = lambda a, b: a / b if b else None
    precision = div(tp, tp + fp)
    recall = div(tp, tp + fn)
    specificity = div(tn, tn + fp)
    f1 = div(2 * tp, 2 * tp + fp + fn)
    if f1 is None and n:
        f1 = 0.0
    if precision is None and n:
        precision = 0.0
    denominator = ((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)) ** 0.5
    mcc = div(tp * tn - fp * fn, denominator)
    if mcc is None and n:
        mcc = 0.0
    balanced_accuracy = (
        (recall + specificity) / 2
        if recall is not None and specificity is not None
        else None
    )
    return {
        "n": n,
        "confusion_matrix": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
        "accuracy": div(tp + tn, n),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "mcc": mcc,
        "balanced_accuracy": balanced_accuracy,
    }


def pct(value: float | None) -> str:
    return "N/A" if value is None else f"{100 * value:.2f}"


def fmt(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.4f}"


def update_run_population_columns(metric_text: str) -> str:
    """Set table denominators to the all-provider target population per run."""
    output: list[str] = []
    branch_count = 0
    total_qwen_calls = 0
    total_qwen_ids = 0
    total_all_model_ids = 0
    for line in metric_text.splitlines():
        if line.startswith("| [") and " / test |" in line:
            fields = line.split("|")
            raw_match = re.search(r"\[raw\]\(<([^>]+)>\)", line)
            if raw_match:
                raw_path = ROOT / raw_match.group(1)
                raw_rows = read_jsonl(raw_path)
                all_ids = {
                    str(row["record_id"])
                    for row in raw_rows
                    if row.get("record_id") is not None and row.get("model")
                }
                qwen_rows = [
                    row for row in raw_rows
                    if row.get("model") == QWEN_MODEL
                    and row.get("prompt_truncation", {}).get("context_limit") == 8192
                    and row.get("record_id") is not None
                ]
                qwen_ids = {str(row["record_id"]) for row in qwen_rows}
                call_parts = [part.strip() for part in fields[4].split("/")]
                if len(call_parts) == 2 and call_parts[0].isdigit():
                    total_qwen_calls += int(call_parts[0])
                    fields[4] = f" {call_parts[0]} / {len(all_ids)} "
                    line = "|".join(fields)
                    branch_count += 1
                    total_qwen_ids += len(qwen_ids)
                    total_all_model_ids += len(all_ids)
        if line.startswith("| Run / branch |"):
            line = line.replace(
                "Qwen calls eligible / unique samples",
                "Qwen calls eligible / unique target samples (all models)",
            ).replace(
                "Valid / invalid (unique samples)",
                "Valid / invalid (unique Qwen samples)",
            ).replace(
                "N0 / N1 thật",
                "N0 / N1 thật (Qwen samples)",
            ).replace(
                "Coverage (%)",
                "Coverage among Qwen samples (%)",
            )
        if line.startswith("Nguồn nhánh:"):
            line = (
                "Nguồn nhánh: [bang_quan_ly_run.md](<bang_quan_ly_run.md>). Mỗi dòng là một run/nhánh trong bảng nguồn. `Qwen calls eligible` là số request vật lý đủ điều kiện (Vertex Qwen, context limit 8192); `unique target samples (all models)` là số `record_id` duy nhất được gọi bởi bất kỳ model nào trong run. Với arm mix, mẫu số gồm cả các ID được gọi bằng Qwen và model khác. Các cột valid/invalid, N0/N1, confusion matrix, metric và coverage vẫn chỉ mô tả phần Qwen đủ điều kiện; coverage = valid / số ID Qwen duy nhất, không phải / tổng target của mọi model."
            )
        if line.startswith("Nhãn thật lấy từ sealed_label"):
            line = line.replace(
                "N0/N1 tính trên toàn bộ request Qwen đủ điều kiện. Coverage = valid / unique eligible requests.",
                "N0/N1 tính trên các ID Qwen đủ điều kiện. Coverage = valid / số ID Qwen duy nhất đủ điều kiện.",
            )
        if line.startswith("Tổng: 36 nhánh;"):
            line = (
                f"Tổng: {branch_count} nhánh; {total_qwen_calls:,} request Qwen đủ điều kiện trên {total_qwen_ids:,} unique Qwen record_id (cộng theo nhánh); "
                f"{total_all_model_ids:,} unique target record_id được gọi bởi mọi model (cộng theo nhánh; trùng ID giữa các nhánh được tính riêng)."
            )
        output.append(line)
    return "\n".join(output) + "\n"


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    result: list[dict[str, Any]] = []
    for run_path in MIX_RUNS:
        raw_path = ROOT / "runs" / run_path / "inference" / "raw_responses.jsonl"
        qwen_ids = {
            str(row["record_id"])
            for row in read_jsonl(raw_path)
            if row.get("model") == QWEN_MODEL
            and row.get("prompt_truncation", {}).get("context_limit") == 8192
            and row.get("record_id") is not None
        }
        if not qwen_ids:
            raise ValueError(f"No eligible Qwen IDs found in {raw_path}")

        dataset = run_path.split("/", 1)[0].lower()
        arm = prediction_map(run_path)
        grace_path = f"{dataset.title()}/Ablations/Grace-baseline/test_v2"
        full_path = f"{dataset.title()}/Ablations/Full-cai-tien/test_v2"
        grace = prediction_map(grace_path)
        full = prediction_map(full_path)
        common_ids = sorted(
            rid
            for rid in qwen_ids
            if valid_label(arm.get(rid)) is not None
            and valid_label(grace.get(rid)) is not None
            and valid_label(full.get(rid)) is not None
        )
        if not common_ids:
            raise ValueError(f"No common valid IDs across all three runs for {run_path}")

        labels = [int(arm[rid]["sealed_label"]) for rid in common_ids]
        if any(int(grace[rid]["sealed_label"]) != int(arm[rid]["sealed_label"]) for rid in common_ids):
            raise ValueError(f"Conflicting GRACE labels in {run_path}")
        if any(int(full[rid]["sealed_label"]) != int(arm[rid]["sealed_label"]) for rid in common_ids):
            raise ValueError(f"Conflicting Full-improvement labels in {run_path}")
        if not set(labels) <= {0, 1}:
            raise ValueError(f"Unexpected labels in {run_path}")

        arm_scores = scores([(int(arm[rid]["sealed_label"]), valid_label(arm[rid])) for rid in common_ids])
        grace_scores = scores([(int(grace[rid]["sealed_label"]), valid_label(grace[rid])) for rid in common_ids])
        full_scores = scores([(int(full[rid]["sealed_label"]), valid_label(full[rid])) for rid in common_ids])
        n0 = sum(label == 0 for label in labels)
        n1 = sum(label == 1 for label in labels)
        all_vulnerable = scores([(label, 1) for label in labels])
        all_non_vulnerable = scores([(label, 0) for label in labels])
        result.append({
            "dataset": dataset,
            "arm_run": run_path,
            "qwen_eligible_unique_ids": len(qwen_ids),
            "qwen_eligible_record_ids": sorted(qwen_ids),
            "common_valid_ids": len(common_ids),
            "common_valid_record_ids": common_ids,
            "excluded_from_common_cohort": len(qwen_ids) - len(common_ids),
            "invalid_or_missing_in_qwen_cohort": {
                "arm": sum(valid_label(arm.get(rid)) is None for rid in qwen_ids),
                "grace_baseline": sum(valid_label(grace.get(rid)) is None for rid in qwen_ids),
                "full_improvement": sum(valid_label(full.get(rid)) is None for rid in qwen_ids),
            },
            "n0_n1": {"n0": n0, "n1": n1},
            "grace_baseline": grace_scores,
            "full_improvement": full_scores,
            "arm": arm_scores,
            "always_vulnerable": all_vulnerable,
            "always_non_vulnerable": all_non_vulnerable,
        })

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "## Bảng đối chứng những arm đang dùng mix model",
        "",
        "Do backbone đang dùng bị nhà cung cấp retire đột ngột, một số arm mix Qwen và DeepSeek mới chạy được một phần test. Đồng thời, nhóm đang chuyển context limit lên 24.000 byte nhưng lượt đối chứng này chưa hoàn tất. Vì vậy, phần dưới chỉ lấy những mẫu có raw request thực sự dùng Qwen và `context_limit = 8192`, rồi ghép với prediction đã lưu của cùng arm, Grace baseline và Full cải tiến trên đúng `record_id`.",
        "",
        "Để so sánh công bằng, metric của cả ba cấu hình và hai đối chứng predict-all được tính trên cùng giao các ID mà cả arm, Grace baseline và Full cải tiến đều có prediction hợp lệ 0/1. N0/N1 là phân phối nhãn thật trên cohort chung; `Số mẫu / tổng số Qwen IDs` cho biết số mẫu dùng tính metric trên tổng ID Qwen đủ điều kiện. Nếu Grace baseline có invalid hoặc thiếu prediction, ID đó bị loại khỏi cohort chung cho cả ba cấu hình; số invalid/missing của từng cấu hình được ghi dưới mỗi arm. Ma trận nhầm lẫn theo thứ tự TN/FP/FN/TP; các metric phần trăm gồm Accuracy, Precision, Recall, F1 và Balanced accuracy; MCC là hệ số.",
        "",
    ]
    configurations = [
        ("Arm ablation", "arm"),
        ("Full cải tiến", "full_improvement"),
        ("GRACE gốc", "grace_baseline"),
        ("Chỉ dự đoán vulnerable", "always_vulnerable"),
        ("Chỉ dự đoán non-vulnerable", "always_non_vulnerable"),
    ]
    for index, row in enumerate(result, start=1):
        lines.extend([
            f"### Arm {index}: `{row['arm_run']}`",
            "",
            f"Dataset/split: **{row['dataset']} / test**. Cohort Qwen đủ điều kiện: **{row['qwen_eligible_unique_ids']} ID**; cohort chung hợp lệ: **{row['common_valid_ids']} ID** (N0/N1 = **{row['n0_n1']['n0']}/{row['n0_n1']['n1']}**). Loại khỏi cohort chung: **{row['excluded_from_common_cohort']} ID**. Invalid/thiếu prediction trong cohort Qwen (arm / Grace baseline / Full cải tiến): **{row['invalid_or_missing_in_qwen_cohort']['arm']} / {row['invalid_or_missing_in_qwen_cohort']['grace_baseline']} / {row['invalid_or_missing_in_qwen_cohort']['full_improvement']}**.",
            "",
            "| Cấu hình | Số mẫu / tổng số Qwen IDs | TN / FP / FN / TP | Accuracy (%) | Precision (%) | Recall (%) | F1 (%) | MCC | Balanced accuracy (%) |",
            "|---|---:|---|---:|---:|---:|---:|---:|---:|",
        ])
        for label, key in configurations:
            metric = row[key]
            cm = metric["confusion_matrix"]
            cm_text = " / ".join(str(cm[k]) for k in ("tn", "fp", "fn", "tp"))
            lines.append(
                f"| {label} | {row['common_valid_ids']} / {row['qwen_eligible_unique_ids']} | {cm_text} | {pct(metric['accuracy'])} | {pct(metric['precision'])} | {pct(metric['recall'])} | {pct(metric['f1'])} | {fmt(metric['mcc'])} | {pct(metric['balanced_accuracy'])} |"
            )
        lines.append("")
    lines.append(
        f"Danh sách `record_id` trong từng cohort và metric chưa làm tròn: [JSON đối chứng ghép cohort](<{OUT_PATH.relative_to(ROOT).as_posix()}>). Tái tạo bằng `python tools/paired_qwen_subset_comparisons.py`."
    )

    metric_text = update_run_population_columns(METRIC_PATH.read_text(encoding="utf-8"))
    markers = [
        "## Đối chứng predict-all cho các nhánh mix",
        "## So sánh arm mixed-model",
        "## Bảng đối chứng những arm đang dùng mix model",
    ]
    existing = [metric_text.index(marker) for marker in markers if marker in metric_text]
    if existing:
        metric_text = metric_text[:min(existing)].rstrip() + "\n\n"
    metric_text = metric_text.rstrip() + "\n\n" + "\n".join(lines) + "\n"
    METRIC_PATH.write_text(metric_text, encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
