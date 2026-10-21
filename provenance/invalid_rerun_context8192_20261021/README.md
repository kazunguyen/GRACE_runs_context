# Rerun invalid trên sáu nhánh — context 8192

Cập nhật ngày21/10/2026. Notebook retry đúng 6.322 target originally invalid; 7.780 response valid cũ được giữ nguyên. Đã kiểm tra toàn bộ14.102 mẫu trong sáu nhánh: ID/prediction khớp raw, prompt hash đúng và không quá8.192 UTF-8 byte.

**Kết quả dùng hai backbone**: giữ valid cũ từ Qwen3-Coder-480B/Vertex, gọi lại bằng DeepSeek-V4-Flash/FPT. Không nhận đây là benchmark một backbone.

| Run | Invalid trước | Invalid sau | Valid sau |
|---|---:|---:|---:|
| Devign/Ablations/Plus-C8-mmr-selection/test_v2 | 1251 | 0 | 2732 |
| Reveal/Ablations/No-C2-stratified-demo-selection/test_v2 | 1013 | 0 | 2274 |
| Reveal/Ablations/No-C3-GEPA-prompt-optimization/test_v2 | 930 | 1 | 2273 |
| Reveal/Ablations/No-C5-graph-verbalization/test_v2 | 1036 | 1 | 2273 |
| Reveal/Ablations/Plus-C1-tri-signal-retrieval/test_v2 | 934 | 0 | 2274 |
| Reveal/Ablations/Plus-C7-security-cot/test_v2 | 1158 | 0 | 2274 |

Hai ca còn lại là HTTP429: giới hạn100 requests/phút ở FPT, đã hết5 attempts. Không gọi LLM thêm trong lượt đồng bộ này.

Các link artifact cũ vẫn đúng do giữ cấu trúc runs/. repair_manifest.json mô tả phần inference thay thế; run_manifest.json/freeze.json vẫn là provenance preparation lịch sử. standard_evaluator.py là logic đã dùng để tính lại toàn bộ cohort trong mỗi nhánh, gồm hai đối chứng. Notebook ở đây bỏ output hiển thị, giữ nguyên code đã chạy.

summary.json và generation_spec.json được copy từ checkpoint rerun. sync_verification.json ghi hash giữa C và SHARE, model counts và hai ID còn invalid. Raw đầy đủ từng attempt vẫn nằm ở work directory local được repair manifest dẫn tới; gói này chia sẻ raw cuối và metadata finish reason/usage, không bao gồm toàn bộ attempt log.
