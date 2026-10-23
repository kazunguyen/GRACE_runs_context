# Kaggle Vertex DeepSeek V4.1 — 2026-10-23

Nhờ Hiếu chạy full H2 Guarded v3 trên Kaggle bằng Vertex AI
`deepseek-ai/deepseek-v4.1-flash-maas` (`global`), prompt limit 8.192 UTF-8
bytes, temperature 0, seed 42, max_tokens 256.

- Devign: 2.732/2.732 request hợp lệ.
- ReVeal: 2.274/2.274 request hợp lệ.
- Đã đối chiếu raw request với prompt v3 theo query ID: đủ 5.006/5.006 prompt
  và code hash khớp.
- Mỗi dataset có `predictions.jsonl`, `raw_responses.jsonl`, `evaluation.json`
  và `run_manifest.json`; `baseline_comparison_report.json` ở thư mục gốc.
- ZIP đầu vào không chứa notebook Kaggle đã thực thi; raw response lưu đầy đủ
  request body và response để kiểm tra.

Đây là kết quả DeepSeek, không phải request Vertex Qwen; không cộng vào metric
Qwen trong bảng `metric_cai_tien_vertex_qwen_context8192.md`.
