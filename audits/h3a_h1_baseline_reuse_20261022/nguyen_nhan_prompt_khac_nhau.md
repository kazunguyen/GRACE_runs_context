# Vì sao prompt baseline H1 và H3-A khác nhau?

Đối chiếu ReVeal/test H1 `0779c879b6d11431` với H3-A8192 `f65b0c326b9337c4`, tổng2274 mẫu. Đây là điều tra artifact/code, chưa sửa code, cache hoặc chạy lại Joern/LLM.

## Kết luận
Cùng thuật toán và hàm render, nhưng không dùng cùng toàn bộ graph artifact. Graph tác động trực tiếp đến prompt và gián tiếp đến chọn demo qua syntax rerank. Chuyển context24000 xuống8192 không đồng bộ lại graph/demo với H1. Gate không phải bước tự đổi nội dung prompt: run ReVeal này có2274/2274 inspect.

## Đối chiếu pipeline
| Bước | H1 so với H3-A | Bằng chứng |
| --- | --- | --- |
| Dataset/train/test, code identity | Giống | data_manifest, train/targets identity trong manifest khớp;2274 code hashes khớp |
| CodeT5 embedding/recipe | Giống | index/vector hashes của train/query và recipe khớp |
| Whitening dimension/semantic retrieval | Giống | dimension256; top50 candidate IDs và top5 semantic IDs/khoảng cách khớp2274/2274 retrieval rows |
| Graph inputs | Khác | graph_feature_sha256 lệch1163/2274, schema lệch41; hash graph có metadata nên không đồng nghĩa1163 prompt khác |
| Lexical/syntax rerank | Cùng code, khác graph đầu vào | retrieval.py hash khớp; selected demo IDs khác20/2274 |
| Template/render/fitter | Giống code | reference.py hash c81abb7376a8c43ba192598b63c3693884ac4eb7e4593cda9f7aaed246abc82e ở cả hai manifest; template hash khớp |
| Context workflow | Khác nguồn | H1 render trực tiếp8192; H3 source24000 rồi prepare_context_view refit8192, giữ demo/graph nguồn H3 |

## 848 prompt khác ở đâu?
| Phần thay đổi | Số mẫu |
| --- | ---: |
| Chỉ GRAPH CONTEXT | 831 |
| Chỉ REFERENCE EXAMPLES | 5 |
| Cả GRAPH CONTEXT và REFERENCE EXAMPLES | 12 |
| TASK INSTRUCTION, TARGET CODE, OUTPUT CONTRACT khác | 0 |

Tổng khác graph843; khác văn bản demo17. Demo ID đổi20 không đồng nghĩa có20 đoạn demo text đổi: một số ID khác vẫn render text giống sau cắt/equivalent code; không suy từ ID sang khác byte.

## Graph: vấn đề lớn nhất
- Trong843 graph context khác,616 chỉ khác thứ tự cạnh: node text giữ nguyên, multiset dòng cạnh giống, chuỗi thứ tự khác. Không chỉ đổi ID node.
-741/843 giữ nguyên đoạn nodes nhưng khác đoạn edges; trong đó616 chỉ đổi thứ tự,125 còn lại khác multiset cạnh hiển thị. Prefix80 cạnh và cắt theo byte khiến khác thứ tự có thể làm khác cả tập cạnh được giữ; chưa kết luận full graph của125 trường hợp khác cấu trúc.
-99 trường hợp H1 GRAPH UNAVAILABLE nhưng H3 có graph. Không có trường hợp ngược lại trong843.
- Ví dụ reveal:test:7092216800726729686#30: H1 graph chỉ câu unavailable, prompt1424byte; H3 có CPG, prompt6430byte. Cùng target và demo, khác graph thật trong prompt.
- Ví dụ reveal:test:-1929262071302712016#505: cùng các cạnh CDG nhưng thứ tự dst55834574851,30064771086,30064771087,30064771088 đổi giữa hai prompt.

Code reference.py::parse_graphml append nodes/edges theo thứ tự XML, không canonical-sort danh sách trước lưu. raw_graph_context lấy40 nodes đầu và80 cạnh đầu sau lọc, render nguyên thứ tự. ast_edge_tokens cũng sinh từ thứ tự AST edges. Vì vậy hai cache/export có thể khác serialization, làm prompt khác và làm syntax similarity khác dù thuật toán retrieval không đổi.

graphs.py của hai run có hash khác. Diff hiện khớp các hash manifest: H1 tìm GraphML chỉ tầng đầu bằng glob, H3 tìm đệ quy rglob và bổ sung diagnostics. Chỉ diff này chưa chứng minh nguyên nhân của toàn bộ graph lệch; artifact chứng minh cache/graph đầu vào khác. Chưa xác định đầy đủ phiên bản/config Joern ở từng lần export; không gán mọi sai khác cho phiên bản hay số worker. Graph coverage trong manifest H1≈95.12%, H3≈99.47% phù hợp với việc H3 có thêm graph ở99 mẫu.

## Demo đổi dù embedding giống
rerank dùng0.7*lexical +0.3*syntax. Top5 semantic giữ nguyên, nhưng syntax đọc ast_edge_tokens từ graph target/demo. Graph/serialization đầu vào thay đổi có thể đổi thứ hạng: có20 selected_demo_id khác. Cùng code retrieval không đảm bảo cùng demo nếu graph không cố định. Cần phân biệt đây là nhánh syntax, không phải H1 projection tác động: cả hai run đều baseline_whitening.

## Context8192 không tự làm hai prompt giống nhau
prepare_context_view trong tools/context_limit_rerun.py lấy source H3 `5a64cba3ab7edefb`, không lấy source H1. Nếu source<=8192: giữ nguyên text. Nếu source>8192: đọc graph và demo H3 đã khóa, kiểm tra tái dựng source đúng rồi fit lại8192 bằng cùng fitter. Có872 prompt source quá8192, nhưng đây không phải872 prompt lệch H1. Trên artifact cuối, target/instruction/output đều khớp;848 prompt còn lệch do graph/demo nguồn. Không có bằng chứng cần đổi thuật toán fitter để giải thích chúng.

## Hệ quả và cách đánh giá đúng ý tưởng bộ lọc
Để cô lập tác động gate, dùng nguyên cặp prompt/response baseline H1 làm expert cố định cho cả reference và H3-A. Routing skip_low trả0; inspect lấy prediction H1. Kết quả này đã xuất riêng trong audit cùng folder. Không cần chạy lại LLM; không cần ép prompt H3 lịch sử phải giống mới có thể đánh giá một cascade dùng H1 làm expert. Nhưng không ghi phép tái dựng đó là hoàn tất những request DeepSeek/FPT cũ.

Nếu sau này sinh lại prompt: freeze/reuse cùng graph snapshot và retrieval/demo của baseline cho mọi arm muốn so paired; dùng chung formatter/cap; canonicalize graph serialization có version riêng khi cần rebuild. Không sửa in-place graph/prompt lịch sử vì sẽ mất tính truy xuất nguồn.

## Code để đọc
- D:/JUNIOR/LabThayTho/GRACE-H3-CalibratedCascade/grace_h1/reference.py:67 parse_graphml, :126 ast_edge_tokens, :156 raw_graph_context, :182 fitter.
- D:/JUNIOR/LabThayTho/GRACE-H3-CalibratedCascade/grace_h1/retrieval.py:61 shortlist, :73 rerank.
- D:/JUNIOR/LabThayTho/GRACE-H3-CalibratedCascade/grace_h1/pipeline.py:122-133 render pipeline.
- D:/JUNIOR/LabThayTho/GRACE-H3-CalibratedCascade/tools/context_limit_rerun.py:17 prepare_context_view.
- prompt_difference_causes.jsonl: phân loại theo từng ID trong848 mẫu.

## Quyết định sử dụng được người dùng chấp nhận — 22/10/2026

Dùng kết quả baseline H1 làm expert cho H3-A: ReVeal/test `0779c879b6d11431`, Devign/test `9afe3268729648c6`, cùng Qwen3-Coder-480B/Vertex/context8192. Lý do người dùng chấp nhận: thuật toán chọn demo và truncate giống nhau; chấp nhận khác biệt graph artifact/thứ tự render và các demo phát sinh từ graph, không yêu cầu prompt thực tế trùng byte để dùng phép đánh giá gate + H1 expert.

Kết quả tái dựng đã xuất là kết quả được chọn dùng cho đánh giá H3-A theo quyết định này, không chỉ là gợi ý thay thế. Không cần gọi LLM mới. Dùng prediction H1 cho inspect, prediction gate cho nhánh bỏ qua. ReVeal toàn bộ2274 inspect nên F1=17,11%, MCC=0,0318 bằng baseline H1. Devign2726 inspect/6 skip_low, F1=35,75%, MCC=0,0595.

Quyết định này cho phép dùng nguồn H1 khác prompt thực tế; không biến các prompt thành giống byte, không biến các lượt FPT partial thành đã inference xong, và không đổi kết quả FPT/24000 thành benchmark8192. Nguồn Qwen/H1 và kết quả tái dựng được ghi riêng, không trộn response giữa model.
