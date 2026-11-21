# Tasks: Phase 1 lõi — gather + quan

**Input**: `specs/001-phase-1-core/` (spec, plan, data-model, contracts)
**Định dạng**: `[ID] [P?] [Story] [module] (người) Mô tả — file`
- `[P]`: làm song song được (khác file hoặc khác hàm, không phụ thuộc task chưa xong)
- module: `sim/gather` · `sim/quan` · `client/ui` · `qa` · người theo `TEAM.md` (TV1–TV6)
- Mốc theo `docs/plan/phase-1.md`: hợp đồng 0:15 · đóng băng tính năng 0:45 · tag < 1:00

## Phase 1: Setup / hợp đồng (0:00–0:15)

- [x] T001 [qa] (TV1) Sửa `team_size` = 6 trong `game.contract.json` (người được phép sửa file chung)
- [x] T002 [P] [qa] (TV1) Chốt `docs/contracts/` từ `specs/001-phase-1-core/contracts/events.md` + `sim-ui.md` (tên sự kiện, `data`, trường snapshot — đang là GIẢ ĐỊNH, Q-D)
- [ ] T003 [P] [qa] (TV6) [XONG một phần — TICKET-02 đã trả lời] PO đối chiếu `GIẢ ĐỊNH` #12–#21 trong `docs/clarify.md` + Q-A…Q-F (`docs/research/phase-1.md` mục 7) với PRD-0; sửa spec nếu khác

## Phase 2: Foundational (chặn mọi story)

- [x] T004 [sim/gather] (TV1) Thêm helper `_nearest(coll, radius)` (khóa `(dist, id)`) và `_add_to_hold(kind, count) -> bool` (tất cả hoặc không, ≤ `hold_capacity`) — `chonoi/sim/gather.py`
- [ ] T005 [P] [sim/quan] (TV3) Thêm `self.tick`, helper `_ticks(sec)` đọc `tick_hz`, `_clamp_rep()` (kẹp + `round(x,6)`), dựng khách từ scenario với tập trường cố định (`state`, `dish_id`, `patience_ticks_left`, `eat_ticks_left`, `reserved`) — `chonoi/sim/quan.py`
- [ ] T006 [P] [qa] (TV5) Tạo khung `tests/test_p1_rules.py` dùng `tests/helpers.py` (Workdir, run_headless, events, snapshots)

**Checkpoint**: helper xong (~0:25) → TV2, TV4 bắt đầu lát của mình.

## Phase 3: US1 — Lặn sinh tồn (P1) 🎯 MVP

- [x] T007 [US1] [sim/gather] (TV1) `_update_zone(was_surface)` → `dive`/`surface` {pos} — `chonoi/sim/gather.py`
- [x] T008 [US1] [sim/gather] (TV1) `_update_oxygen()` theo d cuối bước, kẹp, `oxygen_empty` — `chonoi/sim/gather.py`
- [x] T009 [US1] [sim/gather] (TV1) Ngạt (`zero_oxy_ticks` tính cả bước chạm 0, `choke` {hp}, reset khi oxy > 0 hoặc lên mặt nước — đã xác nhận bởi TICKET-02) + ngất (`faint`, `hold=[]`, `_finish("fainted")`, return) — `chonoi/sim/gather.py`
- [ ] T010 [P] [US1] [qa] (TV5) Test AC-P1-01…05 — `tests/test_p1_rules.py`

## Phase 4: US2 — Hái, bắt cá, giỏ LIFO (P1)

- [ ] T011 [US2] [sim/gather] (TV2) `_try_gather()`: chỉ mặt nước, nút `ready` gần nhất, `gather` {node_id, kind, count} / `hold_full`, đặt `regrow_ticks` — `chonoi/sim/gather.py`
- [ ] T012 [US2] [sim/gather] (TV2) `_try_catch()`: chỉ dưới nước + cd 0, `fish_caught` {fish_id, kind, count} / `hold_full`, đặt hồi chiêu khi thành công, đàn bị bắt bị loại (GIẢ ĐỊNH clarify #14) — `chonoi/sim/gather.py`
- [ ] T013 [P] [US2] [qa] (TV5) Test AC-P1-06…10 — `tests/test_p1_rules.py`

## Phase 5: US3 — Kết thúc buổi sáng, ghi kho (P1)

- [ ] T014 [US3] [sim/gather] (TV2) Rà thứ tự bước FR-012 (bến trước hái; faint dừng bước; chỉ một `gather_end`) — `chonoi/sim/gather.py`
- [ ] T015 [P] [US3] [qa] (TV5) Test AC-P1-11, AC-P1-12 (thêm ca fainted ghi kho `{}`) — `tests/test_p1_rules.py`

## Phase 6: US4 — Khách, kiên nhẫn, uy tín (P1)

- [ ] T016 [US4] [sim/quan] (TV3) `_cookable()` = món nấu được từ kho − giữ chỗ (sắp id) — `chonoi/sim/quan.py`
- [ ] T017 [US4] [sim/quan] (TV3) `_spawn_if_due()`: lịch `120 + 900·k` (đã xác nhận bởi TICKET-02), bàn trống id nhỏ, ghi `order_tick`, chọn món qua `self.rng.get("quan_order")`, `IdAllocator`, `customer_arrived` / `no_dish` / bỏ lượt khi hết bàn — `chonoi/sim/quan.py`
- [ ] T018 [US4] [sim/quan] (TV3) Kiên nhẫn giảm khi `waiting`; về 0 → `customer_left`, uy tín += delta (kẹp), nhả giữ chỗ chưa nấu — `chonoi/sim/quan.py`
- [ ] T019 [US4] [sim/quan] (TV3) Kiểm mâu thuẫn scenario mức luật (giữ chỗ vượt kho, `eating` thiếu price/tip, `hand` không phải món) → `BadInput` trong `QuanSim.__init__` (không sửa `scenario.py` nếu nhóm chưa đồng ý) — `chonoi/sim/quan.py`
- [ ] T020 [P] [US4] [qa] (TV5) Test AC-P1-14, 15, 16, 23 — `tests/test_p1_rules.py`

## Phase 7: US5 — Nấu, bưng, phục vụ, tiền, boa (P1)

- [ ] T021 [US5] [sim/quan] (TV4) `_tick_stoves()`: cooking → `dish_ready` — `chonoi/sim/quan.py`
- [ ] T022 [US5] [sim/quan] (TV4) `_interact()`: ứng viên hợp lệ trong `interact_radius`, khóa `(dist, bếp=0/bàn=1, id)`, tối đa một hành động: `cook_started` cho đơn reserved cũ nhất theo `order_tick` rồi id bàn (trừ kho, gắn `customer_id`) / `dish_picked` / `served` — `chonoi/sim/quan.py`
- [ ] T023 [US5] [sim/quan] (TV4) Ăn xong → `paid` {price, tip}; boa `floor(price·tip_rate)` (đã xác nhận bởi TICKET-02) khi tỉ lệ kiên nhẫn lúc served ≥ `tip_min_patience_ratio`, uy tín += `tip_reputation`; cộng `money/earned/shift_earned`; xóa khách — `chonoi/sim/quan.py`
- [ ] T024 [US5] [sim/quan] (TV4) Ghép thứ tự bước FR-022 trong `step()`; đóng ca (khách ăn trả ngay, khách chờ rời không trừ uy tín, dọn giữ chỗ) rồi `quan_end` dùng `shift_earned` — `chonoi/sim/quan.py`
- [ ] T025 [P] [US5] [qa] (TV5) Test AC-P1-17…21, AC-P1-24 — `tests/test_p1_rules.py`

## Phase 8: US6 — Nối ngày + tất định (P1)

- [ ] T026 [US6] [qa] (TV1 + TV5) Chạy chuỗi gather → `kho.json` → quan theo `quickstart.md`; lưu log vào `docs/proof/phase-1/`
- [ ] T027 [P] [US6] [qa] (TV5) Test AC-P1-13, AC-P1-22 (chạy 2 lần, so byte cả gather và quan) — `tests/test_p1_rules.py`
- [ ] T037 [P] [US6] [qa] (TV5) Lưu JSONL vàng (golden) cho 3–4 kịch bản P1 vào `tests/golden/p1/` + test so byte, để phase sau phát hiện hồi quy; khóa tên + `data` sự kiện đã chốt ở T002

## Phase 9: US7 — client/ui (P3) — giao worker Cursor, chủ: TV6

> Chỉ sửa `chonoi/web/` (và đọc `chonoi/live.py`). Chỉ đọc snapshot/event theo `contracts/sim-ui.md`; không chứa luật. Không đồ họa thật ở P1.

- [x] T028 [P] [US7] [client/ui] (TV6) HUD gather: oxy, Máu, `zero_oxy_ticks`/cảnh báo ngạt, giỏ 12 ô với món trên cùng (LIFO), hồi chiêu bắt — `chonoi/web/index.html`
- [x] T029 [P] [US7] [client/ui] (TV6) Vẽ nút (ready/đang mọc + đếm ngược) và đàn cá; vùng bến — `chonoi/web/index.html`
- [x] T030 [P] [US7] [client/ui] (TV6) HUD quan: khách (món, thanh kiên nhẫn, đang ăn), bếp (state, đếm ngược), tay, stock, tiền/`shift_earned`, uy tín — `chonoi/web/index.html`
- [x] T031 [P] [US7] [client/ui] (TV6) Nhật ký sự kiện: thêm `gather`, `fish_caught`, `node_regrown` vào danh sách hiển thị; nhãn tiếng Việt — `chonoi/web/index.html`
- [x] T032 [US7] [client/ui] (TV6) Kiểm tay bằng `python3 -m chonoi.live --mode gather|quan`, chụp ảnh vào `docs/proof/phase-1/`; `tests/test_live.py` vẫn xanh

## Phase 10: Polish / kiểm chứng (0:45–1:00)

- [ ] T033 [qa] (TV5) Điền `docs/verification/phase-1.md` (AC-P1-01…23 → test → kết quả trung thực)
- [ ] T034 [P] [qa] (TV5) Skill/hook #1 của nhóm ở `.agents/skills/` + cập nhật `AGENTS.md`
- [ ] T035 [P] [qa] (TV6) Gom `docs/ai-usage-log.md`, `docs/standup.md`; kiểm `git shortlog -sn` ở 0:50
- [x] T036 [qa] (TV1) Test xanh (TV5 báo) → gắn tag `phase-1`

## Phụ thuộc & song song

- T001–T003 song song. T004 → T007–T012; T005 → T016–T024.
- gather (TV1, TV2) ∥ quan (TV3, TV4) ∥ client/ui (TV6/Cursor) ∥ test (TV5).
- Trong cùng file: TV1 xong T004 trước để TV2 dùng; TV3 xong T005, T016 trước để TV4 dùng.
- T026–T027, T037 cần US1–US5; T033, T036 cuối cùng.

## Chiến lược

MVP = US1 + US3 (gather sống sót + ghi kho) → US2 → US4 → US5 → US6. Hết 0:45 ngừng thêm tính năng; AC chưa đạt ghi trung thực.
