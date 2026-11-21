# Brief Phase 2 · 3 · 4 — chia việc theo người

> Người viết: TV6 (thanhhale288, PO · Scrum/Release). Cập nhật: 2026-11-21 — thêm **Phase 4 / TICKET-04** từ lab board.
> Đề đầy đủ (chép từ lab board để AI đọc được): [`docs/prd/phase-2-ticket-02.md`](docs/prd/phase-2-ticket-02.md), [`docs/prd/phase-3-ticket-03.md`](docs/prd/phase-3-ticket-03.md), [`docs/prd/phase-4-ticket-04.md`](docs/prd/phase-4-ticket-04.md).
> Spec & task: [`specs/002-day-loop/tasks.md`](specs/002-day-loop/tasks.md), [`specs/003-freshness/tasks.md`](specs/003-freshness/tasks.md), [`specs/004-release/tasks.md`](specs/004-release/tasks.md) (P4). Research: [`docs/research/phase-2.md`](docs/research/phase-2.md), [`docs/research/phase-3.md`](docs/research/phase-3.md). ADR kho: [`docs/adr/0001-kho-ca-the-v1-2.md`](docs/adr/0001-kho-ca-the-v1-2.md).
> Board: [Chợ Nổi Lab `#phase-4`](https://claude.ai/artifact/E35v787wSx2wDgPTNhMVDg#phase-4).

## Ai là ai

| Vai | Người (theo commit — **(suy luận)**, mỗi người tự điền `TEAM.md`) | Module |
|---|---|---|
| TV1 | thanhanbk02 | `sim/gather` lát 1, Integrator (contract, tag) |
| TV2 | Tăng Nguyễn Hải Đăng (`haidangwork1411`) | `sim/gather` lát 2 |
| TV3 | dqk2210 | `sim/quan` khách, giữ chỗ, uy tín |
| TV4 | noobpyno (`mai-le-ba-vuong`) | `sim/quan` bếp, bưng, tiền, boa |
| TV5 | (chưa rõ) | `qa`, QA lead |
| TV6 | thanhhale288 | `client/ui`, PO · Scrum/Release, khung `day` |

> ⚠️ `TEAM.md` mới có dòng TV6. Commit của người không có trong `TEAM.md` **không được tính** — mỗi người tự điền tên + handle ngay (`python3 tools/check_team.py`).

## Tóm tắt đề

**Phase 2 — TICKET-02 "Một ngày ở chợ nổi" (Contract v1.1, hạn tag `phase-2` 1:55).** Hai buổi thành một vòng Ngày: DayIntro → gather → EveningIntro → quan → DayResult → Shop. Số chuẩn mới (180 s mỗi buổi, oxy 30 s, Máu 3, giỏ 12, N1–N6, cá bơi 1.5 m/s và sinh thêm). Cá Sấu: chạm ≤ 1.5 m khi người chơi ở d ≥ 10 → −1 Máu, rơi một nửa giỏ theo LIFO, bất tử 90 tick. Quán 2 bếp, 4 bàn, 6 món; boa `floor(giá × 0.2)`; bếp lấy đơn theo `order_tick`. Mode mới `--mode day --days 1..5`, Shop nâng cấp oxygen/hp, pause.

**Phase 3 — TICKET-03 "Mùa Nước Nổi" (Contract v1.2, hạn tag `phase-3` 2:30) — đổi yêu cầu.** Kho thành **cá thể** `{"items":[{"id":"I1","kind":"ca_linh","fresh":100}]}`; kho đếm cũ → **mã 2**. Độ tươi: giỏ −0.5/s, kho quán −0.25/s, `fresh < 30` là ươn (vẫn chiếm ô, không nấu, phát `spoiled` đúng 1 lần). Giữ chỗ theo id (tươi nhất trước). Giá = `floor(giá × fresh trung bình / 100)`. Ghi file kho nguyên tử.

**Phase 4 — TICKET-04 "Phát hành v1.0.0" (Contract v1.3, hạn tag `phase-4` + Release `v1.0.0` 3:00).** 30 phút (2:30–3:00). Lõi: (1) **benchmark có render** — `<bench_cmd> --seed 42 --duration 30 --out bench.json`, cảnh gather (độ tươi + cá + Cá Sấu + FX), Út Sen đứng yên ở bến, 1280×720, warm-up 3 s / đo 30 s, JSON 5 trường `avg_fps,p1_low_fps,frames,measured_s,load_ms` (mốc kỹ thuật avg≥60 / 1%low≥30 / load≤10s); (2) **cảnh báo** chữ/icon: thủy quái gần, oxy sắp hết, khách sắp giận + chế độ tương phản cao; (3) **đóng gói** — clone sạch ≤ 3 lệnh, README đủ lệnh, artifact Release, `contract_version:"1.3"` + `bench_cmd`/`soak_cmd` ở gốc (gameplay vẫn v1.2). Soak (GV chạy): `<soak_cmd> --seed 7 --days 10 --out soak.json`, 10 Ngày headless `gather→quan→shop`, đạt khi `days_completed=days` và `crashes=0`. Mở rộng P4: `leaderboard`, phụ đề SFX (+ sáng tạo). Retro rà hành động P2; mỗi người `docs/members/<handle>.md`; demo sau 3:00 (&lt;5 phút).

**Mở rộng:** nhóm 6 người cần **≥ 2 mục** trong cả buổi lab, khai trong `extensions` + README. Đề xuất: `burn` (TV4), `snake` (TV2), `leaderboard` / phụ đề SFX (P4) — làm sau lõi.

## Hiện trạng `main` (`2fd94cf`, 60 test OK)

| Hạng mục | Tình trạng |
|---|---|
| Gather lát 1 + 2 | ✅ trên `main` (TV1 `4d2752c`, TV2 PR #2, #5) |
| Quán | 🟡 QuanSim (PR #1) đã gộp nhưng **chưa nối vào `step`**; `dqk2210/quan-validate` (TV3) và `mai-le-ba-vuong` (TV4) **chưa gộp** |
| Contract | 🔴 vẫn `"1.0"` → `--mode day` trả mã 2 "chờ TV1" |
| Mode `day`, Shop, pause, live day (TV6) | ✅ `2fd94cf` (chạy được ngay khi contract lên v1.1) |
| UI menu/màn ngày/Shop/pause/HUD + HUD độ tươi (TV6) | ✅ chờ dữ liệu sim thật |
| Tag | 🔴 **chưa có `phase-1`, `phase-2`** |

## Chia việc Phase 2 (ưu tiên: push code đang có, gắn tag đúng giờ, ghi trung thực)

### TV1 — thanhanbk02
- [ ] **Gắn `phase-1` ngay** (quá hạn), rồi `phase-2` trước 1:55 sau khi TV5 báo xanh.
- [x] T210/T211: dán JSON tuning v1.1 từ [`docs/research/phase-2.md`](docs/research/phase-2.md) vào `game.contract.json` (`contract_version:"1.1"`), cập nhật `contract.py`/`inventory.py` (thêm `ca_keo`, `keo_neo`, `fish_initial: 8`). **Việc này mở khóa mode `day`.**
- [x] Lát 1: số chuẩn + cá bơi/sinh (`fish_speed`, `fish_spawn_ticks` 360, trần 12).

### TV2 — haidangwork1411
- [x] Lát 2: Cá Sấu patrol/chase/recoil, hit, rơi LIFO `floor(n/2)`, bất tử 90 tick, ngất (`faint` có `cause:"monster"`, `lost`, `hp:0`) (`561c1d9`, PR #7).
- [x] T246: `GatherSim` nhận ngữ cảnh Ngày (`oxygen_max`, `hp_max` theo `active_upgrades`; M2 từ Ngày 3) (`561c1d9`, PR #7).
- [ ] (sau lõi) mở rộng `snake`.

### TV3 — dqk2210
- [ ] **Gộp `dqk2210/quan-validate` vào `main` ngay** (đụng `chonoi/scenario.py` mà TV6 cũng sửa — gộp sớm đỡ conflict).
- [ ] Nối luật khách vào `QuanSim.step`: lịch 120 + 900·k nếu có bàn trống, ghế trống id nhỏ nhất, kiên nhẫn 3.600 tick, `no_dish`, uy tín −0.5 khi bỏ đi.
- [ ] T230: lọc món theo `day_plan` (mode `day`), 4 bàn.

### TV4 — noobpyno
- [ ] **Gộp `mai-le-ba-vuong` vào `main`**, nối 4 hàm thao tác QuanSim vào `step`.
- [ ] 2 bếp, 6 món; bếp lấy đơn `reserved` cũ nhất theo `order_tick` rồi id bàn; boa `floor`, uy tín +0.2.
- [ ] (sau lõi) mở rộng `burn`.

### TV5 — QA lead
- [ ] T251: sửa test cũ vỡ khi contract lên v1.1, **ghi lý do trong commit**: `test_smoke_p1.py:45, :65-67, :70-77`, `test_python_starter_units.py:46-50`.
- [ ] Smoke tích hợp `gather --inventory-out → quan --inventory`, lưu `docs/proof/phase-2/integration.*`; smoke `day --days 1`.
- [ ] Điền `docs/verification/phase-2.md` (AC-P2-xx → bằng chứng → kết quả, trung thực).
- [ ] Skill nhóm tự viết #1 trong `.agents/skills/` (Spec Kit không tính).

### TV6 — thanhhale288
- [x] Spec 002, research P2, UI menu/DayIntro/EveningIntro/DayResult/Shop/Summary/pause/HUD (chữ ≥ 18 px).
- [x] Lát 4: mode `day`, Shop, pause, `live.py --mode day` (T240–T245, T248).
- [x] Retro nháp P2 (`docs/retro.md`), `docs/clarify.md` theo số chuẩn, nhật ký AI.
- [ ] Hỏi Anh Năm clarify #30, #32, #33.

## Chia việc Phase 3 (đổi kho sang cá thể + độ tươi)

**Phút 0–7, cả nhóm:** chốt [ADR-0001](docs/adr/0001-kho-ca-the-v1-2.md) — adapter trước, đọc được 2 phiên bản, bật `"1.2"` khi hai đầu sẵn sàng; độ tươi **số nguyên 240 đơn vị/điểm** (giỏ −2/tick, quán −1/tick; research đã chứng minh float ươn sớm 1 tick ở bước 8400 thay vì 8401). Ghi breaking change vào `CHANGELOG.md`.

**Thứ tự tích hợp:** (1) adapter + contract `freshness` → (2) Lặn, Quán, HUD song song → (3) `day` → (4) bật `"1.2"`, smoke, regression → tag.

| Module | File | Test | Người |
|---|---|---|---|
| Adapter / schema | `inventory.py`, `contract.py`, `game.contract.json` | kho đếm → mã 2, id trùng, `fresh` ngoài [0,100] | **TV1** |
| Adapter (khung) | `scenario.py`, `headless.py`, `runner.py` | ghi nguyên tử, bộ cấp id toàn cục | TV6 (agent khung) |
| Lặn | `sim/gather.py` | ngưỡng 30 (`spoiled` tick 1), LIFO cá thể | **TV2** (+TV1) |
| Quán — giữ chỗ | `sim/quan.py` | giữ theo id, thử giữ lại khi vừa ươn | **TV3** |
| Quán — hao tươi, giá | `sim/quan.py` | hao 0.25/s, `base_price` theo fresh | **TV4** |
| day | `runner.py`, `sim/day.py` | bàn giao cùng tick, id xuyên Ngày | TV6 (agent khung) |
| HUD | `chonoi/web/index.html` | `test_live.py` xanh | TV6 (Cursor) |
| QA | `tests/`, `docs/verification/phase-3.md`, `docs/proof/phase-3/`, `CHANGELOG.md` | regression P1–P2 | **TV5** |

### TV1
- [x] T301–T304: schema kho v1.2 trong `inventory.py` (đọc theo `contract_version`, kho đếm → mã 2), thêm `tuning.freshness` `{initial:100, gather_decay_per_s:0.5, quan_decay_per_s:0.25, spoiled_below:30}` (JSON sẵn trong [`docs/research/phase-3.md`](docs/research/phase-3.md)).
- [x] T340: gather và quán đã bàn giao cá thể. `Session` truyền `contract_version` vào sim. File contract lên `"1.3"` (schema kho vẫn v1.2).

### TV2
- [x] Cá thể trong giỏ, id `I1, I2…` tăng xuyên pha/Ngày; hao từ bước sau khi lấy; `spoiled` đúng 1 lần theo id (`0d156f2`, `27e7f99`, PR #11).
- [x] Rơi hàng/ngất theo LIFO cá thể; `lost` là mảng cá thể (`0d156f2`, `27e7f99`, PR #11).
- [x] Xong khi: `{"gather":{"hold":[{"id":"I1","kind":"ca_linh","fresh":30}],"random_fish":false,"monsters":[]}}` chạy 1 bước → `spoiled` ở tick 1 (`test_gather_phase3_freshness.py`, PR #11).

### TV3
- [ ] Giữ chỗ lấy cá thể tươi nhất (hòa theo id); `customers[].reserved` là mảng id.
- [ ] Phần giữ vừa ươn: nhả hết, thử giữ lại 1 lần (theo `order_tick` rồi id bàn), thiếu → `unfulfillable`.

### TV4
- [ ] Kho quán hao 0.25/s kể cả hàng đang giữ; pause dừng hao; món chín không hao.
- [ ] Bắt đầu nấu: tiêu đúng id đang giữ, `base_price = floor(giá × fresh TB / 100)`; boa trên giá đã chốt; `cook_started.data.items` sắp theo kind rồi id.

### TV5
- [ ] Test ngưỡng 30, thử giữ lại khi vừa ươn, chốt giá, bàn giao file (smoke của đề: `fresh:100`, `interact` frame 0, `quan --inventory <file> --ticks 0`).
- [ ] Phút 20: smoke kho; cuối: smoke 2 tiến trình + `day`, regression P1–P2; 8 test sẽ vỡ liệt kê trong research P3.
- [ ] `docs/verification/phase-3.md`, `docs/proof/phase-3/`, `CHANGELOG.md`; skill nhóm #2.

### TV6
- [x] Spec 003, research P3, ADR-0001 (bảng tác động), HUD độ tươi (T335), clarify #34–#45.
- [ ] Agent khung: T305, T306, T330, T331 (đang làm; không sửa `inventory.py` của TV1).
- [x] Cursor: T336 (nguyên liệu món đang nấu, giá chốt).
- [ ] Dẫn standup phút 20, retro bài học đổi kho, nhật ký AI.

## Chia việc Phase 4 (TICKET-04 — 2:30–3:00, ưu tiên tag + Release)

Chi tiết task: [`specs/004-release/tasks.md`](specs/004-release/tasks.md) · PRD: [`docs/prd/phase-4-ticket-04.md`](docs/prd/phase-4-ticket-04.md).

| Vai P4 (kiêm được) | Người gợi ý | Việc chính |
|---|---|---|
| Đóng gói | TV1 | Clone sạch ≤ 3 lệnh, README, artifact Release (T420–T421) |
| Bench/QA | TV5 (+TV2 hỗ trợ bench cảnh) | `bench_cmd` / `soak_cmd`, regression, `docs/verification/phase-4.md`, proof (T411–T412, T422–T423, T430–T431) |
| Release/Integrator | TV1 | `contract_version:"1.3"`, `bench_cmd`/`soak_cmd`, CHANGELOG, tag `phase-4` + Release `v1.0.0` (T410, T432, T450–T451) |
| Điều phối retro + UI + demo | TV6 | Cảnh báo + tương phản cao (T413); retro P2→P4 (T440); standup; demo (T470); clarify / ai-usage-log |

### TV1 — Integrator / Đóng gói / Release
- [x] T410: `contract_version:"1.3"`, `bench_cmd` và `soak_cmd` đã khai. Gameplay giữ v1.2.
- [x] T420: README (env, điều khiển, test, headless, bench); clone sạch UI ≤ 3 lệnh.
- [x] T421: gói nguồn chạy được `dist/chonoi-v1.0.0.zip` (giải nén rồi `python3 -m chonoi.live --mode day`).
- [x] T432, T450: CHANGELOG theo phase; CREDITS đã rà (không có LICENSE trong starter, không thêm file giả). Release notes: `docs/release-notes-v1.0.0.md`.
- [x] T451: tag `phase-1`…`phase-4` và Release [v1.0.0](https://github.com/bavuong2005/K5-L3B-LAB-Day12-AI-SDLC-X/releases/tag/v1.0.0) trên `89a035d`. Verification phase 2–4 vẫn của TV5.

### TV2 — hỗ trợ bench / mở rộng
- [x] Hỗ trợ TV5 dựng cảnh bench (gather + Cá Sấu + FX, player đứng yên ở bến) — fixture & test T411 (`94e9739`, PR #9).
- [ ] (sau lõi) T462: hoàn thiện mở rộng `snake` (hoặc mục đã chọn) + `extensions` + test.

### TV3 / TV4 — ổn định quán + mở rộng
- [ ] Giữ `quan` xanh trên `main` (regression P3); hỗ trợ smoke day nếu TV5 kêu.
- [ ] (sau lõi) T462: `burn` (TV4) hoặc mục đã chọn + bằng chứng.

### TV5 — Bench/QA / Soak
- [ ] T411–T412: implement/chạy bench → `docs/proof/phase-4/bench.json` (5 trường đúng công thức).
- [ ] T422–T423: `soak_cmd` sẵn sàng (đủ schema `soak.json`); smoke ngắn; GV sẽ chạy 10 Ngày.
- [ ] T430–T431, T442, T452: regression P1–P3; ma trận AC-P4; standup phút 20; xác nhận DoD trước khi TV1 gắn tag.

### TV6 — UI cảnh báo, retro, demo
- [x] T400: phân công P4 ghi trong brief + standup.
- [x] T413: cảnh báo thủy quái / oxy thấp / khách giận + tương phản cao (`?demo=warn`, `?demo=warnq`, phím C).
- [x] T433, T440: clarify #46 + ai-usage-log P4; retro cuối (rà hành động P2, shortlog, 1 lỗi AI).
- [x] T441 (riêng TV6): `docs/members/thanhhale288.md`.
- [ ] T470: dẫn demo (&lt;5 phút) hoặc video **sau 3:00** — chưa tới giờ.
- [x] T461: SFX + phụ đề SFX (`?demo=sfx`, M tắt âm, N tắt phụ đề).

### Mọi người
- [ ] T441: `docs/members/<handle>.md` ≤ 200 từ + dẫn commit.
- [ ] Có mặt phút 20 standup; hỗ trợ lát trễ khi đã xong phần mình.

### Lịch gợi ý trong 30 phút
| Phút | Việc |
|---|---|
| 0–15 | Bench + cảnh báo/tương phản + clone sạch + regression + chuẩn bị Release **song song** |
| 15–25 | Retro + members; phút 20 standup; pair smoke bản tích hợp |
| 25–30 | Chốt commit/artifact/tag/`v1.0.0` — hạn **3:00** |

## Điểm đồng bộ & git

- **Handoff P3:** TV1 chốt schema kho → TV2, TV3, TV4, TV6 mới đổi code theo schema.
- **Handoff P4:** TV5 báo bench + regression xanh → TV1 mới gắn `phase-4` / Release `v1.0.0`.
- **File dễ conflict:** `gather.py` (TV1 + TV2), `quan.py` (TV3 + TV4), `scenario.py` (TV3 + TV6), `game.contract.json` / README (TV1). Mỗi người một hàm riêng, `git pull --rebase` trước khi sửa, commit nhỏ, gộp branch sớm.
- **Chỉ TV1** sửa `game.contract.json`, `docs/contracts/` và gắn tag / công bố Release (sau khi TV5 báo xanh).
- **TV6 giữ** `docs/clarify.md`, `docs/standup.md`, `docs/ai-usage-log.md`, điều phối retro/demo. Câu hỏi đề gửi PO.
- **Mỗi người tự làm:** dòng của mình trong `TEAM.md`, `docs/members/<handle>.md`, ≥ 3 commit có nội dung bằng tài khoản của mình.

## Rủi ro & câu hỏi còn mở

- 🔴 Chưa có tag nào; contract còn v1.0 trên một số máy / cần lên v1.2 rồi v1.3 trước Release. Test ẩn kiểm lại phase trước.
- 🟡 P4 chỉ 30 phút — ưu tiên `bench_cmd` + đóng gói + tag/Release; mở rộng (`leaderboard`, SFX) chỉ sau lõi.
- 🟡 `load_ms` có trong ví dụ JSON board nhưng bảng công thức a11y chỉ nêu rõ 4 trường kia — implement theo 5 trường ví dụ; nếu lệch hỏi PO/#clarify.
- Hỏi Anh Năm: #30 (ngất do ngạt có `lost`/`hp`?), #32 (`extensions` mảng hay object), #33 (đàn bị bắt biến mất?), #34 (`freshness` ở `tuning` hay gốc), #37, #40, #42 — xem [`docs/clarify.md`](docs/clarify.md).
