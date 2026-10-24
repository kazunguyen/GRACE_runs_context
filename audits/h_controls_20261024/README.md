# Hồ sơ đối soát bốn hướng H — 24/10/2026

- `audit_results.json`: metric, paired bootstrap 5000 lần/seed 42, exact McNemar, ca sửa đúng/làm sai và SHA-256 nguồn.
- `h3b_session_snapshot/`: lock, summary và prediction của gate_tuned/full_grace/gate_0_5; snapshot chỉ sao chép output có sẵn.
- `before_reports/`: bản báo cáo trước lần bổ sung; giữ nguyên byte để truy vết, còn link máy cá nhân lịch sử.
- `report_update_provenance.json`: checksum của lần cập nhật báo cáo trước đó, không phải chứng nhận các file đó chưa được sửa tiếp.
- `h3b_test_metrics_table.md`: bảng metric dùng khi biên tập.

Script: [audit_h_controls_20261024.py](../../tools/audit_h_controls_20261024.py). Script offline hiện cần các repo/dataset cục bộ ghi trong source registry; snapshot này phục vụ đọc và đối chiếu, không đóng gói toàn bộ model/data để train lại. Không có API key hoặc file .env trong hồ sơ.

Báo cáo chính: [đối soát bốn hướng H](../../bao_cao_doi_soat_4_huong_H_20261024.md).
