# Tasks: Phase 2 — day loop (Test Contract v1.1)

**Input**: `specs/002-day-loop/` + `specs/001-phase-1-core/` (đã sửa theo số chuẩn)
**Định dạng**: `[ID] [P?] [Story] [module] (người) Mô tả — file` · `[P]` = song song được · module `sim/gather` · `sim/quan` · `sim/day` · `client/ui` · `qa`
**Lịch đề §5**: 0–5 kế hoạch · 5–20 build 4 lát · 20 smoke tích hợp · 20–35 build + chốt day · 35–45 smoke day, regression, verification, tag · 45–50 retro.

## P0 — NỐT lõi P1 (ưu tiên cao nhất, chặn regression và test ẩn) ⚠️

> Hiện trạng: `gather.py` đã có lát 1 (oxy, ngạt, ngất, `try_add_hold`); hái/bắt cá và toàn bộ `quan.py` còn `TODO(nhóm)`. Làm theo `specs/001-phase-1-core/tasks.md` với số chuẩn.

- [x] T201 [US0] [sim/gather] (TV1) Rà lát 1 theo số chuẩn: ngạt tính cả bước chạm 0, reset khi oxy > 0 hoặc lên mặt nước; `faint` dừng bước — `chonoi/sim/gather.py` (≈ P1 T009)
- [x] T202 [US0] [sim/gather] (TV1) `_try_gather()` hái nút ở mặt nước, ≤ 2.0 m, hòa theo id, mọc lại 1200 tick; `gather` event (≈ P1 T011)
- [x] T203 [US0] [sim/gather] (TV1) `_try_catch()`: dưới nước, cd 0, gần nhất ≤ 2.0 m, **đủ chỗ cả đàn** (không dùng `try_add_hold` từng món → cần hàm thêm theo lô), loại đàn đã bắt, hồi 30 tick khi thành công; `fish_caught` (≈ P1 T012)
- [ ] T204 [P] [US0] [sim/quan] (TV3) Lõi khách: `self.tick`, lịch 120 + 900·k nếu có bàn trống, ghế id nhỏ nhất, chọn đều theo seed, giữ chỗ, `order_tick`, kiên nhẫn 3600, `customer_left` −0.5, `no_dish`, khách tập trường cố định (≈ P1 T005, T016–T019)
- [ ] T205 [US0] [sim/quan] (TV4) Lõi bếp/bàn: một interact/tick (dist, bếp trước bàn, id), bếp lấy đơn reserved cũ nhất theo `order_tick` rồi id bàn, `cook_started/dish_ready/dish_picked/served`, ăn 600 → `paid`, boa `floor(giá·0.2)` khi ≥ 50% lúc giao, uy tín +0.2 (≈ P1 T021–T023)
- [ ] T206 [US0] [sim/quan] (TV4) Đóng ca: khách đang ăn trả ngay, khách chờ rời không trừ uy tín, dọn món + giữ chỗ → `quan_end` (≈ P1 T024)
- [ ] T207 [P] [US0] [qa] (TV5) Test AC-P1-01…24 với số chuẩn — `tests/test_p1_rules.py`

## Lát (1) — TV1: số chuẩn v1.1 + cá bơi/sinh

- [x] T210 [US1] [qa] (TV1) `game.contract.json` v1.1: `contract_version`, 6 món, N5/N6, `fish_*`, `fish_yield` 3 loài, `gather.monsters`, B2/T2–T4, `day_plan` D1–D5, `shop`; `team_size` 6 — chặn mọi lát dùng số mới
- [x] T211 [P] [US1] [qa] (TV1) `chonoi/contract.py` validate v1.1 + `chonoi/inventory.py` 6 nguyên liệu (`ca_keo`, `keo_neo`) — file khung, báo nhóm
- [x] T212 [P] [US1] [qa] (TV1) `docs/contracts/` mục v1.1 từ `specs/002-day-loop/contracts/*.md` (dán JSON tuning đề xuất ở `docs/research/phase-2.md` §1.4)
- [x] T213 [US1] [sim/gather] (TV1) `chonoi/sim/fish.py`: 8 đàn đầu ca ở 8 điểm khác nhau (seed), bơi 1.5 m/s, đổi hướng bước 120·k trước khi bơi, phản xạ mép/góc, `age_ticks`
- [x] T214 [US1] [sim/gather] (TV1) Sinh cá tại `phase_tick = 360·k`: trần 12, clearance > 1 m, trọng số chuẩn hóa, `fish_spawned`, `IdAllocator`; `random_fish:false` tắt bơi/sinh
- [x] T215 [US1] [sim/gather] (TV1) Ghép vào `GatherSim.step` theo thứ tự v1.1 (bắt cá dùng vị trí trước bơi; cá bơi/sinh sau xét hết giờ)
- [ ] T216 [P] [US1] [qa] (TV5) Test AC-P2-01, 03–07

## Lát (2) — TV2: Cá Sấu, Máu, ngất, rơi LIFO

- [ ] T220 [US2] [sim/gather] (TV2) `chonoi/sim/monsters.py`: dựng từ `spawns[]` theo `from_day` (gather độc lập = Ngày 1) hoặc `scenario.gather.monsters[]`; patrol 1.0 (đổi waypoint bước sau), chase 3.0 khi d ≥ 10 & ≤ 10 m, thoát khi > 16 m hoặc d < 10; chặn biên + `depths`
- [ ] T221 [US2] [sim/gather] (TV2) Hit: sau khi cả hai di chuyển, ≤ 1.5 m, d ≥ 10, hết bất tử; tối đa 1 hit/bước (gần nhất, id); −1 Máu, rơi `floor(n·loss_ratio)` theo LIFO, `invuln_ticks = 90`, `monster_hit {monster_id,hp,lost,pos}`
- [ ] T222 [US2] [sim/gather] (TV2) Recoil 60 bước từ bước sau, 2/60 m/bước xa người chơi (trùng tâm +x), chặn mép, không hit → patrol
- [ ] T223 [US2] [sim/gather] (TV2) Máu 0 do hit → `faint {cause:"monster", lost:[giỏ còn lại], hp:0}` ngay sau `monster_hit` → `gather_end(fainted)` kho rỗng; snapshot `monsters[]`, `player.invuln_ticks`
- [ ] T224 [P] [US2] [qa] (TV5) Test AC-P2-08…14

## Lát (3) — TV3 + TV4: quán 2 bếp / 4 bàn / 6 món + day_plan (sau P0)

- [ ] T230 [US3] [sim/quan] (TV3) Bàn T1–T4, ghế trống id nhỏ nhất; menu 6 món từ dữ liệu; `QuanSim` nhận `plan_dishes` (None = quán riêng, cả 6 món); lọc menu theo kế hoạch **trước** lọc nguyên liệu
- [ ] T231 [P] [US3] [sim/quan] (TV4) 2 bếp nấu song song; interact chọn đúng bếp/bàn; đóng ca với nhiều bàn
- [ ] T232 [P] [US3] [qa] (TV3) Kiểm `day_plan.ingredients` = Σ công thức × suất (unit test trên contract)
- [ ] T233 [P] [US3] [qa] (TV5) Test AC-P2-16, 17

## Lát (4) — TV6 (+TV5): mode day, Shop, pause, sự kiện đổi pha

- [x] T240 [US4] [sim/day] (TV6) `chonoi/headless.py`: nhận `--mode day`, `--days` 1–5 (mặc định 1), mã 2 khi sai / dùng với mode khác / kèm `--inventory*` — file khung
- [x] T241 [P] [US4] [sim/day] (TV6) `chonoi/inputs.py`: nút `pause`, `shop_done` (bool, cạnh lên), `attack`/`photo` (bool, bỏ qua khi chưa bật mở rộng), `buy` (chuỗi, chỉ tại frame khai báo, không kế thừa) — file khung
- [x] T242 [P] [US4] [sim/day] (TV6) `chonoi/scenario.py`: khối `day {money,earned,reputation,upgrades,day_plan}`, `gather.monsters[]`, `fish[].age_ticks`, `player.invuln_ticks`; cấm `quan.stock`/`quan.reputation` trong `day`; `0 ≤ money ≤ earned` — file khung
- [x] T243 [US4] [sim/day] (TV6) `chonoi/sim/day.py` + `runner.py`: `DaySession`, `day_start → day_plan → phase_start(gather)`, `gather_end → phase_start(quan)` cùng tick (kho bộ nhớ, ngất → rỗng), `quan_end → phase_start(shop)`, snapshot đổi pha `phase_tick:0`, snapshot có `day, day_plan, upgrades, active_upgrades`, vỏ event thêm `"day":N`, `end.days_completed`, `reason:"days_complete"`
- [x] T244 [US4] [sim/day] (TV6) `chonoi/sim/shop.py`: `buy` trước `shop_done`, `bought`/`buy_failed{funds,max_level,unknown}`, 600 tick hoạt động → `shop_end(time)`, `shop_done` → `shop_end(done)`; đóng → `days_completed+1`, dựng Ngày kế, chép `upgrades → active_upgrades`, hồi oxy/Máu theo cấp, giỏ mới, bỏ kho dư
- [x] T245 [US4] [sim/day] (TV6, pair TV5) Pause trong `runner.py` (lớp bọc chung để gather/quan độc lập cũng pause): tách `tick`/`sim_tick`/`phase_tick`; `paused`/`resumed`; timer kể cả Shop đứng yên; snapshot `state:"paused"`
- [x] T248 [P] [US4] [sim/day] (TV6) `chonoi/live.py` (file khung): `--mode day`, `set_input` nhận `pause`/`shop_done`/`buy`, `meta` theo pha + `menu`, `day_plan`, `shop` — để UI Cursor chạy được
- [ ] T246 [P] [US4] [sim/gather] (TV2) `GatherSim`/`QuanSim` nhận ngữ cảnh Ngày: `oxygen_max`, `hp_max` theo `active_upgrades`; M2 từ Ngày 3
- [ ] T247 [P] [US4] [qa] (TV5) Test AC-P2-15, 18–28

## QA — TV5: contract v1.1, smoke tích hợp, regression P1

- [ ] T250 [qa] (TV5) Smoke tích hợp ở phút 20: `gather --inventory-out` → `quan --inventory`, so snapshot kho tick 0; lưu `docs/proof/phase-2/integration.{jsonl,md}` (AC-P2-31)
- [ ] T251 [qa] (TV5) Regression P1 với số chuẩn: chạy toàn bộ test (AC-P2-02). Sửa test cũ có lý do trong commit: `tests/test_smoke_p1.py:45` (6 → 8 đàn, đọc từ tuning), `:70-77` (bỏ `day` khỏi danh sách mã 2; thêm `--days 0/6` → 2); sửa `:65-67` và `tests/test_python_starter_units.py:46-50` (`attack` chưa bật → bỏ qua, mã 0 — đề §4.2); `test_session_steps_gather_and_dock` nếu đổi bộ đếm tick
- [ ] T252 [P] [qa] (TV5) Smoke `day --days 1` + đo thời gian ≤ 20 s; `day --days 2` mua oxy → Ngày 2 oxy max 2700; `cmp` tất định (AC-P2-23, 25, 29, 30) → `docs/proof/phase-2/`
- [ ] T253 [qa] (TV5) `docs/verification/phase-2.md`: AC-P2-01…31 → test → kết quả trên commit bàn giao
- [x] T254 [P] [qa] (TV6) Cập nhật `docs/clarify.md` (theo dõi #30, #32, #33 còn GIẢ ĐỊNH), `docs/ai-usage-log.md`, `docs/retro.md` (phút 45–50)
- [x] T255 [qa] (TV1) Gắn tag `phase-2` sau khi TV5 báo xanh (trước 1:55)

## Client/UI — worker Cursor (chủ TV6), chỉ `chonoi/web/` (+ đọc `chonoi/live.py`)

> Chỉ đọc snapshot/event; không chứa luật; tắt ở headless. Chữ không chân ≥ 18 px ở 1280×720, ≥ 30 FPS. Phụ thuộc T248 (`live.py --mode day`); trước đó làm với fixture snapshot. Màn UI-only (Menu, DayIntro…) hiển thị theo `phase` + event `day_start`/`phase_start`/`shop_end`.

- [x] T260 [P] [US5] [client/ui] (TV6) Menu chính (Chơi / Thoát)
- [x] T261 [P] [US5] [client/ui] (TV6) DayIntro (Ngày + danh sách Má Tư đọc từ `day_plan`, tự chuyển 4 s hoặc phím), EveningIntro (số nhập kho, món nấu được), DayResult (phục vụ/bỏ đi, tiền, boa, Δ uy tín), Summary sau Ngày 5 (tổng tiền, điểm, uy tín, món bán chạy)
- [x] T262 [P] [US5] [client/ui] (TV6) Pause menu (Esc/P): làm mờ nền, Tiếp tục / Về menu; gửi `pause`
- [x] T263 [P] [US5] [client/ui] (TV6) Shop UI: 2 nâng cấp × 2 cấp, giá, cấp đã mua/đang áp dụng, nút mua (`buy`) và đóng (`shop_done`), đồng hồ 600 tick, thông báo `buy_failed`
- [x] T264 [P] [US5] [client/ui] (TV6) HUD sáng: Máu, oxy (< 25% đổi màu/nhấp nháy), thời gian (≤ 30 s đổi màu), độ sâu, giỏ theo loại, đã lấy/cần, hồi bắt, gợi ý hái/cập bến, "Thủy quái!" + viền tím khi Cá Sấu gần, "Hết hơi!"; vẽ Cá Sấu, cá kèo, N5/N6
- [x] T265 [P] [US5] [client/ui] (TV6) HUD quán: đồng hồ ca, tiền ca, uy tín, 4 bàn (món + kiên nhẫn < 25% đổi màu), 2 bếp (tiến độ/món chín), món đang cầm, kho khả dụng; tên 6 món
- [x] T266 [US5] [client/ui] (TV6) Kiểm tay 1 Ngày trên `chonoi.live`, đo FPS, ảnh vào `docs/proof/phase-2/`

## Mở rộng — đề xuất cho Phase 3 (không làm ở P2)

- `burn` (rẻ): `quan.burn_s = 20`; `ready_ticks > 1200` → bỏ món, nguyên liệu mất, thử giữ lại cho đơn (`reserved`/`unfulfillable`), `dish_burnt` — một người (TV4).
- `snake` (rẻ): loài `ran` + M3 [72,14]↔[76,14], d ∈ [8,20], detect 8, chase 3.5 — tái dùng `monsters.py` (TV2).

## Phụ thuộc & song song
- P0 (T201–T207) chạy ngay, song song với T210–T212.
- T210 (contract v1.1) chặn T213–T215, T220, T230, T243–T244.
- Lát 1 ∥ lát 2 ∥ lát 3 (sau P0 của TV3/TV4) ∥ lát 4 khung (T240–T242) ∥ UI.
- T243 cần sim con dựng được với ngữ cảnh Ngày (T246) và quán lọc kế hoạch (T230).
- File khung: mỗi file một chủ — `headless/inputs/scenario/runner/live` TV6, `contract/inventory` TV1; gộp thành commit "khung v1.1" qua Integrator; TV5 sửa test cũ cùng lúc.
- T250 ở phút 20 chỉ cần P0 + T211; T252–T253 cuối; T255 cuối cùng.

## Chiến lược
P0 trước hết (không có lõi P1 thì regression và mọi pha `day` đều sai). Sau phút 20: chốt day với fixture cố định. Phút 35 đóng băng tính năng; AC chưa đạt ghi trung thực.
