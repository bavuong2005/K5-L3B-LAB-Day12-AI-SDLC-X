# Changelog

## Unreleased

### Phase 4
- `contract_version` là `"1.3"`. Gameplay và schema kho giữ v1.2 (cá thể). `bench_cmd` và `soak_cmd` đọc version này.
- File kho đếm đưa vào headless/live trả mã 2. Mẫu đang chạy: `docs/contracts/inventory.sample.json`.

### Phase 3
- **Breaking change (đã bật):** từ `"1.2"` (và `"1.3"`), file kho là `{"items":[{"id","kind","fresh"}]}`. Kho đếm trả mã 2.
- `Session` / headless / live / soak / bench truyền `contract_version` vào GatherSim và DaySim, nên giỏ và bàn giao quán đi theo schema của file contract.
- Quán bắt đầu nấu kho cá thể thì truyền `base_price = floor(giá × fresh trung bình / 100)`. Trước đó `step` gọi `start_cooking` không kèm giá nên món không bao giờ vào bếp.
- Fixture cũ: mỗi món đếm thành một cá thể `fresh: 100`, id `I1`, `I2`, … không trùng. Contract 1.0/1.1 (fixture `CHONOI_CONTRACT`) vẫn dùng kho đếm.
- `tuning.freshness`: initial 100, giỏ −0.5/s, quán −0.25/s, ươn khi fresh < 30. Nội bộ 240 đơn vị/điểm.

### Phase 2
- Contract `"1.1"`: số chuẩn, 6 món, cá bơi/sinh, kế hoạch D1–D5, shop, Cá Sấu trong tuning.

### Phase 1
- Khung headless gather/quan, kho đếm, smoke Test Contract.
