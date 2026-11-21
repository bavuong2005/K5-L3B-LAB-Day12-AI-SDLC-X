# Bằng chứng `leaderboard` (mở rộng, TICKET-04 mục 3)

Chạy ngày 2026-11-21 trên cây làm việc nhánh `tv6/phase-1-team-ai` (HEAD `a5d5965` + thay đổi chưa commit), macOS, Python 3.13. Store riêng ở thư mục tạm, không đụng repo. Bot không input nên điểm đều 300 (mốc uy tín 3.0): hai mục hòa điểm, mục ghi trước đứng trước.

Mã thoát khi thiếu cờ đi cặp / sai mode là 2 (xem `tests/test_leaderboard.py::test_flag_errors_exit_2`; lệnh dưới in lý do, mã thoát kiểm bằng test).

```text
$ python3 -m chonoi.headless --mode day --days 5 --seed 42 --ticks 200000 --out out.jsonl --leaderboard lb.json --player-name "Út Sen"
exit 0
$ (lần 2) --seed 7 --player-name "Bé Tư"
exit 0
$ python3 -m chonoi.live --export-leaderboard top.json --leaderboard lb.json
exit 0
{"entries": [{"name": "Út Sen", "score": 300, "days_completed": 5, "seed": 42}, {"name": "Bé Tư", "score": 300, "days_completed": 5, "seed": 7}]}
$ chạy 3 Ngày (không đủ 5 Ngày) với cờ: không ghi mục mới
exit 0
2 mục
$ thiếu --player-name
đầu vào sai: --leaderboard và --player-name phải đi cặp
exit 2 (xác nhận bằng test)
$ sai mode (gather)
đầu vào sai: --leaderboard chỉ dùng với --mode day
exit 2 (xác nhận bằng test)
$ PYTHONPATH=tests:. python3 -m unittest tests.test_leaderboard -v
test_export_command_and_default_unchanged_without_flags ... ok
test_five_days_writes_exactly_one_entry ... ok
test_flag_errors_exit_2 ... ok
test_incomplete_run_or_other_days_writes_nothing ... ok
test_empty_name_and_bad_store_rejected ... ok
test_export_sorted_four_fields ... ok
test_sort_desc_ties_keep_insertion_order_after_reopen ... ok
test_top_10_only_and_unicode_name ... ok

----------------------------------------------------------------------
Ran 8 tests in 2.886s

OK
```

Khai báo: contract hiện có `extensions: ["burn"]`; cần TV1 thêm `"leaderboard"` (xem `docs/verification/phase-4.md` P4-16).
