# Các điểm cần đối chiếu và hoàn thiện hồ sơ Dũng–Hiếu

**Cập nhật 24/10/2026.** Phụ lục của [báo cáo chung](bao_cao_chung_Dung_Hieu_gui_thay.md). Nội dung về Hiếu chỉ căn cứ [báo cáo chính thức ngày 22/10/2026](https://github.com/HuuHieu03/GRACE/blob/5987486641fe1db799d472f0ba6ed509c3b601ad/00_Reports_and_Docs/BAO_CAO_TIEN_DO_NGHIEM_THU_GRACE_20261022.md). “Chưa trình bày” chỉ phạm vi tài liệu này, không khẳng định người thực hiện chưa làm.

| Mục | Thông tin hiện có | Phần cần đối chiếu / bổ sung |
|---|---|---|
| Metric/evaluator | Dũng có evaluator, hai đối chứng hằng và bảng ghép cohort 6 arm mixed. Hiếu có metric, đối chứng hằng và CI tại Bảng 1.1. | Xác nhận entrypoint và quy ước metric không xác định dùng chung khi so trực tiếp; nguồn Hiếu chưa mô tả chi tiết này. |
| Cấu hình so sánh | Dũng ghi Qwen/Vertex, context 8192 byte UTF-8. Hiếu ghi Qwen/Vertex, temperature 0, seed 42, max_tokens 256, context 8192 tokens và graph tối đa 25/25. | Đối chiếu model, target, retrieval, inference params, context/truncation và evaluator cho từng phép so sánh chung. Làm rõ đơn vị budget. |
| ID và độc lập dữ liệu | Hiếu báo cáo split sạch, manifest UID v2 và sửa mapping 50 target ReVeal (Phần 5). | Nếu dùng chung dữ liệu, cần hồ sơ ID/code hash/nhãn và kết quả kiểm overlap. Báo cáo không cung cấp số đếm overlap/near-clone để kết luận cho hai pipeline. |
| Parser/checkpoint/lấy mẫu | Hiếu báo cáo sửa parser regex, invalid 0% trên các run trong Bảng 1.1; Dũng có phân rã invalid từng run. | Báo cáo Hiếu chưa nêu số nhãn đổi khi reparse, cơ chế checkpoint/resume, tham số train/test riêng hoặc thống kê nhánh bổ sung ứng viên. Bổ sung mô tả/bằng chứng nếu cần nghiệm thu các mục này. |
| Cohort và CI của Dũng | Đã ghép ID hợp lệ, tính metric và đối chứng hằng cho 6 arm mixed; JSON có danh sách ID và metric điểm. | Bổ sung CI/McNemar nếu chọn cặp V1/V2 để xác nhận cải thiện, từ output đã lưu. |
| CI của Hiếu | Bảng 1.1 ghi CI ΔF1 B3–B2 dương, CI ΔMCC chứa 0; Bảng 3.1 ghi CI Full–NoDiff chứa 0. | Phân biệt tăng F1/recall với cải thiện khả năng phân biệt; khi gửi hồ sơ từng mẫu, kèm dữ liệu hai arm dùng cho phép ghép cặp. |
| Retrieval 100 mẫu | Phần 4 ghi 50 Devign + 50 ReVeal, mỗi tập 25/25; đồng thuận 24/50 mỗi tập, Kappa 0,3151 và 0,3271. Phần 5 ghi sửa mapping ReVeal. | Gửi kèm phiếu, bảng đối soát và mapping mà báo cáo chính thức dẫn để thầy có thể đối chiếu. |
| Hướng tiếp theo của Dũng | Dũng đề xuất hoàn thiện H1/H2/H3; phương pháp, kết quả và đối chứng còn thiếu nằm trong [báo cáo riêng](bao-cao-cai-tien.md). | Xin ý kiến về ưu tiên, phạm vi và mốc nộp cho các hướng này. |
| Hướng tiếp theo của Hiếu | Phần 6 và kế hoạch cuối báo cáo đề xuất Gemini 1.5 Flash/Pro hoặc vLLM riêng; đánh giá test sau khi thầy phê duyệt kết quả development. | Trình thầy lựa chọn model/hạ tầng và kế hoạch test như Hiếu đã nêu; bổ sung dự toán cho phạm vi được đề xuất. |

## Nguồn

- [Báo cáo chính thức của Hiếu — nguồn duy nhất cho phần Hiếu](https://github.com/HuuHieu03/GRACE/blob/5987486641fe1db799d472f0ba6ed509c3b601ad/00_Reports_and_Docs/BAO_CAO_TIEN_DO_NGHIEM_THU_GRACE_20261022.md).
- [Ledger Dũng](https://github.com/kazunguyen/GRACE_runs_context/blob/33895c1cf4cb62eb0d40707bac8263ecaea0b444/bang_quan_ly_run.md), [JSON ghép cohort](https://github.com/kazunguyen/GRACE_runs_context/blob/bf632e82f3fd5901f659691c4187e34979673741/provenance/qwen_subset_paired_comparisons_20261023.json), [phân rã invalid](phan_tich_invalid_36_run.md).
