# TV4 — T462 · Cháy món · 2111

Kiểm tra trên cây làm việc nhánh `mai-le-ba-vuong`, commit nền `ce47266`.

- `CookingWithFreshStock.test_burn_boundary_and_re_reservation` kiểm món vẫn bưng được ở tick 1200, cháy ở tick 1201, bếp rảnh và đơn chuyển sang `reserved` hoặc `unfulfillable` tùy kho.
- Lệnh `.agents/skills/pre-push-check/check.sh`: 173 test, OK (4 bỏ qua). JSONL hai mode giống từng byte khi chạy lại cùng seed. Tick âm trả mã 2.
