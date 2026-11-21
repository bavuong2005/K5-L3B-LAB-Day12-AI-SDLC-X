# Quán Ăn Chợ Nổi v1.0.0

## Điểm mới
- Một vòng ngày: lặn, quán, shop, tạm dừng.
- Số liệu chuẩn Phase 2, cá bơi và sinh thêm, Cá Sấu.
- Contract `"1.3"`. Kho và gameplay theo v1.2: mỗi món là `{id, kind, fresh}`. Độ tươi ban đầu 100, giỏ hao 0.5/s, quán hao 0.25/s, ươn khi dưới 30.
- Lệnh đo: `python3 -m chonoi.bench --seed 42 --duration 30 --out bench.json`.
- Lệnh soak: `python3 -m chonoi.soak --seed 7 --days 10 --out soak.json`.

## Cách chạy
Python 3, không cài thêm gói.

```bash
git clone <fork-của-nhóm>
cd <fork-của-nhóm>
python3 -m chonoi.live --mode day
```

WASD di chuyển, E tương tác, Space bắt cá, Esc hoặc P tạm dừng, R chơi lại.

## Giới hạn đã biết
- File kho đếm (`{"items": {kind: số}}`) trả mã 2. Dùng mảng cá thể, mẫu ở `docs/contracts/inventory.sample.json`.
- `docs/verification` mới có phase 1. Phase 2–4 vẫn là việc của TV5.
- `extensions` vẫn rỗng. Repo starter không có `LICENSE`. Không có asset ngoài.
