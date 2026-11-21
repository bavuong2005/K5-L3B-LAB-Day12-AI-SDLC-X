# TV4 — kiểm chứng T323

Chạy trên cây làm việc nhánh `mai-le-ba-vuong`, commit nền `bcfaf6e`.

```powershell
$env:PYTHONPATH = 'tests;.'
python3 -m unittest test_quan_p3_freshness.CookingWithFreshStock -v
```

Kết quả: 1 test, OK. Bếp dùng đúng I2 đã giữ dù I1 tươi hơn. Giá 29 được chốt sau tick hao tươi và giữ nguyên đến lúc trả tiền.

`pre-push-check` trên cùng bản sửa luật trước khi thêm test trên: 171 test, OK (4 bỏ qua); JSONL gather và quan giống từng byte khi lặp cùng seed; ticks âm trả mã 2.
