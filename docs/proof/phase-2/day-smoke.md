# Smoke Day Phase 2

- `day --days 1 --seed 1 --ticks 22200`: exit 0, `reason=days_complete`, `days_completed=1`; thời gian thực **2.44 s** trên môi trường chạy lần này (ngưỡng AC-P2-30: ≤20 s).
- `day --days 2 --seed 1 --ticks 44400`: exit 0, `reason=days_complete`, `days_completed=2`.
- Chạy lại cùng lệnh Day 2 và `cmp` JSONL: byte giống nhau (AC-P2-29).
- Mua oxygen áp dụng từ Ngày kế tiếp, oxy tối đa 2700 tick: `tests/test_day_mode.py::DayLoopTest::test_shop_buy_and_next_day_upgrade` (đã pass trong unittest).

Unit test đầy đủ và kết quả deterministic / exit code sai đầu vào: [`pre-push-check.txt`](pre-push-check.txt).
