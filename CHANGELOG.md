# Changelog

## Unreleased

### Phase 4
- `chonoi.bench` (`--seed --duration --out`, làm nóng 3 s, 5 trường JSON) và `chonoi.soak` (`--seed --days --out`, `gather → quan → shop`, D1–D5 lặp Ngày 6–10). Tag `v1.0.0`.
- UI: cảnh báo chữ cho thủy quái gần, oxy sắp hết, khách sắp giận; tương phản cao (phím C); SFX WebAudio và phụ đề SFX (M/N).
- Mở rộng `burn` (món cháy sau 20 s trên bếp, TV4).
- `tools/package.py` tạo `dist/chonoi-v1.0.0.zip`. Bằng chứng ở `docs/proof/phase-4/`, ma trận ở `docs/verification/phase-4.md`.
- Mở rộng `leaderboard` (`chonoi/leaderboard.py`): cờ `--leaderboard/--player-name` (headless day) và `--export-leaderboard`. Mặc định không đổi.
- `contract_version` là `"1.3"`. Gameplay và schema kho giữ v1.2 (cá thể). `bench_cmd` và `soak_cmd` đọc version này.
- UI (TV6, sau 3:00): đồ họa PixiJS thủ tục (`chonoi/web/art/`), hướng dẫn trong game, cốt truyện (nhân vật "Trường con"), nhạc nền thủ tục, chế độ terminal `chonoi.play`; leaderboard hiện top 3 ở Tổng kết; sửa lỗi pause/Shop/giữ hàng/DayResult/Summary.
- `chonoi.bench` mặc định `--mode auto`: chạy client web thật trong Chrome headless (không có Chrome thì rơi về `sim`, không phải render).
- Test: 4 test skip lỗi thời viết lại; `PYTHONPATH=tests:. python3 -m unittest discover -s tests` → 265 test OK.
- File kho đếm đưa vào headless/live trả mã 2. Mẫu đang chạy: `docs/contracts/inventory.sample.json`.

### Phase 3
- **Breaking change (đã bật):** từ `"1.2"` (và `"1.3"`), file kho là `{"items":[{"id","kind","fresh"}]}`. Kho đếm trả mã 2.
- `Session` / headless / live / soak / bench truyền `contract_version` vào GatherSim và DaySim, nên giỏ và bàn giao quán đi theo schema của file contract.
- Giá lúc nấu kho cá thể do `start_cooking` của TV4 chốt (`floor(giá × fresh trung bình / 100)`). Mở rộng `burn` của TV4 nằm trong `extensions`.
- Fixture cũ: mỗi món đếm thành một cá thể `fresh: 100`, id `I1`, `I2`, … không trùng. Contract 1.0/1.1 (fixture `CHONOI_CONTRACT`) vẫn dùng kho đếm.
- `tuning.freshness`: initial 100, giỏ −0.5/s, quán −0.25/s, ươn khi fresh < 30. Nội bộ 240 đơn vị/điểm.

### Phase 2
- Contract `"1.1"`: số chuẩn, 6 món, cá bơi/sinh, kế hoạch D1–D5, shop, Cá Sấu trong tuning.

### Phase 1
- Khung headless gather/quan, kho đếm, smoke Test Contract.
