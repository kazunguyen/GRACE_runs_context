# Đối soát và thiết kế đối chứng cho bốn hướng H của Dũng

**Cập nhật 24/10/2026 — H1, H2, H3-A, H3-B.** Đây là phần bổ sung cho báo cáo cải tiến, tách khỏi báo cáo chung V1/V2 của Dũng–Hiếu. Áp dụng ba đợt và sáu điều kiện của thầy cho từng hướng; giữ kết quả âm và trường hợp chưa đủ bằng chứng. Trong lượt này chỉ đọc artifact, tính lại metric/CI/McNemar và cập nhật báo cáo; **không train hoặc gọi API mới**.

## 1. Đợt 1 — Nền thực nghiệm và bằng chứng đã đối soát

Sáu điều kiện được kiểm trong từng phép so sánh: **LLM; target IDs/code; kho retrieval; tham số suy luận; context/truncation; evaluator**. Không bắt buộc mọi hướng dùng cùng một LLM khi không so trực tiếp với nhau; nhưng hai arm của một đối chứng thành phần phải giữ các điều kiện không thuộc thành phần đang xét.

| Hướng | Reference được dùng | Kết quả đối soát hiện có | Trạng thái |
|---|---|---|---|
| H1 | Whitening 256, cùng common top-50/top-5, rerank, một demo và graph policy | Raw Qwen/Vertex/context 8192 khớp prompt/code. Common-pool hash giống và graph query giống trên toàn bộ ID được ghép. V1 loại 12 Devign/69 ReVeal thiếu metadata request; V2 ReVeal có 9 invalid. | Có thể phân tích paired trên phần đủ bằng chứng; chưa coi chênh lệch là tác động thuần của retrieval vì có dao động ở prompt giống hệt. |
| H2 | Cần graph-prefix control có cùng demo/code được khôi phục, cap 25/25 và tổng 8192 byte như H2 v3 | H2 Vertex DeepSeek đã có đủ 2732/2274 target, code hash khớp canonical. Baseline DeepSeek test FPT mới cũng đã có, nhưng khác provider/thinking khai báo và cách dựng graph/demo; H2 lấy demo theo run Reproduced-Code-Based, không mặc định bằng baseline H3-B. | Chưa đủ đối chứng chỉ thay evidence; không lấy chênh lệch H2 với Qwen hoặc FPT khác policy làm tác dụng H2. |
| H3-A | Gate/routing đã khóa + cùng file expert H1 cho cả reference và cascade | Đã có phép tái dựng được chấp nhận: Devign dùng `9afe3268729648c6`, ReVeal dùng `0779c879b6d11431`. ReVeal là benchmark với expert H1, không phải hoàn tất run FPT cũ. | Có paired test; giảm query rất nhỏ hoặc bằng 0. |
| H3-B | Winner trong session `deepseek_v41_hieu_8192_seed42`, so với full GRACE và các classifier controls | Đã có winner lock và prediction test của 16 arm cho cả hai dataset. Đã đối chiếu checksum lock/model manifest/prediction, code hash và metric lưu. Validation do Hiếu chạy Vertex; test baseline `abbf356612344183` qua FPT. | Benchmark hiện có đã đi qua train/meta-fit/lock/test; winner là `gate_tuned`, không phải một arm kết hợp LLM. |

**Phân loại theo Mục 1 của thầy:** đã xác định ảnh hưởng của thiếu metadata/invalid, demo bị cắt rỗng, khác context/provider và overlap/exposure. Không có bất đồng giữa parser dòng cuối và prediction trong các raw H1 đủ điều kiện đã kiểm. Chưa đủ dữ liệu để chứng nhận mọi checkpoint lịch sử hoặc giải thích nguyên nhân provider trả response rỗng. Không suy từ việc đã sửa code sang khẳng định mọi run cũ không bị ảnh hưởng.

Nhãn train/development được dùng đúng vai trò học/chọn tham số. Nhãn test chỉ dùng đánh giá sau khi có prediction; không đưa vào retrieval, renderer hoặc routing. Hai split validation/test cần khác nhau; yêu cầu cùng target áp dụng giữa các arm trên cùng split, không buộc validation trùng test.

## 2. Kết quả offline đã tính thêm

Dùng một evaluator cho các cặp trong phần bổ sung: nhãn canonical theo ID/code hash; giữ invalid trong coverage; metric paired trên giao ID hợp lệ của hai arm. Hai đối chứng hằng dùng đúng cohort đó. Precision/MCC không xác định được ghi N/A; bảng lịch sử giữ quy ước cũ để truy vết, không âm thầm sửa artifact.

CI dưới đây dùng **5000 lần bootstrap ghép cặp theo query, seed 42**; McNemar exact hai phía dùng hai ô reference sai/phương án mới đúng và ngược lại. Đây là phân tích hậu kiểm trên test đã được xem, chưa chỉnh phụ thuộc project/commit, chưa hiệu chỉnh nhiều phép so sánh; không dùng như một xác nhận đăng ký trước. Δ lấy phương án mới trừ reference.

| Cặp: phương án mới so với reference | ID chung hợp lệ | MCC reference / mới | ΔMCC | CI 95% ΔMCC | Sửa đúng / làm sai | McNemar p |
|---|---:|---|---:|---|---:|---:|
| H1-V1 / Devign | 2720 | 0,0571 / 0,0263 | -0,0308 | [-0,0520; -0,0105] | 60 / 97 | 0,0039 |
| H1-V1 / ReVeal | 2205 | 0,0350 / 0,0275 | -0,0075 | [-0,0235; 0,0078] | 24 / 30 | 0,4966 |
| H1-V2 / ReVeal | 2265 | 0,0340 / 0,0359 | 0,0019 | [-0,0148; 0,0186] | 51 / 38 | 0,2031 |
| H3-A / Devign | 2732 | 0,0587 / 0,0595 | 0,0008 | [0,0000; 0,0025] | 1 / 0 | 1,0000 |
| H3-A / ReVeal | 2274 | 0,0318 / 0,0318 | 0,0000 | [0,0000; 0,0000] | 0 / 0 | 1,0000 |
| H3-B gate_tuned / Devign | 2732 | 0,0668 / 0,2961 | 0,2292 | [0,1844; 0,2743] | 580 / 303 | 0,0000 |
| H3-B gate_tuned / ReVeal | 2274 | 0,0971 / 0,3705 | 0,2734 | [0,1981; 0,3477] | 201 / 218 | 0,4345 |


H1-V1 Devign có MCC giảm trong phép đo này; hai cặp ReVeal H1 chưa cho bằng chứng lợi ích. H3-A Devign chỉ sửa một số rất ít ca, CI chạm 0; ReVeal bằng reference. Gate H3-B có tín hiệu tốt hơn full GRACE trên test hiện tại, nhưng cần phân biệt lợi ích của classifier/ngưỡng với lợi ích của việc kết hợp GRACE.

### 2.1. H1 — kiểm tra biến mà LLM thực sự nhận

| Cặp H1 | Prompt giống hệt | Prediction khác trong phần prompt giống | Đổi ID demo nhưng prompt vẫn giống | Demo baseline / H1 bị cắt còn 0 ký tự |
|---|---:|---:|---:|---:|
| devign_V1 | 2168 | 0 | 137 | 1173 / 1173 |
| reveal_V1 | 1865 | 0 | 80 | 634 / 634 |
| reveal_V2 | 2179 | 77 | 39 | 658 / 658 |


Đổi demo ID không bảo đảm đổi prompt: fitter có thể cắt phần demo tới rỗng. Ngược lại, prompt giống hệt vẫn có thể cho prediction khác qua hai lượt gọi. Vì vậy, cần lưu cả selected demo IDs, số ký tự/token thực sự xuất hiện và raw response; repeat prompt gốc là control cần thiết trước khi quy chênh lệch nhỏ cho projection. Không thay prediction lịch sử hoặc dùng cache khác run để che dao động.

### 2.2. H3-B — kết quả cuối của session đã có

| Dataset / arm | Ngưỡng | Valid / invalid | TN / FP / FN / TP | Acc (%) | P / R / F1 (%) | MCC | BA (%) | Query expert (%) |
|---|---:|---:|---|---:|---|---:|---:|---:|
| devign / `full_grace` | — | 2732 / 0 | 1247 / 230 / 995 / 260 | 55,16 | 53,06 / 20,72 / 29,80 | 0,0668 | 52,57 | 100,00 |
| devign / `gate_0_5` | 0,50 | 2732 / 0 | 1056 / 421 / 521 / 734 | 65,52 | 63,55 / 58,49 / 60,91 | 0,3025 | 64,99 | 0,00 |
| devign / `gate_tuned` | 0,53 | 2732 / 0 | 1144 / 333 / 615 / 640 | 65,30 | 65,78 / 51,00 / 57,45 | 0,2961 | 64,23 | 0,00 |
| reveal / `full_grace` | — | 2274 / 0 | 1907 / 137 / 195 / 35 | 85,40 | 20,35 / 15,22 / 17,41 | 0,0971 | 54,26 | 100,00 |
| reveal / `gate_0_5` | 0,50 | 2274 / 0 | 2022 / 22 / 200 / 30 | 90,24 | 57,69 / 13,04 / 21,28 | 0,2414 | 55,98 | 0,00 |
| reveal / `gate_tuned` | 0,14 | 2274 / 0 | 1790 / 254 / 95 / 135 | 84,65 | 34,70 / 58,70 / 43,62 | 0,3705 | 73,13 | 0,00 |


Winner được chọn trên development là `gate_tuned`: ngưỡng **0,53 Devign**, **0,14 ReVeal**. Giữ nguyên winner đó dù một control có điểm test cao hơn; ví dụ Devign `gate_0_5` có MCC cao hơn `gate_tuned`, nhưng không chọn lại bằng test.

`gate_tuned` dùng classifier/fusion và ngưỡng, **query expert = 0**. Do đó có thể báo classifier đạt kết quả tốt hơn full GRACE trong cấu hình này; chưa thể gọi đó là bằng chứng routing/stacking với LLM có ích. Các arm benefit-router, selector và stacking vẫn phải đối chiếu với gate độc lập được khóa cùng quy trình, không chỉ với full GRACE yếu hơn.

So với base classifier/fusion đã chọn trên train, gate_tuned chỉ tăng MCC khoảng +0,0076 trên Devign và +0,0146 trên ReVeal; cả hai CI đều chứa 0. Vì vậy, ngay cả lợi ích của điều chỉnh ngưỡng so với base winner cũng chưa được xác nhận trên hai cặp này.

Manifest giữ `expert_shift` và `benchmark_comparable=false` do endpoint/provider/alias model khác, thinking validation chưa ghi còn test ghi false. Cờ này nói cấu hình chưa xác minh tương đương, không phủ nhận metric đã tính hay chứng minh hai bên chắc chắn khác trọng số. Với arm không gọi expert, prediction không phụ thuộc response LLM lúc test; với arm kết hợp expert, cần kiểm tra sự ổn định dưới giả định cùng backbone và công bố khác biệt phục vụ.

## 3. Đợt 2 — Ma trận đối chứng tối thiểu cho từng hướng

Các dòng chưa có prediction được ghi là **cần chạy**. Không lấy kiểm thử code, proxy retrieval hay benchmark GRACE baseline làm kết quả cuối của cải tiến.

| Hướng / giả thuyết chính | Cặp đối chứng và controls | Những thứ giữ cố định | Tiêu chí và việc còn thiếu |
|---|---|---|---|
| **H1-V2:** residual local có cải thiện việc chọn demo hữu ích cho LLM? | Whitening 256 ↔ residual-local 256; thêm residual-CE cùng kiến trúc. Nếu cần quy đóng góp loss mới thêm ablation geometry/local, ghi rõ arm nào chưa implement/chưa inference. | Encoder/cache, full train, common top-50, top-5/rerank, một demo, query graph, fitter, provider và params. Head/epoch chọn trên development; test không chọn objective/seed. | MCC downstream là chính; proxy P@5 chỉ hỗ trợ. Báo % đổi demo, % đổi prompt, % demo rỗng; repeat control trên prompt giống. V2 Devign và downstream residual-CE còn thiếu. |
| **H2:** evidence có liên kết thao tác–guard giúp hơn graph prefix trong cùng budget? | Prefix control ↔ H2 đầy đủ; control bỏ phần guard/counterevidence giữ cùng thao tác/data evidence và không lấp chỗ trống; có thể thêm slicing thuần khi cần phân biệt. | Cùng target, demo IDs/code/label, instruction ngoài graph; khôi phục code theo cùng policy trước cả hai arm; cap 25/25, tổng 8192 byte, cùng nguồn graph và LLM. | Tạo baseline bằng đúng policy H2; control mới chưa có inference. Kiểm guard gắn đúng thao tác, closure, polarity/unknown; lấy ví dụ đúng và sai. Nếu đồng thời đổi cách khôi phục demo thì phải gọi là so toàn cấu hình. |
| **H3-A:** routing giảm query mà giữ ràng buộc bỏ sót? | Full GRACE ↔ cascade đã khóa; gate-only là control bắt buộc. Random routing cùng query ratio là control đề nghị nếu muốn chứng minh chọn đúng mẫu. | Cùng expert output cho cùng prompt/ID, feature/model gate, threshold chọn trên validation, metric/fallback. Random control không dùng nhãn test. | Báo query ratio, FN tăng/giảm và upper bound trên validation; config hiện có `max_lost_positive_fraction=0.01`, không coi đó là bảo đảm test. Cần định trước mức giảm chất lượng chấp nhận và mức tiết kiệm đáng quan tâm. |
| **H3-B:** expert có bổ sung giá trị vượt classifier tốt nhất đã khóa? | Winner khóa ↔ gate độc lập ↔ full GRACE; báo các router/selector/stacking như controls, không chọn winner theo test. Ablation view phải train/chọn lại trong development. | Cùng cohort, encoder/feature recipe, expert file, seed/folds; preprocessing/calibration fit trong fold train; train OOF và meta OOF không dùng test để chọn ngưỡng. | Session hiện tại đã có benchmark, winner không cần LLM. Phép xác nhận tiếp phải đo ΔMCC so với gate và chi phí tăng, không chỉ thắng full GRACE. Không bắt buộc winner phải là ensemble nếu classifier tốt hơn. |

### 3.1. Controls chung từ yêu cầu của thầy

- **B0–B1:** code-only ↔ code + graph, không demo; **B1–B2:** thêm một demo đã đóng băng để kiểm tín hiệu. Dùng đúng cùng LLM/budget/evaluator. Đây là controls cho nhánh GRACE; không thay thế đối chứng graph trong cấu hình đã có demo.
- **Graph trong ICL:** giữ cùng demo/code/instruction, bỏ graph và không retrieve lại hoặc nhồi nội dung khác vào phần trống. Muốn đo riêng representation thì dùng cùng node/edge, chỉ đổi cách render.
- **Label flip:** chỉ đổi nhãn demo ở mọi vị trí do template sinh; giữ nguyên code/demo/order/graph. Với hai demo đổi cả hai. **Repeat original** dùng prompt giống hệt để đo dao động; order-swap là phép khác. Controls này áp dụng cho GRACE expert; gate-only không có nhãn demo để đảo.
- **Subset:** chỉ giảm số target gọi LLM; giữ full retrieval bank và danh sách ứng viên đã khóa. Demo một mẫu dùng để kiểm luồng, không được báo như benchmark.

### 3.2. Đánh giá retrieval/evidence bằng mã nguồn

Với H1, lấy cùng target và demo trước/sau; với H2, lấy cùng graph input và phần evidence được giữ/bỏ. Hồ sơ mỗi ca giữ code/ID/hash, vai trò biến, sink/thao tác, guard/nhánh thoát và lý do Unknown. Không chấm chất lượng retrieval bằng chính hàm score nó tối ưu, không dùng nhãn target để chọn demo đẹp hơn.

Lượt Codex hỗ trợ đọc code phải ghi nguồn thực hiện và mức hỗ trợ. Nếu cần đánh giá độc lập, packet phải tạo từ selections thật, che tên arm/score, khóa đánh giá trước giải mã và giữ bất đồng; xác nhận một bảng tổng hợp không thay thế bằng chứng quá trình. Chưa tạo thêm phiếu hoặc kết quả chấm mới trong lượt này.

## 4. Đợt 3 — Xác nhận, giải thích và điều kiện dừng

Trước lượt xác nhận, khóa **một phép so sánh chính cho mỗi hướng** trên development, cùng tiêu chí và ngân sách. MCC/BA là thước đo khả năng phân biệt; F1, confusion matrix và tỷ lệ dự đoán 1 giải thích đánh đổi. Routing còn phải đạt mục tiêu query/cost dưới ràng buộc chất lượng. Giữ cả always-0/always-1 trên đúng ID, báo invalid/fallback và coverage theo nhãn.

Bootstrap theo nhóm project/commit hoặc ít nhất code hash khi dữ liệu phụ thuộc; chạy seed/lượt độc lập cho cấu hình đã chọn, không lấy seed tốt nhất. Độ bất định do lấy mẫu và dao động LLM được báo riêng. Chi phí tách prepare/train/retrieval, số query theo thuật toán, request vật lý/cache/retry và latency/token/tiền; thiếu usage ghi thiếu, không suy từ query ratio.

Test hiện tại đã được xem trong quá trình phát triển; paired CI mới chỉ tăng độ chặt của phân tích trên cohort này. Cần holdout chưa dùng chọn phương án hoặc split project/time trước kết luận khái quát. Nếu MCC vẫn gần 0 hoặc CI không xác nhận lợi ích, ưu tiên lỗi nhãn/overlap, graph/demo bị cắt và độ nhạy prompt; không thêm thành phần chỉ để tìm một F1 cao hơn.

## 5. Việc đã làm và thứ tự tiếp tục

| Ưu tiên | Đã làm trong lượt này | Việc tiếp theo |
|---|---|---|
| 1 | Chuẩn hóa metric paired, ghép ID, kiểm code/prompt/parser H1; tính CI và McNemar; kiểm checksum session H3-B. | Chốt một protocol/evaluator và danh sách cặp xác nhận; giữ các bảng cũ là snapshot, không gộp khác cohort. |
| 2 | Cập nhật baseline DeepSeek test và benchmark H3-B thực tế; chỉ rõ gate thắng, chưa có lợi ích ensemble được xác nhận. | Phân tích các ca gate sửa đúng/làm sai so với expert; xác nhận expert có thêm giá trị so với gate trong một lượt đã khóa. |
| 3 | Kiểm H2 đủ target/code, xác định baseline khác policy chưa cô lập evidence. | Dựng prefix control bằng cùng builder/policy H2, khóa từ validation rồi mới inference cặp. |
| 4 | Phát hiện prompt H1 giống nhưng prediction khác và demo có thể rỗng; lượng hóa mức tiết kiệm H3-A. | Chạy controls repeat/graph/demo hoặc H1-V2 Devign theo giả thuyết đã chốt; không cần chạy toàn bộ tổ hợp. |
| 5 | Lưu script, audit JSON, source SHA-256 và bản báo cáo trước sửa. | Xin thống nhất với thầy mốc nộp, dữ liệu xác nhận và trần chi phí trước lượt LLM/huấn luyện tiếp theo. |

## 6. Artifact và cách tái lập phần offline

- [Phản hồi và lộ trình của thầy](https://github.com/HuuHieu03/GRACE/blob/5987486641fe1db799d472f0ba6ed509c3b601ad/project_docs/docs/reports/GRACE_phanhoibaocaoDungHieu.docx).
- [Script đối soát](tools/audit_h_controls_20261024.py) — dùng chung evaluator cho mọi cặp trong phần bổ sung, không train/gọi API.
- [Audit JSON](audits/h_controls_20261024/audit_results.json) — metric hai arm/đối chứng hằng, ID hash, CI/McNemar, ca sửa đúng/làm sai, nguồn SHA-256 và trạng thái expert.
- [Session H3-B](audits/h_controls_20261024/h3b_session_snapshot/benchmark_summary.json) và [winner lock](audits/h_controls_20261024/h3b_session_snapshot/winner_lock.json); nguồn validation do Hiếu chạy, test baseline mới `abbf356612344183`.
- [Ledger](bang_quan_ly_run_cai_tien.md) và [metric hiện hành](metric_cai_tien_vertex_qwen_context8192.md); [bản báo cáo trước bổ sung](audits/h_controls_20261024/before_reports).

Chạy từ thư mục SHARE: `python tools/audit_h_controls_20261024.py`. Script tính lại từ prediction/raw/prompt hiện có; từ chối duplicate IDs, hash không khớp hoặc metric H3-B lệch prediction. Output mới có provenance riêng, không sửa response, nhãn hoặc lock gốc.
