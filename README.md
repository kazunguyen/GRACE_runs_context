# Dữ liệu 36 run GRACE — context 8.192 byte (có cập nhật rerun)

Mở **bang_quan_ly_run.md** để xem bảng và liên kết tương đối tới từng artifact.
Giữ nguyên cấu trúc thư mục khi tải từ Google Drive; nếu Drive preview không mở được link JSONL, tải folder về máy và mở bằng trình soạn thảo.

- 4 run Reproduced (Code-Based/Paper-Based × Devign/ReVeal), thư mục test.
- 32 run Ablation_V2 (16 arm × 2 dataset), thư mục test_v2.
- Tổng 90.108 mẫu prompt/response. Không gồm test_v3, selective 24.000 byte, H1/H2/H3.
- Mỗi run có prompts/prompts.jsonl, inference/raw_responses.jsonl, evaluation/predictions.jsonl, run_manifest.json, freeze.json, evaluation/evaluation.json và retrieval/retrievals.jsonl.
- Trường prompt chứa nguyên văn đầu vào sau cắt để gửi model; raw_response chứa văn bản trả lời, có cả dòng rỗng khi request thất bại. Đây không phải bản đầy đủ JSON provider hoặc log từng retry.

Xem kiem_tra_raw_prompt_limits.md về context/node/edge. Tất cả prompt <=8.192 byte, <=40 khai báo node và <=80 khai báo cạnh; 382 prompt nhắc tới hơn 40 ID đầu mút cạnh. Không đồng nhất giới hạn khai báo node với số đỉnh duy nhất của graph.

Artifact gốc được copy nguyên byte; sáu nhánh sau rerun đã thay raw/prediction/evaluation và bổ sung repair manifest. manifest/freeze có thể chứa đường dẫn tuyệt đối của máy nguồn. Không chỉnh chúng để giữ bằng chứng gốc. Bảng Markdown/JSON ở thư mục gốc dùng đường dẫn tương đối; provenance chứa bảng gốc và tài liệu đối soát. Chưa phục hồi snapshot contract lịch sử đúng hash; không đưa contract 24.000 byte hiện tại vào thay thế.

copy_manifest.json ghi nguồn, kích thước và SHA-256 của artifact hiện tại. Sáu nhánh đã được notebook cập nhật đồng thời ở nguồn C và SHARE; lịch sử trước rerun vẫn nằm trong Git. Không kèm API key, .env, model weights hay cache nặng. Đây là bộ artifact để xem và đối soát, không phải môi trường tái chạy toàn pipeline.

## H3 bổ sung — không thuộc bộ 36 run context8192

- [H3: validation 8192 / test 24000](additional_runs/H3-BenchmarkEnsemble/validation8192_test24000_20261021/README.md). Snapshot trộn model, giữ đúng context thực tế; không gộp vào thống kê 36 run lịch sử.

## Cập nhật rerun invalid ngày 21/10/2026

Sáu nhánh có invalid trên40% đã được retry 6.322 mẫu bằng DeepSeek-V4-Flash/FPT; còn2 invalid. Prompt giữ nguyên8.192 byte, valid cũ giữ nguyên. Kết quả sáu nhánh là mixed backbone Qwen/Vertex + DeepSeek/FPT. [Bảng run cập nhật](bang_quan_ly_run.md) · [Báo cáo rerun](provenance/invalid_rerun_context8192_20261021/README.md). Link prediction/raw/prompt cũ giữ nguyên; mỗi nhánh có thêm repair_manifest.json.


## Run cải tiến H1 / H2 / H3

Bảng riêng cho các cải tiến, không cộng vào 36 run gốc: [bảng quản lý run cải tiến](bang_quan_ly_run_cai_tien.md) · [JSON](bang_quan_ly_run_cai_tien.json).

Artifact snapshot H1 và hai bản H3: [improvements_20261021](additional_runs/improvements_20261021/). H2 đang chạy nên chưa snapshot kết quả.
