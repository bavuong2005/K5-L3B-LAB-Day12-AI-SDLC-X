# Chơi trong terminal (`chonoi.play`)

Vỏ thứ ba của game, cạnh `headless` và `live`: chơi game thật ngay trong dòng lệnh, chỉ dùng thư viện chuẩn Python (curses). Dùng chung `chonoi/runner.py::Session`, không có luật riêng; chỉ đọc snapshot/event. Không đổi gì ở headless, JSONL hay `live`.

## Chạy

```bash
python3 -m chonoi.play --mode day                      # chơi 1 Ngày, seed 1
python3 -m chonoi.play --mode day --days 5 --seed 7    # đủ 5 Ngày
python3 -m chonoi.play --mode day --scenario sc.json   # scenario như headless
python3 -m chonoi.play --mode day --demo               # bot tự chơi vài giây (smoke test)
printf 'enter\nd 60\ns 90\ne\n' | python3 -m chonoi.play --mode day --text   # dòng lệnh, không cần TTY
```

Cần terminal tối thiểu 80x24 (nên 100x35), nên dùng UTF-8. Có curses và TTY thì chạy thời gian thực (60 tick/s, vẽ ~30 fps); không có (hoặc stdout bị chuyển hướng, hoặc `--text`) thì tự chuyển sang chế độ dòng lệnh. `--mode gather|quan` cũng chạy được (quan không có kho mặc định nên cần scenario có `quan.stock`).

| Cờ | Ý nghĩa |
|---|---|
| `--mode day\|gather\|quan` | mặc định `day` |
| `--seed N`, `--days 1-5`, `--scenario F` | như headless; sai đầu vào thoát mã 2 |
| `--demo [--demo-seconds S] [--speed X]` | bot tự chơi (mặc định 8 giây, tốc độ x12) |
| `--text [--ticks N]` | chế độ dòng lệnh; `--ticks` giới hạn tổng tick |
| `--ascii` | chỉ ký tự ASCII (tự bật nếu locale không phải UTF-8) |
| `--sticky` | hướng đi giữ tới khi bấm hướng khác hoặc `X` |

## Phím

| Phím | Tác dụng |
|---|---|
| `W A S D` / mũi tên | bơi (sáng) / đi (tối) |
| `E` | hái bông (ở mặt nước), cập bến; ở quán: nấu / lấy món / giao món |
| `Space` | bắt cá (sáng); tiếp tục ở màn chờ |
| `P` / `Esc` | tạm dừng, bấm lại để tiếp tục |
| `1`, `2` | mua nâng cấp trong Shop; `Enter`/`Space` = xong Shop |
| `Enter` / `Space` | qua màn chờ (mở đầu Ngày, mở quán, kết quả Ngày) |
| `R` | chơi lại, chỉ khi đã kết thúc |
| `H` | bật/tắt trợ giúp |
| `Q` | thoát (hỏi `Y`/`N`; ở màn tổng kết thoát luôn) |
| `X` | dừng hẳn (chỉ có ý nghĩa với `--sticky`) |

Terminal không báo nhả phím, nên mỗi lần bấm hướng giữ chuyển động khoảng 0,2 giây; giữ phím để đi liên tục (có thể hơi khựng lúc bắt đầu do độ trễ lặp phím của terminal), hoặc dùng `--sticky`.

## Cách phục vụ ở quán (dòng "BÂY GIỜ LÀM" bám đúng luật)

1. Đứng gần bếp trống (bán kính `interact_radius`), bấm `E`: nấu món của khách chờ lâu nhất (đơn "chờ nấu").
2. Món chín: đứng gần bếp đó, bấm `E` để bưng (tay chỉ cầm 1 món; để quá lâu sẽ cháy).
3. Đi tới đúng bàn của đơn đó, bấm `E` để giao; khách ăn xong trả tiền, boa nếu còn kiên nhẫn.

## Màn hình

Màn mở đầu Ngày (lời truyện lấy từ `chonoi/web/story.js` nếu đọc được, không thì dùng chữ riêng; nhân vật chính là Trường con):

```
          ┌─ NGÀY 1/1 — BUỔI SÁNG ──────────────────────────────────────────────────────┐
          │ Bà Tư: Trường con, dậy đi! Nắng lên tới ngọn dừa rồi.                       │
          │ ...                                                                         │
          │ Hôm nay quán bán: Cá lóc nướng trui x3, Gỏi bông súng x3                    │
          │ Cần mang về: cá lóc 3, bông súng 6                                          │
          │ Nhấn ENTER hoặc SPACE để bắt đầu.   (H: trợ giúp, Q: thoát)                 │
          └─────────────────────────────────────────────────────────────────────────────┘
```

Buổi sáng (nhìn ngang, thước độ sâu bên trái; `@` bạn, `><>` cá, `*` nút rau, `~Cá Sấu~`, `X` mục tiêu gợi ý; giỏ: `LI` cá linh, `LO` cá lóc, `KE` cá kèo, `DD` điên điển, `BS` bông súng, `KN` keo nèo, `+` tươi, `!` ươn):

```
 QUÁN ĂN CHỢ NỔI    · Ngày 1/1 · Buổi sáng — Lặn & Hái               Tiền 0đ  Uy tín 3.0★  Điểm 300
 Giờ 02:59   O2 [███████████████████░] 28.9s  HP ♥♥♥
 Giỏ 0/12       .   .   .   .   .   .   .   .   .   .   .   .
 Cần: cá lóc 0/3, bông súng 0/6
 BÂY GIỜ LÀM: Lặn tới đàn cá lóc F7 rồi bấm SPACE (xuống-phải, cách 14m)
  0m ~⌂bến~~~~~~❀~~~~~~~~~~~~~~❀~~~~~~~~~~~~~~❀~~~~~~~~~~~~~~❀~~~~~~~~~~~~~~❀~~~~~~~~~~~~❀~~~~~~~~~
       @
  5m ·   ·   ·   ·   ·   ·   ·   ·   ·   ·   ·   ·   ·   ·   ·   ·   ·   ·   ·   ·   ·   ·   ·
 10m ·   ·   ·  <X<  ·   ·   ·   ·   ·   ·  <><  ·   ·   ·   ·   ·   ·   ·   ·   ·   ·   ·   ·
 ...
 [00:01] Lặn xuống.
```

Buổi tối (nhìn từ trên: bàn T1-T4, bếp B1/B2, khách có món và thanh kiên nhẫn, `▼▼` chỉ chỗ cần tới):

```
 BÂY GIỜ LÀM: Chờ bếp B2 nấu xong (còn 5s); đứng gần bếp sẵn sàng lấy món.
 ┌── Ghe Quán ──────────────────────────────────────────────────────┐  ĐƠN KHÁCH
 │                                   [T1]            [T2]           │  T1 Lóc nướng
 │                                   ☺Lóc nướng      ☺Lóc nướng     │    đang ăn
 │                                   ăn █░░░░░       ████████       │  T2 Lóc nướng
 │                                                   chờ món        │    đã nấu/chờ món
 │       [B1]        [B@]                                           │
 │       nghỉ        nấu 5s                                         │
```

Sau quán: màn Kết quả Ngày, rồi Shop (số phím mua nâng cấp, đồng hồ Shop vẫn chạy theo contract), cuối cùng Tổng kết (điểm, `R` chơi lại, `Q` thoát). Capture thật từ pty: `docs/proof/phase-4/play-cli.txt`.

## Chế độ dòng lệnh (`--text`)

Mỗi dòng stdin là một lệnh, sau mỗi lệnh in một khung 100x35:

| Lệnh | Tác dụng |
|---|---|
| `w\|a\|s\|d [n]` | di chuyển n tick (mặc định 10) |
| `e`, `space` | bấm E / Space (1 tick) |
| `wait n` | đứng yên n tick |
| `enter` | qua màn chờ / xong Shop |
| `buy 1\|2\|oxygen\|hp`, `done` | mua nâng cấp / xong Shop |
| `p`, `h`, `r`, `q`, `bot [n]` | tạm dừng, trợ giúp, chơi lại (khi kết thúc), thoát, để bot chơi n tick |

`--ticks N` giới hạn tổng tick. Kèm `--demo` thì bot chơi cả Ngày và in khung mỗi `--every` tick.

## Giới hạn

- Bot demo chỉ để thử, không tối ưu.
- Không có âm thanh/đồ họa; màu phụ thuộc terminal (không có màu thì dùng đậm/đảo màu).
- Terminal nhỏ hơn 80x24 chỉ hiện thông báo yêu cầu phóng to.
- Chưa có bảng xếp hạng ở vỏ này (dùng `headless`/`live`).
