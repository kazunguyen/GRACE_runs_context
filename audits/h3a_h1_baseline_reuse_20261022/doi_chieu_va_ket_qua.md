# Đối chiếu H3-A với baseline H1 — 22/10/2026

## Kết luận
Không thể ghi hai run ReVeal FPT cũ là đã được hoàn tất bằng H1: model/provider khác, và nhiều prompt không trùng. Có thể đánh giá riêng H3-A với gate đã khóa và expert chính là baseline H1 (Qwen/Vertex/8192), không gọi LLM mới. Đây là phép tái dựng có provenance riêng, không phải nối tiếp hoặc sửa kết quả FPT cũ.

| Đối chiếu | Số mẫu | Code khớp | Prompt khớp tuyệt đối | Prompt khác |
| --- | ---: | ---: | ---: | ---: |
| reveal8192_full | 2274 | 2274 | 1426 | 848 |
| reveal8192_prefix1137 | 1137 | 1137 | 977 | 160 |
| reveal24000_full | 2274 | 2274 | 772 | 1502 |
| reveal24000_partial1140 | 1140 | 1140 | 573 | 567 |
| devign8192_full | 2732 | 2732 | 2732 | 0 |

H1 ReVeal nguồn: `0779c879b6d11431`, không dùng `2d1845eabf62eb84` vì run đó còn12 invalid. H1 Devign nguồn: historical `9afe3268729648c6`. Đã xác minh toàn bộ prediction/raw/prompt SHA256, request_key, request_spec và parse dòng cuối cho2274/2732 mẫu. Request spec H1: Qwen3-Coder480B, Vertex, temp0, seed42, max_tokens256, exact_last_line_binary_v1. Đổi sang nguồn Qwen không phải tương đương response DeepSeek/FPT cũ.

ReVeal full8192 chỉ1426/2274 prompt giống; 848 khác. Trong prefix1137 là977 giống/160 khác. Full24000 là772 giống/1502 khác; partial1140 là573 giống/567 khác. Nguyên nhân bao gồm nội dung/schema graph, demo hoặc ngân sách cắt context; cùng arm không bảo đảm cùng prompt. Ví dụ ID reveal:test:7092216800726729686#30: H1 prompt1424byte, H3 bản8192 prompt6430byte, graph schema khác. Bản24000 vẫn tạm loại theo quyết định hiện tại; không đổi tên nó thành8192.

Devign full2732 prompt khớp tuyệt đối, cùng Qwen request spec với H3 Devign reference: có thể dùng H1 làm nguồn response chuẩn cho phép so sánh gate/reference. Hai lượt gọi độc lập cùng config có thể cho prediction khác; phép tái dựng dùng cùng response H1 cho cả reference và cascade, không cam kết tái hiện bitwise kết quả H3 cũ.

## Kết quả tái dựng H3-A dùng H1 làm expert
Gate/routing cố định, nhãn test chỉ dùng đánh giá. Nhánh inspect lấy prediction H1; nhánh skip_low dùng0; direct_high nếu có dùng prediction cố định. Toàn bộ cohort giữ nguyên. Nhánh GRACE được định nghĩa bằng prompt H1, nên ReVeal tái dựng này không tuyên bố giữ nguyên prompt H3 cũ.

| Tập / nguồn H1 | N | Inspect | P (%) | R (%) | F1 (%) | MCC | Acc (%) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| reveal / 0779c879b6d11431 | 2274 | 2274 | 11.65 | 32.17 | 17.11 | 0.0318 | 68.47 |
| devign / 9afe3268729648c6 | 2732 | 2726 | 51.11 | 27.49 | 35.75 | 0.0595 | 54.61 |

ReVeal routing2274/2274 inspect: cascade bằng baseline H1, không có tiết kiệm call. Devign2726 inspect,6 skip_low. API mới=0. Đây là tiết kiệm call theo thuật toán, không phải đo latency thực tế khi gọi LLM.

## Artifact
- audit.json: số đếm, request spec, đường dẫn và SHA256 file nguồn.
- *_matches.jsonl: đối chiếu từng ID/code/prompt.
- *_h1_expert_cascade_predictions.jsonl: dự đoán tái dựng và nguồn response mỗi mẫu.
- *_h1_expert_evaluation.json: metric cascade/full H1 reference/gate-only.

Giữ nguyên số liệu/link run FPT gốc trong bảng; chỉ thêm ghi chú dẫn tới phép tái dựng này. Không trộn response FPT/Qwen và không công bố một benchmark lai dưới tên cùng model.

## Quyết định sử dụng được người dùng chấp nhận — 22/10/2026

Dùng kết quả baseline H1 làm expert cho H3-A: ReVeal/test `0779c879b6d11431`, Devign/test `9afe3268729648c6`, cùng Qwen3-Coder-480B/Vertex/context8192. Lý do người dùng chấp nhận: thuật toán chọn demo và truncate giống nhau; chấp nhận khác biệt graph artifact/thứ tự render và các demo phát sinh từ graph, không yêu cầu prompt thực tế trùng byte để dùng phép đánh giá gate + H1 expert.

Kết quả tái dựng đã xuất là kết quả được chọn dùng cho đánh giá H3-A theo quyết định này, không chỉ là gợi ý thay thế. Không cần gọi LLM mới. Dùng prediction H1 cho inspect, prediction gate cho nhánh bỏ qua. ReVeal toàn bộ2274 inspect nên F1=17,11%, MCC=0,0318 bằng baseline H1. Devign2726 inspect/6 skip_low, F1=35,75%, MCC=0,0595.

Quyết định này cho phép dùng nguồn H1 khác prompt thực tế; không biến các prompt thành giống byte, không biến các lượt FPT partial thành đã inference xong, và không đổi kết quả FPT/24000 thành benchmark8192. Nguồn Qwen/H1 và kết quả tái dựng được ghi riêng, không trộn response giữa model.
