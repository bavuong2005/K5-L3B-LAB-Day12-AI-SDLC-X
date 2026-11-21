# Tasks: Phase 3 — kho cá thể + độ tươi (v1.2)

**Input**: `specs/003-freshness/` · Người theo bảng tác động `.lab-notes/brief-phase-2-3.html` ("Chia việc Phase 3").
**Định dạng**: `[ID] [P?] [Story] [module] (người) Mô tả — file` · module: `adapter` · `sim/gather` · `sim/quan` · `sim/day` · `client/ui` · `qa`
**Thứ tự**: Adapter/schema TRƯỚC → Lặn ∥ Quán ∥ HUD → day → bật v1.2 → regression + tag.

> ⚠️ Nền P1/P2 chưa xong (hái/bắt cá TODO, quán chưa nối `step`, `day` chưa chạy). Nếu phút 0–7 lõi P1 vẫn chưa xanh, giữ ưu tiên `specs/002-day-loop/tasks.md` nhóm P0 trước các task Quán/day dưới đây.

## Phase 0 — Phân tích tác động (phút 0–7)
- [x] T300 [qa] (TV6) Dẫn phân tích tác động; ghi quyết định schema v1.2, thứ tự tích hợp, cách chuyển (đọc 2 phiên bản, bật v1.2 khi hai đầu sẵn sàng) vào `docs/clarify.md` hoặc `docs/adr/0001-kho-ca-the.md`

## Phase 1 — Adapter / schema (làm trước, chặn mọi lát) — TV1 (+TV6 khung)
- [x] T301 [US1] [adapter] (TV1) `chonoi/inventory.py`: `read_inventory` chọn schema theo `contract_version`; v1.2: mảng cá thể, kiểm id duy nhất/khác rỗng, kind 6 loại, fresh hữu hạn [0,100]; kho đếm/sai → `BadInput` (mã 2)
- [x] T302 [US1] [adapter] (TV1) `write_inventory` v1.2: sắp theo id, fresh float đầy đủ, file tạm + `os.replace`; ngất → `{"items":[]}`
- [x] T303 [P] [US1] [adapter] (TV1) `chonoi/contract.py` validate `freshness {initial, gather_decay_per_s, quan_decay_per_s, spoiled_below}` + kiểm `decay×240/tick_hz` nguyên; `game.contract.json` thêm `freshness` (đổi `"1.2"` ở T340)
- [x] T304 [P] [US1] [adapter] (TV1) `docs/contracts/` mục v1.2 từ `specs/003-freshness/contracts/*.md`; báo nhóm schema đã chốt (handoff cho TV2/TV3/TV4/Cursor)
- [ ] T305 [US1] [adapter] (TV6, agent khung) `chonoi/scenario.py`: `gather.hold`, `quan.stock` mảng cá thể; `customers[].reserved` mảng id; id vật lý duy nhất giữa nơi chứa; reserved trỏ cá thể chưa ươn, đủ công thức, không dùng chung → sai mã 2
- [ ] T306 [P] [US1] [adapter] (TV6, agent khung) `chonoi/headless.py` + `runner.py`: đọc/ghi kho theo version; bộ cấp id cá thể `ItemIds` toàn cục truyền cho sim; `write_inventory_if_done` dùng v1.2
- [ ] T307 [P] [US1] [qa] (TV5) Test AC-P3-01…05 (kho đếm → 2, id trùng, fresh ngoài miền, ghi nguyên tử một lần, ngất rỗng, tick_limit giữ đích)

**Checkpoint (~phút 12)**: TV1 báo schema chốt → các lát dưới chạy song song.

## Phase 2 — Lặn — TV2 (+TV1)
- [ ] T310 [US2] [sim/gather] (TV2) Item `{id,kind,u}` trong `hold`; hái/bắt cấp `I<n>` qua `ItemIds`, `u = 100×240`, thêm sau bước hao (hao từ bước sau) — `chonoi/sim/gather.py`
- [ ] T311 [US2] [sim/gather] (TV2) Hao giỏ đầu bước (sau đồng hồ, cooldown, hồi nút): `u −= 2`/tick, kẹp 0; `spoiled {item_id,kind,location:"hold"}` khi qua 7200, theo id; pause không hao
- [ ] T312 [US2] [sim/gather] (TV2, pair TV1) LIFO cá thể: `monster_hit.lost`, ngất bỏ toàn bộ theo LIFO rồi `faint{lost}` → `gather_end(fainted)`; snapshot `hold` cá thể; `inventory_items()` trả mảng cá thể
- [ ] T313 [P] [US2] [qa] (TV5) Test AC-P3-06…10 (gồm scenario đề → `spoiled` tick 1)

## Phase 3 — Quán — TV3 (giữ chỗ) + TV4 (hao tươi, giá)
- [ ] T320 [US3] [sim/quan] (TV4) Hao kho quán `u −= 1`/tick kể cả hàng giữ; món chín không hao; pause không hao; `spoiled {location:"stock"}` theo id — đặt sau đồng hồ/timer — `chonoi/sim/quan.py`
- [ ] T321 [US3] [sim/quan] (TV3) `_reserve(order)`: mỗi kind lấy cá thể khả dụng tươi nhất, hòa id; `customers[].reserved` mảng id; khách chỉ chọn món nấu được từ hàng chưa ươn
- [ ] T322 [US3] [sim/quan] (TV3) Phần giữ vừa ươn: sau khi phát hết `spoiled`, gom đơn bị ảnh hưởng theo `(order_tick, table_id)`, nhả toàn bộ, `_reserve` đúng 1 lần; thiếu → `unfulfillable`, khách chờ tới hạn
- [ ] T323 [US3] [sim/quan] (TV4) Bắt đầu nấu: tiêu đúng id đang giữ, `base_price = floor(price·Σu/(n·240·100))`, `cook_started.data.items` sắp (kind, id); boa `floor(base_price × tip_rate)`; `paid` dùng giá chốt
- [ ] T324 [US3] [sim/quan] (TV3) Thứ tự tick quán theo đề (hao → spoiled → giữ chỗ ươn → món chín → di chuyển + 1 tương tác → thanh toán/kiên nhẫn/đóng ca → khách mới); giao đúng tick kiên nhẫn 0 / hết ca vẫn hợp lệ
- [ ] T325 [P] [US3] [qa] (TV5) Test AC-P3-11…17; đổi test boa/giá cũ (giá theo tươi) có lý do

## Phase 4 — day — TV6 (agent khung)
- [x] T330 [US4] [sim/day] (TV6) Bàn giao `gather_end → quan` cùng tick, không hao thêm, quán chạy từ bước sau — `chonoi/runner.py` / `chonoi/sim/day.py`
- [x] T331 [US4] [sim/day] (TV6) Id tăng xuyên Ngày; Ngày đầu giữ id mẫu `gather.hold`, Ngày kế cấp id mới theo thứ tự mảng (kind/fresh ban đầu); Shop `stock` cá thể không hao
- [ ] T332 [P] [US4] [qa] (TV5) Test AC-P3-19…21 (smoke day nhiều Ngày, pause/Shop không hao)

## Phase 5 — HUD — TV6 (Cursor), chỉ `chonoi/web/`
- [x] T335 [P] [US5] [client/ui] (TV6) Giỏ: thanh/số độ tươi từng cá thể, nhãn/biểu tượng "ươn" khi fresh < 30; kho quán (EveningIntro, HUD quán): số lượng tươi/ươn theo loại
- [x] T336 [P] [US5] [client/ui] (TV6) Nhật ký sự kiện: `spoiled` (tiếng Việt), `cook_started.items`, giá chốt trên `paid`; `tests/test_live.py` giữ xanh

## Phase 6 — Bật v1.2, QA, release (phút 20 và 25–32)
- [x] T340 [adapter] (TV1) Đổi schema đang chạy sang kho cá thể. File contract lên `"1.3"` (Phase 4): gameplay vẫn v1.2, `uses_individuals` bật từ 1.2.
- [ ] T341 [qa] (TV5) Phút 20: smoke bàn giao file của đề (fresh 100, interact frame 0, `quan --inventory --ticks 0`) → `docs/proof/phase-3/handoff.*` (AC-P3-18)
- [ ] T342 [qa] (TV5) Smoke 2 tiến trình + `day`; regression P1–P2 còn hiệu lực (AC-P3-22); tất định `cmp` (AC-P3-23)
- [ ] T343 [P] [qa] (TV5) `CHANGELOG.md`: breaking change kho cá thể, schema mới, cách cập nhật fixture (hold/stock/reserved/inventory); test đổi + lý do
- [ ] T344 [qa] (TV5) `docs/verification/phase-3.md` AC-P3-01…23 → bằng chứng → kết quả; skill nhóm #2
- [x] T345 [P] [qa] (TV6) Standup phút 20, retro (bài học đổi kho), `docs/ai-usage-log.md`, `docs/clarify.md`
- [x] T346 [qa] (TV1) Tag `phase-3` sau khi TV5 báo xanh (trước 2:30)

## Mở rộng P3 — tùy chọn, sau lõi
- `current` (dòng lũ), `reservations` (khách đặt trước): chỉ làm khi lõi độ tươi + bàn giao đã xanh; ưu tiên vẫn là `burn`, `snake` (đề xuất từ P2). Không có task bắt buộc ở phase này.

## Phụ thuộc & song song
- T300 → T301–T306. T301/T302 chặn T310–T312, T320–T323, T330–T331, T335.
- Sau checkpoint: Lặn (TV2) ∥ Quán (TV3 ∥ TV4, khác hàm) ∥ HUD (Cursor) ∥ test (TV5).
- T330–T331 cần T306 + T312 + T320. T340 sau khi hai đầu bàn giao xong. T346 cuối cùng.
- File dễ conflict: `gather.py` (TV2 + TV1), `quan.py` (TV3 + TV4) — mỗi người một hàm.
