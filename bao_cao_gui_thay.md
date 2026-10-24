# Phản hồi yêu cầu của thầy

**Cập nhật:** 24/10/2026. Phạm vi: đối soát V1/V2 cũ và cập nhật kết quả các hướng H1, H2, H3.
## Đợt 1 – Đối soát nền thực nghiệm.
### 1. Sửa parser và tính lại nhãn.
*Hàm phân tích phản hồi trong src/evaluator.py hiện gán “Non-vulnerable (0)” thành 1 (chi tiết trong Mục 1.2). Cần làm 3 việc: kiểm tra lỗi này ở mọi parser đang dùng trong cả 2 pipeline; sửa rồi chạy lại parser trên phản hồi thô đã lưu của các run (không cần gọi lại LLM); báo cáo phân phối parse_method, số nhãn thay đổi và số ca lỗi.*

=> Parser của các run Dũng chỉ nhận dòng cuối không rỗng là chính xác `0` hoặc `1`; phản hồi khác giữ invalid. [Audit raw lịch sử 36 run](https://github.com/kazunguyen/GRACE_runs_context/blob/8b62abc7cb9d921bd3ca4ea32378f3aa75188525/provenance/round1_status_audit_2026-10-20/README.md) đối chiếu 90.108 record, không thấy nhãn khác prediction đã lưu. Phân rã 9.307 invalid của bộ raw lịch sử được giữ trong [hồ sơ invalid](phan_tich_invalid_36_run.md); đây không phải số invalid hiện tại sau các lượt recovery.

### 2. Một script đánh giá chung.
*Script này đọc file dự đoán theo từng mẫu và tính toán trên đúng tập mẫu đó: confusion matrix, Accuracy, Precision, Recall, F1, MCC, balanced accuracy, cùng kết quả của 2 đối chứng “luôn đoán vulnerable” và “luôn đoán non-vulnerable”. Mọi bảng kết quả sau này đều được lấy từ script này. Khoảng tin cậy ghép cặp và kiểm định McNemar chỉ cần tính cho những so sánh đã được chọn để xác nhận, không cần tính cho mọi cặp cấu hình.*

=> Các bảng benchmark 36 run của Dũng đã được chuẩn hóa bằng [script cập nhật bảng](https://github.com/kazunguyen/GRACE_runs_context/blob/bf632e82f3fd5901f659691c4187e34979673741/tools/update_run_benchmark_metrics.py), dùng [standard evaluator đã lưu](https://github.com/kazunguyen/GRACE_runs_context/blob/bf632e82f3fd5901f659691c4187e34979673741/provenance/invalid_rerun_context8192_20261021/standard_evaluator.py). Kết quả có confusion matrix, Accuracy/P/R/F1/MCC/BA, coverage/invalid và hai đối chứng hằng trên đúng tập ID hợp lệ của từng run. Hàm evaluate trong pipeline lịch sử vẫn có các bản theo dataset; việc chuẩn hóa bảng này chưa chứng nhận cả hai pipeline Dũng–Hiếu dùng một entrypoint.

Đã ghép 6 arm mixed-model với Grace-baseline và Full trên cùng giao ID có request Qwen/context8192 và prediction hợp lệ: [JSON cohort/metric](https://github.com/kazunguyen/GRACE_runs_context/blob/bf632e82f3fd5901f659691c4187e34979673741/provenance/qwen_subset_paired_comparisons_20261023.json). JSON này chưa có CI/McNemar cho V1/V2 cũ; chỉ bổ sung khi chọn cặp cần xác nhận. Phân tích paired H1 ở phần cải tiến mới là bộ thí nghiệm riêng.

### 3. Bảng quản lý run.
*Mỗi kết quả đã báo cáo là một dòng: run ID, commit, model và nhà cung cấp, split và số mẫu của từng lớp, prompt mode, cấu hình retrieval, đường dẫn file dự đoán và phản hồi thô. Thông tin không còn truy xuất được thì ghi rõ là thiếu.*

=> Đã lập bảng quản lý 36 run context 8.192 byte và bảng riêng cho các run cải tiến: [bảng quản lý run](https://github.com/kazunguyen/GRACE_runs_context/blob/main/bang_quan_ly_run.md), [bảng quản lý run cải tiến](https://github.com/kazunguyen/GRACE_runs_context/blob/main/bang_quan_ly_run_cai_tien.md).

### 4. Chốt điều kiện so sánh.
*Đối chiếu danh sách ID của test set và kho retrieval giữa hai bạn; thống nhất một split và một backbone chung cho các đối chứng sắp tới. Chưa cần chạy lại tất cả các cấu hình.*

=> Đã có contract và cấu hình cho các run Dũng: dataset/split, kho train và backbone được ghi trong manifest. Bộ 36 run đang báo cáo thực tế dùng profile **8192 byte UTF-8**; 6 nhánh có recovery trộn Qwen/Vertex và DeepSeek/FPT, nên bảng Qwen đã lọc theo raw request. Contract 24000 byte cập nhật sau không được gán ngược cho các run 8192. Với đối chứng chung Dũng–Hiếu, cần đối chiếu đủ sáu điều kiện theo hồ sơ của từng bên; cấu hình đã khóa trong một pipeline chưa tự chứng nhận hai pipeline tương đương.

### 5. Sửa hai điểm trong pipeline.
*Tách tham số lấy mẫu train/test trong src/run_pipeline.py; thống kê tần suất nhánh bổ sung ứng viên của contrastive_selector, riêng cho từng dataset.*

=> Trong pipeline reproduced và ablation của em, việc giới hạn số target đánh giá đã được tách khỏi kho retrieval: chạy một phần tập test vẫn giữ toàn bộ tập train làm kho retrieval, theo `keep_full_train_pool_when_running_subset: true` trong contract chung.

## Kết quả khi chạy lại ablations với các cải tiến trước

Các run được đối chiếu trên test của Devign (2.732 mẫu; 1.477 non-vulnerable, 1.255 vulnerable) và ReVeal (2.274 mẫu; 2.044 non-vulnerable, 230 vulnerable). Bảng metric lọc đúng request Vertex AI, model Qwen3-Coder-480B và context 8.192; nhãn chỉ tính trên prediction hợp lệ 0/1, invalid được báo riêng. Kết quả tóm tắt:

| Dataset | Cấu hình | Valid / invalid | Accuracy | Precision | Recall | F1 | MCC | Balanced accuracy |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Devign | GRACE baseline | 2.732 / 0 | 55,01% | 51,91% | 28,21% | 36,55% | 0,0691 | 53,00% |
| Devign | Full cải tiến | 2.732 / 0 | 55,12% | 52,09% | 28,84% | 37,13% | 0,0721 | 53,15% |
| ReVeal | GRACE baseline | 2.224 / 50 | 80,40% | 11,87% | 14,73% | 13,15% | 0,0226 | 51,24% |
| ReVeal | Full cải tiến | 2.274 / 0 | 80,69% | 14,09% | 17,83% | 15,74% | 0,0505 | 52,80% |

Theo metric điểm, cấu hình Full cải tiến tăng F1/MCC so với GRACE baseline lần lượt **+0,58 điểm phần trăm / +0,0030** trên Devign và **+2,59 điểm phần trăm / +0,0279** trên ReVeal. Trên Devign cả hai run có đủ prediction hợp lệ. Trên ReVeal baseline có 50 invalid còn run cải tiến không có invalid, nên kết quả valid-only không cùng số mẫu; cần ghép ID hợp lệ và tính CI/kiểm định ghép cặp trước khi kết luận mức tăng có ý nghĩa. Đây là kết quả ban đầu của tổ hợp cải tiến, chưa tách được đóng góp riêng của từng thành phần.

Metric bao phủ 36 nhánh/run và 83.786 request Qwen đủ điều kiện trên 90.108 target record_id cộng theo nhánh. Các run mix model chỉ tính request Qwen phù hợp; kết quả từng nhánh, confusion matrix, coverage và đường dẫn raw/prompt/prediction có trong [bảng metric 36 run trên GitHub](https://github.com/kazunguyen/GRACE_runs_context/blob/main/metric_vertex_qwen_context8192.md). Bảng quản lý run tương ứng: [bảng quản lý run](https://github.com/kazunguyen/GRACE_runs_context/blob/main/bang_quan_ly_run.md).

## Trình bày các cải tiến mới, và kết quả chạy sơ bộ

Các hướng dưới đây đã có thiết kế và hiện thực ở mức khác nhau; kết quả mới chỉ được xem là bằng chứng hỗ trợ ban đầu. Chỉ xác nhận cải thiện khi có đối chứng cùng backbone, cùng cohort hợp lệ và kiểm định ghép cặp phù hợp.

| Hướng | Thay đổi chính | Kết quả hoặc trạng thái hiện tại |
|---|---|---|
| **H1 — Security Projection** | V1 dùng projection/metric learning; V2 học residual local quanh whitening. | Đã có paired CI/McNemar trên cùng ID. H1-V1: ΔMCC −0,0308 Devign và −0,0075 ReVeal; V2 ReVeal +0,0019, CI chứa 0. V2 còn 9 invalid và chưa có run Devign. Chưa xác nhận lợi ích downstream. |
| **H2 — Guarded Evidence** | Chọn graph context theo thao tác, phụ thuộc dữ liệu và guard. | Full test Vertex DeepSeek: Devign F1 44,55%, MCC 0,0543; ReVeal F1 14,06%, MCC 0,0663. Đã có baseline DeepSeek FPT mới, nhưng khác provider và policy graph/demo; vẫn thiếu prefix control cùng builder/code/demo/budget để cô lập tác dụng evidence. |
| **H3-A — Calibrated Cascade** | Gate tự xử lý mẫu đủ tin cậy, phần còn lại dùng GRACE; benchmark tái dựng với expert H1 đã được chấp nhận. | Devign F1 35,75%, MCC 0,0595; bỏ qua 6/2732 query (0,22%). ReVeal F1 17,11%, MCC 0,0318; không bỏ qua mẫu nào, trùng full reference. Đây là query ratio theo thuật toán, chưa phải tiền/latency tiết kiệm thực đo. |
| **H3-B — Benchmark Ensemble** | Classifier nhiều view, train nested OOF; policy chọn bằng validation OOF rồi khóa trước test. | Đã có đầy đủ test của 16 arm trên mỗi dataset, seed 42. Winner `gate_tuned`, cutoff 0,53 Devign và 0,14 ReVeal: F1/MCC lần lượt 57,45%/0,2961 và 43,62%/0,3705. Winner không gọi expert. Validation Vertex, test FPT có `expert_shift`, `benchmark_comparable=false`; chưa xác nhận kết hợp LLM tốt hơn gate. |

### Đối soát paired cho H1 đã hoàn tất

Đây là so sánh H1 với baseline whitening của chính hướng H1, tách khỏi Grace-baseline/Full V1/V2 cũ ở trên. Δ = H1 trừ baseline, ghép cùng ID hợp lệ; 5000 lần query bootstrap, seed 42, chưa điều chỉnh phụ thuộc project/commit hoặc nhiều phép so sánh.

| Cặp | ID chung | ΔMCC | CI 95% ΔMCC | McNemar p |
|---|---:|---:|---|---:|
| H1-V1 / Devign | 2720 | −0,0308 | [−0,0520; −0,0105] | 0,0039 |
| H1-V1 / ReVeal | 2205 | −0,0075 | [−0,0235; 0,0078] | 0,4966 |
| H1-V2 / ReVeal | 2265 | +0,0019 | [−0,0148; 0,0186] | 0,2031 |

Nguồn: [audit metric/CI/McNemar](https://github.com/kazunguyen/GRACE_runs_context/blob/2fca43f765ba14e235352a6c8438154b48d6b04d/audits/h_controls_20261024/audit_results.json), [bản đối soát bốn hướng H](https://github.com/kazunguyen/GRACE_runs_context/blob/2fca43f765ba14e235352a6c8438154b48d6b04d/bao_cao_doi_soat_4_huong_H_20261024.md). Trên các cặp này, H1-V1 Devign giảm MCC; hai cặp ReVeal chưa xác nhận lợi ích.

### Giới hạn H3-B cần ghi rõ

Benchmark đã có đủ năm nhánh và các biến thể: gate-only, benefit/confidence router, post-selector, stacking LR/MLP và full GRACE. Không đổi winner theo điểm test. Validation/test khác endpoint/provider và thinking validation chưa ghi; đây là giới hạn của các arm dùng expert. Winner gate-only không dùng expert để tạo prediction test.

[Đối soát protocol H3-B](audits/h3b_protocol_review_20261024.json) xác nhận các fold train outer/inner và meta tách code hash, nhưng test vẫn có **5 Devign và 63 ReVeal** trùng code với dữ liệu học/chọn tham số. Cần chấm bổ sung cùng mask không trùng (2727/2211 mẫu), cùng model/cutoff đã khóa; chưa thực hiện phân tích này. Test đã được xem trong quá trình phát triển, nên vẫn cần holdout mới cho kết luận khái quát.

Báo cáo phương pháp và các bảng benchmark: [báo cáo cải tiến](https://github.com/kazunguyen/GRACE_runs_context/blob/62d7ed077eb022591f2572b57660784453e38063/bao-cao-cai-tien.md). Artifact và metric paired có trong audit đã dẫn; bảng metric request Qwen lịch sử: [metric cải tiến](metric_cai_tien_vertex_qwen_context8192.md).

**Đề xuất của Dũng:** tiếp tục hoàn thiện các cải tiến H1, H2, H3 theo yêu cầu đối chứng của thầy. Ưu tiên phần còn thiếu của từng hướng, phân tích cả kết quả âm, ghi rõ chi phí và phạm vi xác nhận. Kết quả Full V1/V2 cũ cao hơn baseline về metric điểm; các hướng H hiện chưa đủ bằng chứng xác nhận hiệu quả tổng quát, và H3-B hiện chọn classifier độc lập làm winner.
