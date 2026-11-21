---
name: qa-proof-run
description: Dựng bằng chứng QA cho một phase. Dùng khi điền docs/verification/phase-N.md hoặc trước khi báo "xanh" cho Integrator. Chạy smoke gather→quan→day, bench, soak, regression rồi lưu output thật vào docs/proof/phase-N/.
---

# qa-proof-run

Quy trình TV5 dùng ở P2–P4. Nguyên tắc: **chỉ ghi "đạt" khi có output thật đã lưu**; thiếu thì ghi "chưa kiểm".

## Các bước (chạy từ gốc repo)
1. **Regression**: `PYTHONPATH=tests:. python3 -m unittest discover -s tests -v > docs/proof/phase-N/regression.txt 2>&1`. Ghi số test, số `skipped` và liệt kê test skip (skip không phải đạt).
2. **Smoke 2 tiến trình** (AC kho): tạo scenario `{"gather":{"hold":[{"id":"I1","kind":"ca_linh","fresh":100}],"random_fish":false,"monsters":[]}}` và input `{"frames":[{"tick":0,"interact":true}]}`; chạy
   `python3 -m chonoi.headless --mode gather --seed 1 --ticks 600 --scenario … --inputs … --inventory-out inv.json --out g.jsonl`
   rồi `--mode quan --seed 1 --ticks 0 --inventory inv.json --out q.jsonl`. So id/kind/fresh của `stock` tick 0 với `inv.json` (snapshot làm tròn 3 chữ số). Thêm kho đếm `{"items":{"ca_loc":1}}` → phải exit 2 và không tạo `--out`.
3. **day**: `--mode day --seed 1 --days 1 --ticks 22200` (≤ 20 s), `--days 2` chạy hai lần rồi `cmp`; `--days 0|6` và `gather --days 1` → exit 2.
4. **Bench**: đọc `bench_cmd` trong `game.contract.json`, chạy `<bench_cmd> --seed 42 --duration 30 --out docs/proof/phase-4/bench.json`; kiểm đủ 5 trường `avg_fps, p1_low_fps, frames, measured_s, load_ms`.
5. **Soak**: `<soak_cmd> --seed 7 --days 1 --out …` (smoke) rồi `--days 10`; đạt khi `days_completed == days` và `crashes == 0`. Ghi rõ nếu bot đứng yên (`earned` = 0 thì không chứng minh tiền xuyên Ngày).
6. **pre-push-check**: `.agents/skills/pre-push-check/check.sh --save docs/proof/phase-N`.
7. **Ma trận**: `AC → bằng chứng (đường dẫn proof / tên test) → kết quả` trong `docs/verification/phase-N.md`. Phân biệt "LỆNH đã chạy" và "TEST ghép theo tên, chưa đọc assertion". Mỗi AC chưa kiểm ghi thẳng "chưa kiểm".

## Lưu ý
- Ghi kèm commit (`git rev-parse --short HEAD`), contract_version và ngày giờ vào đầu file proof.
- Đừng sửa test cho xanh; luật sai thì báo owner module. Đừng sửa `game.contract.json` / `docs/contracts/` (TV1).
- Khi cây chưa commit, nói rõ proof chạy trên cây nào so với tag.
