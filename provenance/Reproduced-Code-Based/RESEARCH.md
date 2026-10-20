# GRACE: quyết định tái lập theo contract

Nguồn nghiên cứu: PDF gốc trong `GRACE-original-code`, đặc biệt §3.1–3.3, Fig. 5–6 và §4.5; source cùng thư mục (`genexample.py`, `llmpre.py`, `basep.py`, `util.py`). Đã đọc trực tiếp PDF và kiểm tra Fig. 5–6 bằng ảnh render, không chỉ dựa vào bản Markdown cũ.

## Hai profile thực sự khác nhau ở đâu?

| Thành phần | Paper | Source được phát hành | Bản tái lập có contract |
|---|---|---|---|
| Semantic features | CodeT5; không nêu pooling/checkpoint revision | `RobertaModel` từ thư mục tên codet5-base; `sents_to_vecs` và checkpoint không được cung cấp | Dùng encoder CodeT5 thật, masked mean, input 512 tokens; hash checkpoint local. Đây là sửa chữa có chủ đích, không khẳng định model nội bộ giống tác giả |
| Giảm chiều/tìm kiếm | t-SNE → L2 | Whitening, 256 chiều, FAISS inner product | Paper: t-SNE/L2; code: train-only whitening/normalized IP. Exact inner-product ranking thay FAISS IVF nlist=1; tie dùng ID để tái lập |
| Semantic candidates | Top K; không cho K cụ thể | `topK=5` | Contract bắt buộc common top-50 trước; native top-5 được chọn **trong pool này**, không trên toàn bộ train. Đây là khác biệt bắt buộc với cả hai nguồn |
| Lexical | Jaccard token sets, Eq. 1 | Jaccard trên `.split()` | Jaccard whitespace tokens, weight 0.7 lấy từ source |
| Syntactic | Joern AST → SimSBT → normalized Levenshtein, Eq. 2 | `seqratio(str(ast).split(), ...)`; file train_ast_clean.csv và serializer không được cung cấp | Paper: type-only preorder theo AST child ORDER và Eq. 2 (substitution cost 1). Code: sequence ratio trên AST edge strings (indel/substitution cost 2). Serializer của code là lựa chọn tái dựng, chưa chứng minh bằng serializer tác giả |
| Demo | Một demonstration kèm label, Fig. 6 | Nối `row['example']`; nguồn tạo example classification không đầy đủ, `train_nl_list`/`test_nl_list` chưa khai báo | Một demo train có nhãn theo contract; không balance theo lớp, không MMR |
| Graph prompt | Danh sách CPG node/edge, AST+CFG+PDG | `node`/`edge` từ processed JSON, nguồn preprocessing thiếu | Whole CPG, giới hạn 40 nodes/80 edges theo revision hiện tại; giữ node IDs, types/code và typed edges, không GraphVerb/sink slice |
| Prompt/model/data | GPT-4, prompt Fig. 6, 8:1:1, window 8192 tokens | GPT-4; 4000/2000/2000/4000 ký tự; 2000 test đầu | Shared template + binary output + pinned Qwen/Vertex + pinned dataset/cohort + shared caps. Không phải tái lập số liệu GPT-4 trong bài |

Paper không quy định đủ t-SNE dimensions/perplexity/iterations, K, omega, pooling và checkpoint để tái lập bit-for-bit. Mặc định được freeze trong Config: K=5, omega=0.7, t-SNE 2 chiều/perplexity 30/1000 iterations/seed 42. Không được gọi những lựa chọn này là thông số tác giả xác nhận.

t-SNE không có out-of-sample transform. Profile paper fit trên train + **code features không có nhãn** của toàn bộ cohort hiện tại, như một lựa chọn transductive được công khai. Tọa độ phụ thuộc cohort; smoke/subset không được tái sử dụng như tọa độ của full run. Whitening chỉ fit train. Cả hai luôn giữ đầy đủ ngân hàng train khi chạy subset validation.

Đã đối chiếu thêm [ComFormer §III-A.2, Fig. 2](https://arxiv.org/pdf/2107.03644), là nguồn Sim_SBT được GRACE dẫn ở Yang et al. 2021a: traversal đơn giản dùng preorder, không lặp lại type và ngoặc enter/exit của SBT. Profile paper chỉ lấy node types theo mô tả của GRACE; adapter Joern C/C++ vẫn khác AST Java của ComFormer.

## Vì sao không ghép tất cả No-C?

- No-C1 hiện tại dùng code-token Jaccard, không khôi phục CodeT5/whitening hoặc CodeT5/t-SNE.
- No-C5 bỏ toàn bộ graph khỏi prompt. GRACE gốc **có graph**, chỉ không có GraphVerb cải tiến.
- No-C6 vẫn dùng graph đã verbalize; baseline cần node/edge gốc, không chọn sink.
- No-C2/No-C8 hiện giữ bốn demo; paper gốc chọn một demo.
- C4 là metric và vẫn phải giữ theo contract. GEPA, security CoT, stratification và MMR không xuất hiện trong baseline.

Do đó tái sử dụng hạ tầng invariant (dataset adapters, template fitter, evaluator, Joern binary) có ích, nhưng cần runner baseline riêng. Không monkey-patch nhiều arm No-C rồi gọi kết quả đó là GRACE gốc.

## Tái sử dụng: cùng mẫu là điều kiện cần

Mọi nguồn phải khớp canonical ID/code hash hoặc được rekey bằng code bytes xác minh được. Cache embedding còn phải có model/pooling/order manifest. Cache AST còn phải đúng parser/traversal. Graph text còn phải đúng representation. Khớp số dòng không đủ.

Audit thực tế ngày 2026-10-13:

| Cohort test | Targets | Full train | CPG source bytes khớp | Unique code binaries | Exact train/test code overlap |
|---|---:|---:|---:|---:|---:|
| Devign | 2732 | 21854 | 2732 | 2731 | 4 |
| ReVeal | 2274 | 18187 | 2274 | 2272 | 56 |

Các bản sao code mục tiêu trong train bị loại **cho từng query**; không cắt ngân hàng train khi chạy subset. Giữ toàn bộ target cohort, không loại target có graph ít/thất bại để làm số liệu đẹp hơn. Graph export thất bại phải dừng preparation, không âm thầm thay bằng graph rỗng và gọi là đầy đủ CPG.

CPG binary đã xác minh được dùng lại, chỉ xuất thêm whole property graph. Chỉ giữ graph thuộc AST các function trong source; bỏ external stubs/global metadata, không lọc sink/câu lệnh. Các JSONL hiện tại chủ yếu là PDG nên không đủ cho AST SimSBT hay claim whole CPG. GraphVerb hiện có là view đã slice, không thuộc input baseline. SimSBT Tree-sitter có hash nhưng không phải Joern AST-type traversal. Cache CodeT5 cũ là các array positional, thiếu provenance và dùng `RobertaModel` trên checkpoint CodeT5; không được nhập làm CodeT5 thật.

Graph không có function AST được ghi rõ unavailable, target vẫn giữ trong cohort và syntactic score là 0; không dựng AST giả. Preparation full dừng nếu coverage graph dưới 95%. File `graph_coverage.json` và metadata prompt cho phép phân biệt graph thật với fallback. Train embedding và query embedding được cache riêng, nên validation/test cùng profile có thể dùng lại full train encodings.

ReVeal cần chú ý: `hash` là source group, không phải function ID. Adapter canonical dùng `hash#row_index`; loader train Full cũ dùng hash-only. Runner mới tái dựng pool từ từng row train đã pin và key/tie của Full, kiểm tra danh sách legacy candidate IDs trước khi công nhận cùng sample pool. Nếu không khớp, preparation dừng; phải chạy lại Full cùng pool mới trước khi so sánh. Tuyệt đối không join hai hàm khác nhau chỉ vì cùng source-group hash.

## Điều kiện để dùng so sánh

Hai profile xuất manifest riêng với target/train identity, initial candidate IDs + hashes, selected demo IDs + hashes, checkpoint hashes, source hashes, graph feature identity, template/prompt hashes và các thích nghi. Chỉ inference sau freeze. Checkpoint response chỉ tái sử dụng khi prompt hash và model/generation fingerprint trùng.

So sánh với Full chỉ hợp lệ khi cohort, candidate sample pool, backbone/generation, cap/template/output policy cùng được xác nhận. Khác biệt trong số demo và raw graph so với GraphVerb là thành phần phương pháp được so sánh, phải nêu rõ. Chênh lệch tổng hợp không chứng minh riêng một C có hiệu quả; leave-one-out cùng Full phục vụ câu hỏi đó.

**Audit lịch sử theo cap 25/25 cũ:** đếm trong graph context của các prompt đã render (không đếm từ metadata của graph chưa cắt):

| Full test | Số prompt | Vượt 25 node | Vượt 25 edge | Node/edge tối đa quan sát |
|---|---:|---:|---:|---|
| Devign | 2732 | 1548 | 1527 | 40 / 80 |
| ReVeal | 2274 | 1047 | 1258 | 40 / 80 |

Ngày 2026-10-13, theo yêu cầu người dùng, shared contract và hai snapshot đã đổi sang trần 40 node/80 edge, revision `evaluation_contract_v2_graph40x80_20261013`. Audit cả 16 arm có sẵn xác nhận tất cả nằm trong trần mới; No-C6 dùng 40/60, No-C5 không dùng graph. Baseline đọc cap mới tự động. Không cần chạy lại Full chỉ vì sai lệch cap khai báo cũ; điều kiện cohort, candidate sample pool, inference và các thích nghi vẫn phải kiểm tra. Cap 60 edge riêng của No-C6 lịch sử phải được nêu khi diễn giải C6, không giả định mọi renderer dùng đúng 80 edge.

Nguồn hiện tại: `existing_full_prompt_audit.json` cạnh `reuse_audit.json`; nguồn lịch sử và tổng hợp ở `../../STANDARD_FOR_ALL_INFERENCES/graph_budget_audit_before_20261013.json` và `graph_budget_audit.json`. Audit mới phản ánh revision mới; manifest/prompt/response/metrics của experiment cũ không bị sửa. Các con số này là audit input, không phải đánh giá hiệu quả detection.

Fitter Full hiện dùng `len(prompt)` theo ký tự, còn paper nói 8192 tokens. Bản mới giữ cùng thứ tự cắt prefix, thêm upper bound UTF-8 bytes cho input Unicode để không coi ký tự là token đo thật. Manifest lưu prompt chars, bytes và `token_count_measured=false`; đây là giới hạn bảo thủ cho tokenizer BPE, không phải số token đo qua API. Graph cap được áp dụng trước khi fit context; metadata node/edge là số trước bước cắt context, nên số nhìn thấy cuối cùng có thể nhỏ hơn.

Các notebook test tái dùng cohort đã chạy trước đây; không mô tả đây là test chưa từng dùng. Các audit và smoke kỹ thuật không phải kết quả hiệu quả detection. Chưa chạy inference benchmark trong đợt triển khai này.
