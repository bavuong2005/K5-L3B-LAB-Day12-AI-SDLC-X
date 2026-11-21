# NgMinPhuc — phản tư cá nhân (TV5 · QA lead + Harness AI)

- **Tôi đã làm:** P1: test luật, skill `pre-push-check`, ma trận AC (`16bb5ad`); sửa test bắt cá đủ chỗ cả đàn (`aa73b93`). P2: smoke kho và `day`, verification phase-2. P3–P4: test chấp nhận `tests/test_p{1,2,3}_acceptance.py`, `test_p4_runners.py`, skill `phase-proof`, verification 1–4, bench seed 42, soak 10 Ngày, thử clone sạch `v1.0.0`.
- **Đã giúp ai:** chạy test sau mỗi lần gộp; viết thêm test cho quán (TV3/TV4: hai bếp, ưu tiên tương tác, giá theo tươi + boa) và cho cá (TV1/TV2: bơi, sinh cá).
- **AI sai ở đâu:** so `fresh` bằng nhau giữa file kho và JSONL đã làm tròn (đề cho ±0.01); ngược dấu khi so 2 bếp; suýt ghi "đã báo TV1" khi chưa báo. Phát hiện nhờ traceback và đọc lại đề. Tôi sửa test, không sửa luật.
- **Bài học:** mỗi dòng verification phải trỏ tới lệnh chạy thật trên commit cụ thể. Bench đúng định dạng JSON chưa có nghĩa là đo đúng thứ đề muốn.
