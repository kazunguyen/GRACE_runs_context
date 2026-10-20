# Kiểm tra yêu cầu đợt 1 — 20/10/2026

**Kết luận: chưa hoàn tất cả năm yêu cầu.** Đã có nền kiểm soát cho run mới, nhưng còn thiếu đầu ra báo cáo và đối soát giữa hai pipeline.

Đối chiếu nội dung `GRACE_phanhoibaocaoDungHieu.docx`, contract tại `STANDARD_FOR_ALL_INFERENCES/evaluation_contract.yaml`, code Ablation_V2 và bản GRACE của Hiếu trên ổ D. Chỉ đọc artifact, không gọi LLM hay sửa kết quả cũ. Script kiểm tra: `../audit_round1_status.py`; bằng chứng theo run: `artifact_checks.json`.

## Phạm vi đã kiểm tra trực tiếp

- 4 run reproduce ở `Reproduced-{Code,Paper}-Based/{devign,reveal}/test`.
- 32 run ablation ở `{Devign,Reveal}/Ablations/*/test_v2`, tương ứng bảng `ket-qua-so-sanh.md`.
- Không gộp ablation lịch sử trong `test/` hoặc các lần chạy mới `test_v3/` vào 36 run này.
- 90.108 dòng dự đoán; đối chiếu raw text với file phản hồi thô theo ID, rồi tính lại nhãn bằng quy tắc dòng cuối chính xác 0/1.

## 1. Parser và tính lại nhãn: một phần

Parser dùng cho Ablation_V2 ở hai file `Devign/Ablations/Full-cai-tien/full_cai_tien_pipeline.py` và `Reveal/Ablations/Full-cai-tien/full_cai_tien_pipeline.py` chỉ nhận dòng cuối 0/1; không có lỗi substring `non-vulnerable` thành vulnerable. Reproduced-Paper-Based dùng phần triển khai chung ở Reproduced-Code-Based, phần này gọi evaluator theo dataset. Hai parser dataset có quy tắc tương đương contract, nhưng là bản code riêng, không import trực tiếp contract parser.

Kiểm tra lại 36 run cho kết quả:

| Phương thức tính lại | Số dòng |
|---|---:|
| exact_last_line_binary | 80.801 |
| empty_response | 9.305 |
| last_line_not_exact_binary | 2 |
| Tổng invalid | 9.307 |
| Nhãn khác dự đoán đã lưu | 0 |
| Raw text khác giữa prediction và raw-response cùng ID | 0 |

Đây là **kiểm tra tính nhất quán với parser strict hiện tại**, không phải số nhãn đã thay đổi do sửa parser lỗi trong quá khứ. Các prediction của 36 run không lưu trường `parse_method`; bảng trên được bổ sung bởi audit này. Chưa có bản tổng hợp trước/sau parser lỗi cho mọi run đã từng báo cáo của cả hai bạn.

Bản `D:/JUNIOR/LabThayTho/HuuHieu03/GRACE/src/evaluator.py` đã sửa các ví dụ `Non-vulnerable`, `Non-vulnerable (0)`, `Label: Non-vulnerable (0)` thành 0; phản hồi rỗng trả None. Đã kiểm tra hàm tách từ AST để không khởi tạo model. Tuy nhiên câu `There is 1 loop in this function.` vẫn ra 1 qua `Heuristic standalone '1'`. Vì vậy parser này chưa đáp ứng trọn yêu cầu không đoán nhãn từ một chữ số xuất hiện trong câu. Có `tests/test_parser_audit.py`, nhưng kiểm tra này không chạy toàn bộ test suite hoặc model.

Audit cũ `Grace-with-filters-v2/[src]/01_contract_audit/output/dung_teacher_round1_audit.json` có kiểm tra raw Devign staged và Reveal external (27.153 và 2.238 dòng). Đây là artifact khác, dùng compatibility parser cho verdict chữ. CSV lịch sử không có ID/raw phải ghi rõ không thể phục hồi; không dùng số liệu này thay cho kiểm tra 36 run mới.

## 2. Một script đánh giá chung: một phần

Evaluator đang sinh `evaluation/evaluation.json` của Ablation_V2 tính confusion matrix, Accuracy, Precision, Recall, F1, MCC và balanced accuracy trên valid predictions; lưu tổng invalid riêng. Tuy nhiên **0/36 file evaluation có cả hai baseline tầm thường**. Code tính metric còn được sao chép theo Devign/Reveal, không phải một script duy nhất đọc prediction cho mọi pipeline.

Có evaluator đầy đủ hơn ở `Grace-with-filters-v2/[src]/06_evaluation/code/evaluate_predictions.py` với hai baseline, paired bootstrap và McNemar tùy chọn. Nhưng CLI đó đọc raw responses và sealed labels, không phải đầu vào prediction trực tiếp; các bảng Ablation_V2 hiện lấy từ evaluator riêng. Có script ở nơi khác chưa đủ chứng minh mọi bảng đều dùng chung nó.

Phía Hiếu có `src/common_evaluator.py` nhận JSON/JSONL/CSV và hỗ trợ reparse, phân phối parse_method, metric trước/sau. Chưa thấy hai baseline được thực thi trong script này; việc đã viết tool không chứng minh đã tạo đủ đầu ra audit cho từng run.

`ket-qua-so-sanh.md` đã công khai N hợp lệ và Invalid, nhưng Δ MCC giữa hai arm có invalid khác nhau vẫn trừ metric trên hai tập valid khác nhau. Trước khi dùng để xác nhận cải tiến phải chốt cùng tập ID hợp lệ và công bố coverage. Chỉ cần CI/McNemar cho cặp đã chọn xác nhận; không bắt buộc mọi cặp.

## 3. Bảng quản lý run: một phần

Có `run_manifest.json`, `freeze.json`, prediction và raw-response của 36 run, đủ làm nền dựng bảng. Nhưng chưa thấy bảng thống nhất một dòng cho từng kết quả trong báo cáo hiện tại, chứa đủ commit, model/provider, split, số mẫu từng lớp, prompt mode, retrieval và đường dẫn artifact; bảng metric hiện tại không thay thế bảng này.

Audit cũ có code sinh `dung_legacy_run_ledger.csv` và tài liệu có `run_ledger_template.csv`. Không được coi template hay ledger legacy là ledger đầy đủ cho 36 run mới. Thông tin thiếu phải ghi missing, không suy đoán commit/model của run từ code hiện tại. File `artifact_checks.json` của audit này là bằng chứng kiểm tra, chưa phải ledger hoàn chỉnh theo yêu cầu của thầy.

Cụ thể 32 manifest ablation không có trường commit trực tiếp; 4 manifest reproduce có commit. Đây là thiếu tại manifest, chưa khẳng định commit không thể phục hồi từ provenance khác.

## 4. Điều kiện so sánh: nội bộ đã có bằng chứng; giữa hai bạn chưa xác nhận

- 36/36 run có tập prediction ID trùng baseline Code-Based tương ứng, không có ID trùng lặp; tập raw-response ID cũng khớp prediction.
- Devign: 2.732 target, 1.477 nhãn 0 và 1.255 nhãn 1. Reveal: 2.274 target, 2.044 nhãn 0 và 230 nhãn 1.
- Trong mỗi dataset, 36 manifest chia sẻ một `train_identity` tương ứng; đây là bằng chứng từ manifest, audit chưa đọc lại toàn bộ nội dung kho train để xác thực hash.
- Contract hiện tại đã chốt split theo revision và backbone Qwen3-Coder-480B trên Vertex AI.
- Contract ở repo Hiếu cũng khai báo cùng backbone/provider, nhưng Devign/ReVeal vẫn dùng `@main`, parser trỏ hàm legacy và context/graph caps khác contract chuẩn. Khai báo model giống nhau chưa chứng minh các run đã dùng đúng điều kiện chung.
- Chưa thấy artifact đối chiếu danh sách test ID và retrieval ID giữa Dũng và Hiếu; chưa xác nhận pipeline Hiếu thực thi cùng backbone/split.

Contract hiện tại là revision context24000bytes_20261018. Toàn bộ 90.108 raw row được kiểm tra ghi `context_limit: 8192`; 36 manifest có cùng contract hash cũ, khác hash contract hiện tại. Khi viết báo cáo phải ghi điều kiện đã dùng ở lần chạy, không gán contract hiện tại cho toàn bộ kết quả cũ. Việc đổi contract không tự động bắt buộc chạy lại mọi cấu hình để hoàn tất đợt 1.

## 5. Hai sửa đổi pipeline: xong tách tham số; chưa thấy thống kê nhánh bổ sung

`D:/JUNIOR/LabThayTho/HuuHieu03/GRACE/src/run_pipeline.py` đã có `train_sample_ratio` và `test_sample_ratio` riêng; nhánh lấy dữ liệu gọi loader với hai tỷ lệ riêng. Ablation_V2 cũng tách max_targets khỏi kho train theo contract.

Lưu ý tương thích ngược: nếu truyền `--sample_ratio` cũ thì code vẫn gán cùng tỷ lệ cho cả train/test, ghi đè hai tham số riêng. Khi chạy đối chứng cần dùng hai tham số mới và kiểm tra cấu hình đã lưu.

`src/contrastive_selector.py` vẫn có nhánh thiếu vulnerable/safe thì duyệt train để bổ sung tối đa 5 ứng viên với score 0.5. Chưa thấy counter hoặc metadata ghi nhánh này, và chưa thấy bảng tần suất riêng Devign/ReVeal. `project_docs/plans/GRACE_IMMEDIATE_ACTION_PLAN.md` có kế hoạch instrumentation, không phải bằng chứng đã chạy. Không thể dùng chính sách chọn demo mới của Ablation_V2 để thay thế thống kê nhánh lịch sử này.

## Phần cần đóng trước khi báo hoàn thành đợt 1

1. Hoàn thiện kiểm tra parser của cả hai pipeline; xuất bảng parse_method, invalid, đổi nhãn theo nhãn thật và metric trước/sau cho run có raw. Run mất raw/ID ghi rõ thiếu.
2. Chuẩn hóa evaluator nhận prediction theo mẫu, có hai baseline; tạo lại bảng từ evaluator này. Chốt tập ID chung khi so sánh valid-only.
3. Xuất ledger thống nhất cho các kết quả đã báo cáo, truy vết điều kiện thực tế và ghi missing.
4. Lưu kết quả đối chiếu test/retrieval ID giữa hai bạn và xác nhận split/backbone cho đối chứng sắp tới.
5. Ghi nhận rồi tổng hợp tần suất nhánh bổ sung của contrastive_selector theo dataset; nếu artifact cũ không giữ đủ thông tin thì công khai giới hạn và đo trên lần chạy retrieval được chỉ định, không cần gọi lại LLM.

Audit này không tự sửa pipeline, không đổi contract và không chạy lại inference.
