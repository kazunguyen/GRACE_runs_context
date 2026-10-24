# Đối soát invalid của 36 run context8192

Nguồn: D:/JUNIOR/LabThayTho/SHARE_36_RUNS_CONTEXT8192_20261020_205918. Đã đọc toàn bộ raw response của 23 run có invalid và đối chiếu prediction/ledger; tổng số invalid đều khớp bảng. Không sửa artifact hoặc gọi LLM.

## N0 / N1 là gì?

N0 là số target có nhãn thật 0 (non-vulnerable/an toàn); N1 là số target có nhãn thật 1 (vulnerable/có lỗ hổng). Đây là cơ cấu nhãn thật của toàn cohort, gồm cả các mẫu có response invalid; không phải số dự đoán 0/1 và không phải TN/TP.

- Devign: N0=1.477, N1=1.255, tổng2.732.
- Reveal: N0=2.044, N1=230, tổng2.274.

## Raw đã ghi được nguyên nhân đến đâu?

| Nhóm | Số ca | Bằng chứng trực tiếp | Kết luận |
|---|---:|---|---|
| Response rỗng, request không báo lỗi | 9.206 | raw_response="", request_error=null, request_status=ok | Không có text cho parser; chưa biết nguyên nhân phía provider/model |
| Lỗi API hết retry | 99 | 429 RESOURCE_EXHAUSTED, attempts=5, invalid_exhausted | Có lý do rõ: cạn tài nguyên/dung lượng phục vụ, thử lại vẫn lỗi |
| Response có chữ nhưng không có nhãn cuối | 2 | Hai đoạn giải thích kết thúc dở, request_status=ok | Sai output contract; parser đánh invalid đúng |
| Tổng | 9.307 | | |

9.206/9.307 (khoảng98,91%) invalid là rỗng không có request_error, không phải lỗi regex gán nhãn sai. Trong9.206 ca này,8.898 có attempts=1;308 có attempts>1. Không được coi mọi ca rỗng là API429. Các ca attempts>1 cho biết có thử lại nhưng gói này không lưu log từng lần để phục hồi lỗi trung gian.

## Vì sao rỗng vẫn ghi ok?

Code request của reproduction_pipeline.py đang dùng:

```python
raw = client.models.generate_content(...).text or ""
error = None
break
```

Sau đó request_status=ok nếu error is None. Nghĩa là ok chỉ xác nhận lời gọi không ném exception ở lần cuối, không xác nhận có câu trả lời. Response text trống vẫn thoát vòng lặp; retry chỉ xảy ra khi exception. Raw hiện có phù hợp với cơ chế này. Đây là giải thích vì sao nội dung invalid có thể đi cùng trạng thái request ok, chưa phải xác định nguyên nhân provider trả text rỗng.

Gói chia sẻ không chứa full JSON provider và log từng retry. Các dòng invalid không lưu finish_reason, usage/token counts, safety/block reason hoặc candidate/reasoning parts. Vì vậy chưa thể khẳng định9206 ca rỗng là do hết output tokens, bị chặn, model không tuân thủ prompt hay lớp SDK trích text. Hai ca giải thích kết thúc dở có thể gợi ý bị cắt, nhưng không có finish_reason để xác nhận.

## Phân rã từng run có invalid

| Run | Invalid / N | Tỷ lệ | Rỗng, status ok | Lỗi429 hết5 lần | Không đúng0/1 |
|---|---:|---:|---:|---:|---:|
| Reveal/Ablations/Plus-C7-security-cot/test_v2 | 1158/2274 | 50.92% | 1149 | 9 | 0 |
| Devign/Ablations/Plus-C8-mmr-selection/test_v2 | 1251/2732 | 45.79% | 1237 | 14 | 0 |
| Reveal/Ablations/No-C5-graph-verbalization/test_v2 | 1036/2274 | 45.56% | 1036 | 0 | 0 |
| Reveal/Ablations/No-C2-stratified-demo-selection/test_v2 | 1013/2274 | 44.55% | 1013 | 0 | 0 |
| Reveal/Ablations/Plus-C1-tri-signal-retrieval/test_v2 | 934/2274 | 41.07% | 934 | 0 | 0 |
| Reveal/Ablations/No-C3-GEPA-prompt-optimization/test_v2 | 930/2274 | 40.90% | 930 | 0 | 0 |
| Reveal/Ablations/Plus-C8-mmr-selection/test_v2 | 795/2274 | 34.96% | 795 | 0 | 0 |
| Reveal/Ablations/No-C8-mmr-demo-selection/test_v2 | 575/2274 | 25.29% | 571 | 4 | 0 |
| Devign/Ablations/Plus-C5-graph-verbalization/test_v2 | 465/2732 | 17.02% | 455 | 10 | 0 |
| Reveal/Ablations/Plus-C3-gepa-prompt/test_v2 | 369/2274 | 16.23% | 355 | 14 | 0 |
| Reveal/Ablations/Plus-C5-graph-verbalization/test_v2 | 182/2274 | 8.00% | 178 | 4 | 0 |
| Reveal/Ablations/No-C1-hybrid-retrieval/test_v2 | 146/2274 | 6.42% | 146 | 0 | 0 |
| Reveal/Ablations/Plus-C6-graph-slicing/test_v2 | 140/2274 | 6.16% | 134 | 6 | 0 |
| Devign/Ablations/Plus-C3-gepa-prompt/test_v2 | 129/2732 | 4.72% | 121 | 8 | 0 |
| Devign/Ablations/Plus-C7-security-cot/test_v2 | 105/2732 | 3.84% | 102 | 3 | 0 |
| Reveal/Ablations/Grace-baseline/test_v2 | 50/2274 | 2.20% | 50 | 0 | 0 |
| Reproduced-Paper-Based/devign/test | 13/2732 | 0.48% | 0 | 13 | 0 |
| Devign/Ablations/No-C2-stratified-demo-selection/test_v2 | 6/2732 | 0.22% | 0 | 6 | 0 |
| Devign/Ablations/Plus-C2-stratified-demos/test_v2 | 4/2732 | 0.15% | 0 | 3 | 1 |
| Reveal/Ablations/No-C7-security-cot/test_v2 | 2/2274 | 0.09% | 0 | 2 | 0 |
| Devign/Ablations/Plus-C6-graph-slicing/test_v2 | 2/2732 | 0.07% | 0 | 2 | 0 |
| Reveal/Ablations/No-C6-graph-slicing/test_v2 | 1/2274 | 0.04% | 0 | 1 | 0 |
| Devign/Ablations/No-C7-security-cot/test_v2 | 1/2732 | 0.04% | 0 | 0 | 1 |

## Một số bằng chứng cụ thể

- Devign Plus-C8: target devign:test:83 lưu raw_response rỗng, request_error=null, status=ok, attempts=2. Tổng arm này có1.237 ca rỗng không request_error và14 ca429.
- Devign Plus-C8: target devign:test:9246 lưu ClientError("429 RESOURCE_EXHAUSTED ... Resource exhausted. Please try again later ..."), attempts=5, status=invalid_exhausted.
- Devign No-C7: devign:test:18523 kết thúc bằng “4. The `h_size` calculation and adjustment”, không có nhãn cuối.
- Devign Plus-C2: devign:test:15962 kết thúc bằng “But examining the pattern more closely, the non-vulnerable”, không có nhãn cuối.

## Ý nghĩa đối với bảng kết quả

N0/N1 vẫn là toàn cohort, nhưng metric valid-only dùng ít mẫu hơn. Ví dụ Reveal Plus-C7 cóN0/N1=2.044/230, trong khi phần valid chỉ có1.007/109;1.037 safe và121 vulnerable bị invalid. Không thể đọc metric của arm này như chất lượng trên đủ2.274 mẫu hoặc xếp hạng trực tiếp với arm valid100%.

Phần cần bổ sung để tìm nguyên nhân gốc: giữ provider response metadata/finish reason/usage/candidate parts đã loại dữ liệu nhạy cảm, ghi từng attempt, tách request_status khỏi response/parse_status, và áp dụng policy retry nội dung rỗng có giới hạn đã chốt trước. Mọi lần retry tạo phản hồi mới phải có phiên bản artifact riêng; không nhận là chỉ re-parse. Raw rỗng không có thông tin để khôi phục nhãn bằng parser.

Bằng chứng máy đọc: [invalid_36_runs_audit_20261020.json](D:/JUNIOR/LabThayTho/REPORT_TO_TEACHER/invalid_36_runs_audit_20261020.json).
