# Bench notes (TICKET-04, Phase 4)

Lệnh: `python3 -m chonoi.bench --seed 42 --duration 30 --out docs/proof/phase-4/bench.json` (mặc định `--mode auto` = browser nếu có Chrome).

## Kết quả thật (bench.json, chế độ browser)

```json
{"avg_fps": 86.89, "p1_low_fps": 33.75, "frames": 2607, "measured_s": 30.0039, "load_ms": 1009}
```

Đạt mốc báo cáo (avg >= 60, 1% low >= 30, load <= 10 s) nhưng biên hẹp hơn nhiều so với trước.

Số cũ (3313 fps / 1% low 387) là trước khi gắn lớp art PixiJS (nhân vật, môi trường nhiều lớp, FX bằng `art/characters.js` + `art/environment.js`). Từ giờ cảnh gather thật sự dựng WebGL (headless dùng render phần mềm SwiftShader), nên con số giảm còn ~85 fps. 5 lần chạy cùng máy: avg 82.9 / 83.9 / 86.4 / 86.9 / 87.9, 1% low 24.0 / 33.8 / 34.8 / 42.5 / 49.3; 1% low dao động theo tải máy (có lần 24 khi máy đang bận). Trên GPU thật số cao hơn nhiều. Mốc chỉ để báo cáo.

## Phương pháp

- Dựng `chonoi.live` (cổng ngẫu nhiên) với cảnh gather: contract hiện hành (có độ tươi 100%), seed 42, Út Sen đứng yên ở bến [2,0], 6 cá, 4 nút, Cá Sấu Năm Chèo M1 tuần tra [60,24]<->[64,24] (cùng bộ cảnh với `tests/fixtures/scenario-gather-bench-t411.json`).
- Mở ứng dụng web thật `chonoi/web/index.html` (PixiJS: lớp art nền/nhân vật/FX, canvas 2D chồng lên chỉ vẽ HUD) trong Chrome headless (`--headless=new`) qua Chrome DevTools Protocol bằng client WebSocket stdlib; cửa sổ 1280x720, DPR 1 (được kiểm lại trước khi đo). Gọi `startFromMenu()` của trang thay cho bấm nút "Chơi".
- Tắt vsync/giới hạn khung hình (`--disable-gpu-vsync --disable-frame-rate-limit`). Nếu không, headless bị khóa ~60 Hz và con số vô nghĩa.
- Làm nóng 3 s, đo 30 s. Mỗi lần `requestAnimationFrame` ghi `t`; `frames` = số khoảng giữa các lần, `measured_s` = tổng khoảng, `avg_fps = frames/measured_s`, `p1_low_fps` = nghịch đảo thời gian TB của `max(1,ceil(0.01*frames))` khung chậm nhất.
- `load_ms` = từ lúc bắt đầu dựng máy chủ + mở Chrome đến khung gather đầu tiên có snapshot.
- Ảnh khung đo cũ `bench-frame.png` là bản trước khi có art; ảnh cảnh mới nằm ở `docs/proof/phase-4/art/game-*.png`.

## Giới hạn (nói thẳng)

- Đây là thời gian giữa các khung của vòng vẽ thật trong headless Chrome không vsync, không phải số FPS trên màn hình người chơi. Headless không ghép hình ra màn hình, nên con số (hàng nghìn) cao hơn nhiều so với FPS người chơi thấy (bị khóa theo tần số quét, thường 60). Nó đo chi phí JS vẽ + ghi lệnh vẽ; chi phí raster/GPU có thể chưa tính hết. Số phụ thuộc máy (chạy trên macOS, Chrome của máy này; GPU/CPU không ghi lại).
- Bộ đếm FPS trong trang (góc dưới trái ảnh, EMA) là số riêng của trang, không dùng cho JSON.
- Không có Chrome: `--mode auto` rơi về `sim` và in cảnh báo ở stderr; số của sim KHÔNG phải render.

## bench-sim.json (chế độ sim, chỉ để đối chiếu)

`{"avg_fps": 14338, ...}`: chỉ bước `GatherSim` + tô bộ đệm byte CPU. Đây là số cũ (~12900) bị ghi nhận là không phải render; không dùng làm bằng chứng benchmark.

## Đề xuất sửa tài liệu (không tự sửa)

- `docs/verification/phase-4.md`: thay số bench cũ (~12900) bằng số bench.json mới + dẫn bench-notes.md, nêu rõ phương pháp headless Chrome và giới hạn trên.
- README: ghi `bench` cần Chrome/Chromium (hoặc `CHROME_BIN`); có `--mode sim` dự phòng.
