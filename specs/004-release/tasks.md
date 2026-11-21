# Tasks: Phase 4 — Phát hành v1.0.0 (Contract v1.3)

**Input**: [`docs/prd/phase-4-ticket-04.md`](../../docs/prd/phase-4-ticket-04.md) · Chia việc: [`brief.md`](../../brief.md) mục Phase 4.
**Định dạng**: `[ID] [P?] [Story] [module] (người) Mô tả — file`
**Module**: `bench` · `client/ui` · `packaging` · `soak` · `release` · `qa` · `retro`
**Hạn**: tag `phase-4` + GitHub Release `v1.0.0` trên `main` trước **3:00** (30 phút: 2:30–3:00).

> Lõi P4 **không** đổi gameplay v1.2 — chỉ thêm `contract_version:"1.3"`, `bench_cmd`, `soak_cmd`, cảnh báo/UI, đóng gói, verification, retro, demo. Mở rộng (`leaderboard`, phụ đề SFX, …) sau lõi.

## Phase 0 — Lên kế hoạch (phút 0)
- [x] T400 [release] (TV6) Chốt phân công P4 trên kênh nhóm (Đóng gói / Bench-QA / Release-Integrator / Điều phối retro); cập nhật standup 1 dòng — `docs/standup.md`

## Phase 1 — Contract v1.3 + bench (phút 0–15) — song song
- [x] T410 [US1] [bench] (TV1) `game.contract.json`: `contract_version:"1.3"`, khai `bench_cmd` + `soak_cmd` ở gốc; gameplay/tuning/kho/JSONL giữ v1.2 — `game.contract.json`, `chonoi/contract.py` nếu cần validate
- [ ] T411 [US1] [bench] (TV5 + TV2 hỗ trợ) Implement/runner `<bench_cmd> --seed <int> --duration <s> --out <bench.json>`: cảnh gather lõi (độ tươi, cá bơi, Cá Sấu, FX mặc định), Út Sen đứng yên ở bến, cửa sổ 1280×720, warm-up 3 s rồi đo 30 s; xuất đủ 5 trường `avg_fps`, `p1_low_fps`, `frames`, `measured_s`, `load_ms`
- [ ] T412 [P] [US1] [qa] (TV5) Chạy bench seed 42 → lưu `docs/proof/phase-4/bench.json` (+ log); ghi AC-P4-bench trong verification
- [x] T413 [P] [US1] [client/ui] (TV6) Cảnh báo chữ/biểu tượng: thủy quái gần, oxy sắp hết, khách sắp giận; thêm chế độ tương phản cao; chơi thử 3 cảnh báo — `chonoi/web/index.html`

## Phase 2 — Đóng gói + soak sẵn sàng (phút 0–15, song song Phase 1)
- [ ] T420 [US2] [packaging] (TV1 / Đóng gói) README: yêu cầu môi trường, điều khiển, lệnh test, headless, benchmark; từ clone sạch chạy UI **≤ 3 lệnh** (macOS/Linux)
- [ ] T421 [US2] [packaging] (TV1) Chuẩn bị artifact đóng gói đính kèm Release (zip/bundle chạy được)
- [ ] T422 [US2] [soak] (TV5) Implement/runner `<soak_cmd> --seed <int> --days <N> --out <soak.json>`: 1 tiến trình headless, mỗi Ngày `gather → quan → shop`, D1–D5 lặp Ngày 6–10; state tiền/uy tín/nâng cấp/id xuyên suốt; `soak.json` có `days,days_completed,crashes,results[],duration_s`; `results[]` có `day,earned,reputation,score` lúc Shop đóng
- [ ] T423 [P] [US2] [qa] (TV5) Smoke soak ngắn (vd. `--days 1` hoặc 2) + ghi cách giảng viên chạy 10 Ngày; **không** bắt buộc chạy đủ 10 Ngày trên máy nhóm nếu hết giờ — lệnh phải sẵn sàng

## Phase 3 — Verification + CHANGELOG (phút 15–25)
- [ ] T430 [qa] (TV5) Regression P1–P3 còn hiệu lực; lưu bằng chứng `docs/proof/phase-4/`
- [ ] T431 [qa] (TV5) `docs/verification/phase-4.md`: ma trận `AC-P4-xx → bằng chứng → kết quả` trên commit bàn giao
- [x] T432 [P] [release] (TV1) `CHANGELOG.md` theo từng phase; rà `CREDITS.md` + `LICENSE` (starter không có LICENSE, không thêm file giả)
- [x] T433 [P] [release] (TV6) Cập nhật `docs/clarify.md`, `docs/ai-usage-log.md` (P4)

## Phase 4 — Retro + members (phút 15–25)
- [x] T440 [retro] (TV6) Retro cuối: rà hành động P2 (đã làm chưa / vì sao); tốt / tệ; số liệu commit & token theo người; 1 lỗi AI + cách phát hiện; nếu làm lại đổi gì — `docs/retro.md`
- [ ] T441 [retro] (mọi người) `docs/members/<handle>.md` ≤ 200 từ: phần mình làm, đã giúp ai, AI sai ở đâu, bài học, dẫn commit — TV6 đã viết `docs/members/thanhhale288.md`; các handle khác tự điền
- [ ] T442 [P] [qa] (TV5) Standup phút 20: rà vướng, điều người xong sang hỗ trợ — `docs/standup.md`

## Phase 5 — Tag + Release (phút 25–30)
- [x] T450 [release] (TV1 Integrator) Kiểm commit bàn giao trên `main`; viết release notes (điểm mới, cách chạy, giới hạn) — `docs/release-notes-v1.0.0.md`
- [ ] T451 [release] (TV1) Gắn tag `phase-4` **và** GitHub Release `v1.0.0` cùng trỏ commit `main`; đính kèm bản đóng gói — **trước 3:00**
- [ ] T452 [P] [qa] (TV5) Xác nhận clone sạch / artifact Release chạy được; checklist DoD

## Phase 6 — Mở rộng (sau lõi, nếu còn giờ) — nhóm 6 cần ≥ 2 mục cả lab
- [ ] T460 [P] [ext] (tự nhận) `leaderboard` trong `extensions`: store top 10; `--export-leaderboard`; headless `day --leaderboard --player-name` ghi 1 mục khi `reason:"days_complete"` đủ 5 Ngày; thiếu cặp cờ / sai mode → mã 2; soak không ghi — test + README
- [x] T461 [P] [ext] (TV6/UI) Phụ đề SFX: hiện khi có SFX; chơi thử tắt tiếng — `chonoi/web/` + bằng chứng
- [ ] T462 [P] [ext] (TV2/TV4) Hoàn thiện mở rộng P2/P3 còn dở (`burn`, `snake`, …) + khai `extensions` + test

## Demo sau 3:00 (không chặn tag)
- [ ] T470 [release] (TV6 dẫn, cả nhóm) Demo trực tiếp **hoặc** video `.mp4` &lt; 5 phút: (1) chơi 1 Ngày Lặn→Quán→Shop (2) show test xanh (3) bằng chứng chia việc/đóng góp (4) mở ma trận `docs/verification/phase-4.md`

## Dependencies / song song

```text
T400
 ├─ T410 (TV1) ─┬─ T411/T412 (bench) ∥ T413 (UI cảnh báo)
 │              └─ T422/T423 (soak)
 ├─ T420/T421 (đóng gói) ∥ trên
 └─ phút 15+: T430–T433 ∥ T440–T442 → T450–T452 → (T460+) → T470
```

## DoD nhanh (TICKET-04)

- [ ] `bench_cmd` tạo `bench.json` đúng 5 trường; `soak_cmd` sẵn sàng
- [ ] Clone sạch ≤ 3 lệnh; 3 cảnh báo + tương phản cao
- [ ] Regression P1–P3 xanh; verification + proof khớp tag
- [ ] CHANGELOG + release notes + artifact; `phase-4` + `v1.0.0` trên `main` ≤ 3:00
- [ ] Retro P2 đã rà; members đủ người; mở rộng (nếu có) có test/bằng chứng
