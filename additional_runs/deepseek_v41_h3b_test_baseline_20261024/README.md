# H3-B prompt cohorts — GRACE test baseline DeepSeek V4.1

**ĐÂY LÀ TEST BASELINE GRACE GỐC, CHƯA PHẢI METRIC CUỐI CÙNG CỦA H3-B.** Toàn bộ mẫu của hai official test split được đưa vào arm baseline_whitening, không áp dụng classifier/gate/router/post-selector/stacking của H3-B.

**Lượt test baseline được chọn hiện tại: abbf356612344183, ngày 24/10/2026.** Kết quả này thay thế việc tái sử dụng baseline H1/Qwen cho hai dòng H3-B/test trong các bảng hiện hành. Các lượt H1, DeepSeek V4 cũ và test24k được giữ làm lịch sử.

## Cấu hình và kết quả

- Model thực tế trong manifest: DeepSeek-V4.1-Flash.
- Provider: OpenAI-compatible API qua FPT, endpoint https://token-api.fpt.ai/v1/chat/completions; không phải Vertex.
- Temperature 0; seed 42; max_tokens 256; thinking=False; parser exact_last_line_binary_v1.
- Budget prompt: tối đa 8192 UTF-8 bytes.
- Run ID được hash theo identity request chung; hai dataset có cùng ID nhưng artifact ở thư mục dataset riêng.
- Manifest không ghi tên người thực hiện inference test; không suy diễn người chạy từ đường dẫn máy. Validation do Hiếu chạy trên Kaggle/Vertex vẫn là lượt riêng.

| Dataset/split | N0/N1 | Valid/invalid | TN/FP/FN/TP | Accuracy (%) | P (%) | R (%) | F1 (%) | MCC | Balanced accuracy (%) |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|
| Devign/test | 1477/1255 | 2732/0 | 1247/230/995/260 | 55.16 | 53.06 | 20.72 | 29.80 | 0.0668 | 52.57 |
| ReVeal/test | 2044/230 | 2274/0 | 1907/137/195/35 | 85.40 | 20.35 | 15.22 | 17.41 | 0.0971 | 54.26 |

Nguồn đầy đủ và số thập phân gốc: [summary](baseline_comparison_report.json), [evaluation Devign](devign/abbf356612344183/evaluation.json), [evaluation ReVeal](reveal/abbf356612344183/evaluation.json).

## Artifact

- [Notebook đã thực thi](baseline_whitening_test_inference.ipynb), runner/parser, requirements, request_config và bundle_manifest là snapshot từ package inference.
- [Devign](devign/abbf356612344183/) và [ReVeal](reveal/abbf356612344183/) giữ nguyên byte các file predictions.jsonl, raw_responses.jsonl, run_manifest.json, export_manifest.json.
- Mỗi thư mục dataset/run có request_checkpoints.zip chứa nguyên các checkpoint JSON, thay vì đưa hơn 5000 file lẻ vào Git. Nội dung từng checkpoint đã được đối chiếu với raw response tổng hợp.
- [Prompt Devign](inputs/devign/prompts.jsonl.gz) và [prompt ReVeal](inputs/reveal/prompts.jsonl.gz) giữ nguyên gzip của package inference. Cohort xuất phát từ H3-B run 1c092d22f44923fc và ee956918e7b19785, đúng profile 8192; không lấy ReVeal run test24k cũ.
- evaluated_predictions.jsonl bổ sung gold vào bản prediction riêng để đánh giá sau inference. File predictions.jsonl gốc không bị sửa; gold không có trong input inference.
- [Provenance](provenance/import_provenance.json) ghi SHA-256 và nguồn. Lượt smoke thất bại bc9b31e4c912a3e0 không được dùng tính baseline.

Nguồn máy: D:/JUNIOR/LabThayTho/SHARE_BASELINE_WHITENING_DEVIGN_REVEAL_TEST_CONTEXT8192_20261024/.

## Kiểm tra và tính lại metric

Đã kiểm tra 5006/5006 ID và thứ tự khớp canonical test, code hash/prompt hash khớp, prompt không vượt budget, raw response parse đúng prediction và checkpoint khớp raw. Gold lấy từ canonical test của GRACE-H3-BenchmarkEnsemble; file evaluation ghi checksum của dataset gốc.

Để tính lại metric từ evaluated_predictions và kiểm tra evaluation lưu trữ:

    python recompute_metrics.py

Validation đang được chọn là Vertex DeepSeek V4.1 do Hiếu chạy, trong khi test này dùng FPT và thinking=False. Bảng này chỉ ghi baseline theo từng dataset/split; không ghép thành một kết luận ensemble cùng cấu hình hoặc chọn lại winner H3-B theo test.

Không đưa .env/API key vào archive. Không gọi API hoặc train model khi nhập và tính metric kết quả này.
