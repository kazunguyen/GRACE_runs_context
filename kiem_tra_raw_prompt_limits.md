# Kiểm tra giới hạn raw prompt của 36 run lịch sử

Đã đo 90,108 prompt từ các file liên kết trong bảng quản lý; không dựng lại prompt, không gọi LLM, không sửa dữ liệu inference.

Ngưỡng kiểm tra: 8.192 byte UTF-8, 40 khai báo node và 80 khai báo edge. Số mẫu có lỗi kiểm tra: 0.
Giá trị lớn nhất đo được: 8192 byte; 40 khai báo node; 80 khai báo edge.

Lưu ý: đếm node/edge trong phần GRAPH CONTEXT và đối chiếu graph_counts; source_nodes/source_edges là graph nguồn trước cắt, không phải số được gửi. Giới hạn node ở đây là số khai báo node, không phải hợp của mọi ID xuất hiện trong endpoint cạnh.
Có 984 prompt dùng graph legacy không giữ ánh xạ node-ID; có 382 prompt có hơn 40 ID endpoint cạnh khác nhau. Vì vậy không thể khẳng định graph là subgraph khép kín tối đa 40 đỉnh chỉ từ việc số khai báo node <=40.

Chưa phục hồi snapshot contract lịch sử đúng hash: báo cáo xác thực ba giới hạn nêu trên, không chứng nhận mọi điều khoản contract. Chi tiết từng run và lỗi nằm trong kiem_tra_raw_prompt_limits.json.

| Run | Prompt | Max bytes | Max nodes | Max edges | Lỗi |
|---|---:|---:|---:|---:|---:|
| Reproduced-Code-Based/devign/test | 2732 | 8192 | 40 | 80 | 0 |
| Reproduced-Code-Based/reveal/test | 2274 | 8192 | 40 | 80 | 0 |
| Reproduced-Paper-Based/devign/test | 2732 | 8192 | 40 | 80 | 0 |
| Reproduced-Paper-Based/reveal/test | 2274 | 8192 | 40 | 80 | 0 |
| Devign/Ablations/Full-cai-tien/test_v2 | 2732 | 8192 | 40 | 65 | 0 |
| Devign/Ablations/Grace-baseline/test_v2 | 2732 | 8192 | 40 | 80 | 0 |
| Devign/Ablations/No-C1-hybrid-retrieval/test_v2 | 2732 | 8192 | 40 | 65 | 0 |
| Devign/Ablations/No-C2-stratified-demo-selection/test_v2 | 2732 | 8192 | 40 | 66 | 0 |
| Devign/Ablations/No-C3-GEPA-prompt-optimization/test_v2 | 2732 | 8192 | 40 | 76 | 0 |
| Devign/Ablations/No-C5-graph-verbalization/test_v2 | 2732 | 8192 | 40 | 80 | 0 |
| Devign/Ablations/No-C6-graph-slicing/test_v2 | 2732 | 8192 | 40 | 78 | 0 |
| Devign/Ablations/No-C7-security-cot/test_v2 | 2732 | 8192 | 40 | 68 | 0 |
| Devign/Ablations/No-C8-mmr-demo-selection/test_v2 | 2732 | 8192 | 40 | 65 | 0 |
| Devign/Ablations/Plus-C1-tri-signal-retrieval/test_v2 | 2732 | 8192 | 40 | 80 | 0 |
| Devign/Ablations/Plus-C2-stratified-demos/test_v2 | 2732 | 8192 | 40 | 80 | 0 |
| Devign/Ablations/Plus-C3-gepa-prompt/test_v2 | 2732 | 8192 | 40 | 80 | 0 |
| Devign/Ablations/Plus-C5-graph-verbalization/test_v2 | 2732 | 8192 | 40 | 80 | 0 |
| Devign/Ablations/Plus-C6-graph-slicing/test_v2 | 2732 | 8192 | 40 | 80 | 0 |
| Devign/Ablations/Plus-C7-security-cot/test_v2 | 2732 | 8192 | 40 | 80 | 0 |
| Devign/Ablations/Plus-C8-mmr-selection/test_v2 | 2732 | 8192 | 40 | 80 | 0 |
| Reveal/Ablations/Full-cai-tien/test_v2 | 2274 | 8192 | 40 | 65 | 0 |
| Reveal/Ablations/Grace-baseline/test_v2 | 2274 | 8192 | 40 | 80 | 0 |
| Reveal/Ablations/No-C1-hybrid-retrieval/test_v2 | 2274 | 8192 | 40 | 65 | 0 |
| Reveal/Ablations/No-C2-stratified-demo-selection/test_v2 | 2274 | 8192 | 40 | 65 | 0 |
| Reveal/Ablations/No-C3-GEPA-prompt-optimization/test_v2 | 2274 | 8192 | 40 | 75 | 0 |
| Reveal/Ablations/No-C5-graph-verbalization/test_v2 | 2274 | 8192 | 40 | 80 | 0 |
| Reveal/Ablations/No-C6-graph-slicing/test_v2 | 2274 | 8192 | 40 | 79 | 0 |
| Reveal/Ablations/No-C7-security-cot/test_v2 | 2274 | 8192 | 40 | 67 | 0 |
| Reveal/Ablations/No-C8-mmr-demo-selection/test_v2 | 2274 | 8192 | 40 | 65 | 0 |
| Reveal/Ablations/Plus-C1-tri-signal-retrieval/test_v2 | 2274 | 8192 | 40 | 80 | 0 |
| Reveal/Ablations/Plus-C2-stratified-demos/test_v2 | 2274 | 8192 | 40 | 80 | 0 |
| Reveal/Ablations/Plus-C3-gepa-prompt/test_v2 | 2274 | 8192 | 40 | 80 | 0 |
| Reveal/Ablations/Plus-C5-graph-verbalization/test_v2 | 2274 | 8192 | 40 | 80 | 0 |
| Reveal/Ablations/Plus-C6-graph-slicing/test_v2 | 2274 | 8192 | 40 | 80 | 0 |
| Reveal/Ablations/Plus-C7-security-cot/test_v2 | 2274 | 8192 | 40 | 80 | 0 |
| Reveal/Ablations/Plus-C8-mmr-selection/test_v2 | 2274 | 8192 | 40 | 80 | 0 |
