# Hợp đồng tích hợp

Chốt cho Phase 1. Đổi file này hoặc schema kho thì báo cả nhóm trước (ảnh hưởng gather, quán và UI).

## 1. Schema file kho (PRD-0 mục G)

Ghi **một lần** khi có `gather_end` (`--inventory-out`). Quán chỉ đọc (`--inventory`).

```json
{"items": {"bong_sung": 2, "ca_loc": 1}}
```

- Đúng một khóa gốc `items`.
- Khóa là id nguyên liệu: `ca_loc`, `ca_linh`, `ca_keo`, `bong_dien_dien`, `bong_sung`, `keo_neo` (hai id cuối là v1.1).
- Giá trị là số nguyên `>= 0`. Mục bằng 0 bị bỏ khi ghi. Số âm hoặc id lạ thì thoát mã 2.
- Mẫu đang chạy (contract 1.3, kho cá thể): `inventory.sample.json`. Bản đếm ở trên chỉ còn cho contract trước 1.2.
- Giỏ trong sim là mảng thứ tự nhặt (`hold`, phần tử cuối là mới nhất). Từ 1.2 mỗi phần tử là `{id, kind, fresh}`.

## 2. Giao diện sim ↔ UI

UI chỉ đọc snapshot (`GET /state`) và gửi lệnh (`POST /input`). Không tự tính oxy, Máu, giỏ.

Lệnh mỗi tick: `{"move": [x, y], "interact": bool, "catch": bool}`. `move` mỗi thành phần trong `[-1, 1]`. Gather: thành phần thứ hai dương là lặn xuống. `interact` và `catch` là cạnh lên (nhấn một lần, một tick).

Snapshot gather mà UI được đọc:

| Trường | Ý nghĩa |
|---|---|
| `player.pos` | `[x, d]` |
| `player.oxygen_ticks`, `player.oxygen_max_ticks` | oxy còn / tối đa |
| `player.hp`, `player.hp_max` | Máu |
| `player.at_surface` | `d <= surface_depth` |
| `player.zero_oxy_ticks` | số tick đã ngạt ở mốc hiện tại (0–59) |
| `hold`, `hold_count`, `hold_capacity` | giỏ, cuối mảng là món mới nhất |
| `nodes[]` | nút hái: `id`, `pos`, `kind`, `ready`, `regrow_ticks` |
| `fish[]` | đàn cá: `id`, `pos`, `kind`, `heading_deg`, `age_ticks` |
| `time_left_ticks`, `state`, `reason` | đồng hồ và kết thúc buổi |

## 3. Sự kiện gather

Mỗi sự kiện là `(tên, data)`. Runner gắn `tick` và `phase`.

| Tên | Khi nào | `data` | Ai phát |
|---|---|---|---|
| `dive` | từ mặt nước xuống dưới nước trong tick | `{"pos": [x, d]}` | lát 1 |
| `surface` | từ dưới nước lên mặt nước | `{"pos": [x, d]}` | lát 1 |
| `oxygen_empty` | oxy từ số dương xuống 0 | `{}` | lát 1 |
| `choke` | đủ `choke_interval_ticks` tick oxy = 0 dưới nước, trừ 1 Máu | `{"hp": <máu còn>}` | lát 1 |
| `faint` | Máu về 0; giỏ đã xóa | `{}` | lát 1 |
| `gather_end` | hết buổi | `{"reason": "docked"\|"time"\|"fainted", "inventory": {"items": {...}}}` | khung / lát 1 khi ngất |
| `hold_full` | `try_add_hold` khi giỏ đầy, món không được thêm | `{"kind": <id>}` | lát 1 (hàm giỏ); TV2 gọi |
| `node_regrown` | nút hết đếm mọc lại | `{"node_id": <id>}` | khung |
| `gather` | hái được một nút | TV2 chốt | lát 2 |
| `fish_caught` | bắt được cá | TV2 chốt | lát 2 |

Cách thêm vào giỏ, dành cho TV2: gọi `GatherSim.try_add_hold(kind, events)`. Hàm nối vào **cuối** `hold`. Trả `True` nếu thêm được. Đầy thì phát `hold_full` và trả `False`. Sức chứa là `hold_capacity` trong `game.contract.json` (12).

Ngất (`fainted`): xóa hết `hold` rồi mới `gather_end`, nên kho ghi ra là `{"items": {}}`.

Sự kiện quán (khách, bếp, tiền) do TV3/TV4 điền khi viết `quan.py`, theo PRD-0 mục E và F.

## 4. Contract v1.1 (Phase 2, TV1)

`game.contract.json` là `"1.1"`. `fish_initial` là số **8** (không còn danh sách đàn). Thêm N5/N6 `keo_neo`, `fish_yield.ca_keo` = 2, `day_plan` D1–D5, `shop` (oxygen/hp), `gather.monsters` (Cá Sấu — luật do TV2).

`random_fish: false` tắt cá mặc định, tắt bơi và tắt sinh; cá trong scenario đứng yên. Cờ bật mà có `fish` thì dùng đàn đó và vẫn bơi/sinh.

| Tên | `data` | Khi nào |
|---|---|---|
| `fish_spawned` | `{"id", "kind", "pos"}` | sinh theo lịch `phase_tick = 360·k`, không phát cho 8 đàn đầu ca |
| `faint` (ngạt) | `{"hp": 0, "lost": [giỏ còn lại]}` | Máu về 0 vì ngạt. Ngạt không rơi từng món và không nhìn bất tử |

Cá bơi 1.5 m/s trong `fish_x` × `fish_depths[loài]`. Đổi hướng khi `age_ticks` đã là bội của 120, trước khi nhích. Chạm mép thì phản xạ phần dư và đảo thành phần vuông góc; chạm góc đảo cả hai. Cá mới có `age_ticks` 0 và bơi từ bước sau.

## 5. Kho cá thể v1.2 (Phase 3, TV1) — đang chạy trên contract 1.3

`chonoi/inventory.py` chọn schema theo `contract_version`:

```json
{"items":[{"id":"I1","kind":"ca_linh","fresh":100},{"id":"I2","kind":"ca_loc","fresh":97.5}]}
```

Từ `"1.2"` (và `"1.3"`, gameplay vẫn theo v1.2): `items` phải là mảng. Kho đếm, id trùng hoặc rỗng, kind lạ, `fresh` không hữu hạn hoặc ngoài [0, 100] → mã 2. Kho rỗng là `{"items":[]}`. Ghi sắp theo id, `fresh` không làm tròn 3 chữ số, qua file tạm rồi `os.replace`.

Độ tươi nội bộ: 240 đơn vị mỗi điểm. Giỏ trừ 2 đơn vị/tick, quán trừ 1. Ươn khi đơn vị xuống dưới `30 × 240`. `tuning.freshness` trên contract hiện tại là `{initial:100, gather_decay_per_s:0.5, quan_decay_per_s:0.25, spoiled_below:30}`.

`game.contract.json` là `"1.3"`. Gameplay và schema kho theo v1.2 (cá thể). File kho đếm đưa vào headless/live trả mã 2. Contract 1.0/1.1 vẫn đọc kho đếm khi trỏ `CHONOI_CONTRACT` vào fixture cũ.
