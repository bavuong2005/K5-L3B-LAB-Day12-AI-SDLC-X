# Bench notes (TICKET-04, Phase 4)

Lệnh: `python3 -m chonoi.bench --seed 42 --duration 30 --out docs/proof/phase-4/bench.json` (mặc định `--mode auto` = browser nếu có Chrome).

## Kết quả thật (bench.json, chế độ browser)

```json
{"avg_fps": 313.38, "p1_low_fps": 184.61, "frames": 9404, "measured_s": 30.0083, "load_ms": 1161}
```

Đạt mốc báo cáo (avg >= 60, 1% low >= 30, load <= 10 s). Ba lần chạy cùng máy (seed 42, 30 s, máy đang bận do nhiều tiến trình khác): avg 313.4 / 313.5 / 314.0, 1% low 184.6 / 176.4 / 176.8. Lần 1 được lưu làm `bench.json`. Trước khi tối ưu lô vẽ (xem dưới) cùng máy ra avg 67.4, 1% low 26.9 (dưới mốc 30).

Nguyên nhân chậm trước đó: các hình vẽ tay (cá, cây, nhân vật) mỗi hình hơn 100 điểm nên Pixi vẽ rời từng hình, phá gộp lô (~30 µs/hình, riêng nút + cá ~5 ms/khung). Sửa: `PIXI.GraphicsGeometry.BATCHABLE_SIZE = 1500` trong `artInit` (`chonoi/web/index.html`), thời gian khung từ ~14.6 ms xuống ~3.2 ms, hình giữ nguyên. Khi renderer là SwiftShader/llvmpipe, lớp art vẽ ở 75% độ phân giải (`?artscale=1` để tắt); bench dùng đường GPU nên không bị ảnh hưởng.

## Phương pháp

- Dựng `chonoi.live` (cổng ngẫu nhiên) với cảnh gather: contract hiện hành (có độ tươi 100%), seed 42, nhân vật chính đứng yên ở bến [2,0], 6 cá, 4 nút, Cá Sấu Năm Chèo M1 tuần tra [60,24]<->[64,24] (cùng bộ cảnh với `tests/fixtures/scenario-gather-bench-t411.json`).
- Mở ứng dụng web thật `chonoi/web/index.html` (PixiJS: lớp art nền/nhân vật/FX, canvas 2D chồng lên chỉ vẽ HUD) trong Chrome headless (`--headless=new`) qua Chrome DevTools Protocol bằng client WebSocket stdlib; cửa sổ 1280x720, DPR 1 (được kiểm lại trước khi đo). Gọi `startFromMenu()` của trang thay cho bấm nút "Chơi".
- Tắt vsync/giới hạn khung hình (`--disable-gpu-vsync --disable-frame-rate-limit`). Nếu không, headless bị khóa ~60 Hz và con số vô nghĩa.
- Làm nóng 3 s, đo 30 s. Mỗi lần `requestAnimationFrame` ghi `t`; `frames` = số khoảng giữa các lần, `measured_s` = tổng khoảng, `avg_fps = frames/measured_s`, `p1_low_fps` = nghịch đảo thời gian TB của `max(1,ceil(0.01*frames))` khung chậm nhất.
- `load_ms` = từ lúc bắt đầu dựng máy chủ + mở Chrome đến khung gather đầu tiên có snapshot.
- Ảnh cảnh thật của game: `docs/proof/phase-4/art/final-gather.png`.

## Giới hạn (nói thẳng)

- Đây là thời gian giữa các khung của vòng vẽ thật trong headless Chrome không vsync, không phải số FPS trên màn hình người chơi. Headless không ghép hình ra màn hình, nên con số (hàng nghìn) cao hơn nhiều so với FPS người chơi thấy (bị khóa theo tần số quét, thường 60). Nó đo chi phí JS vẽ + ghi lệnh vẽ; chi phí raster/GPU có thể chưa tính hết. Số phụ thuộc máy (chạy trên macOS, Chrome của máy này; GPU/CPU không ghi lại).
- Bộ đếm FPS trong trang (góc dưới trái ảnh, EMA) là số riêng của trang, không dùng cho JSON.
- Không có Chrome: `--mode auto` rơi về `sim` và in cảnh báo ở stderr; số của sim KHÔNG phải render.
