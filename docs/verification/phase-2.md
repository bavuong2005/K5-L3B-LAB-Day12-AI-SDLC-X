# Verification Phase 2 — Một ngày ở chợ nổi

> Lần 1: TV5 kiểm trên `cd1c523` (lúc đó chưa có tag `phase-2`). **Lần 2 (bản này):** kiểm lại trên `main` @ `a5d5965` (tag `phase-2` = `c5b427d`, `v1.0.0` = `89a035d`) và bổ sung `tests/test_p2_acceptance.py` cho các dòng trước đây còn "Một phần" hoặc "Chưa kiểm chứng".

## Ma trận AC

| AC | Kiểm chứng | Kết quả |
|---|---|---|
| AC-P2-01 | Contract v1.1; `test_day_plan_override`, CLI tests | Đạt |
| AC-P2-02 | Regression P1: [phase-1.md](phase-1.md), AC-P1-01…24 xanh; `test_tra_tien_theo_gia_menu` nay chạy (không còn skip) | Đạt |
| AC-P2-03 | `test_p2_acceptance…test_ac_p2_03_tick_0_co_8_dan_o_8_diem_khac_nhau_dung_dai` (seed 1, 2, 3, 42) | Đạt |
| AC-P2-04 | `test_ac_p2_04_boi_1_5_ms_doi_huong_moi_120_tick_va_o_trong_dai` (600 tick, có chạm mép) | Đạt |
| AC-P2-05 | `test_ac_p2_05_sinh_ca_moi_360_tick_tran_12_clearance` (4000 tick: 4 lần sinh, chạm trần 12) | Đạt |
| AC-P2-06 | `test_ac_p2_06_random_fish_false_dung_yen_khong_sinh` | Đạt |
| AC-P2-07 | `test_ac_p2_07_bat_dung_vi_tri_truoc_khi_boi_va_keo_yield_2` + `test_hold_full_contract_payload_and_atomic_fish_rejection` | Đạt |
| AC-P2-08 | `test_patrol_speed_1ms_and_waypoint_flip` | Đạt |
| AC-P2-09 | `test_chase_trigger_speed_and_exit_thresholds` | Đạt |
| AC-P2-10 | `test_hit_exact_boundary_lifo_odd_even_and_id_tiebreak` | Đạt |
| AC-P2-11 | `test_recoil_60_ticks_coincident_plus_x_and_invuln_90_ticks` | Đạt |
| AC-P2-12 | `test_recoil_60_ticks_coincident_plus_x_and_invuln_90_ticks` | Đạt |
| AC-P2-13 | `test_monster_faint_clears_hold_empty_inventory_and_choke_before_hit` | Đạt |
| AC-P2-14 | Monster faint test và gather integration tests | Đạt |
| AC-P2-15 | `test_t246_day_mode_m2_on_day_3_next_day_upgrades_and_determinism` | Đạt |
| AC-P2-16 | `test_quan_p2…test_khach_lan_luot_t1_den_t4_va_khach_thu_5_bi_bo_qua` + `test_p2_acceptance…test_ac_p2_16_hai_bep_nau_song_song` | Đạt |
| AC-P2-17 | `test_quan_p2…test_chi_go_mon_trong_ke_hoach_*`, `test_khong_plan_thi_lau_mam_duoc_chon_*`, `test_day_ke_hoach_lau_mam_*`, `test_day_plan_override` | Đạt |
| AC-P2-18 | `tests/test_day_mode.py` day start/plan/phase events | Đạt |
| AC-P2-19 | `test_dock_hands_inventory_to_quan_same_tick`, ngất trong day | Đạt |
| AC-P2-20 | Day loop và snapshot Shop tests | Đạt |
| AC-P2-21 | Snapshot pha mới và `phase_tick:0` trong day loop tests | Đạt |
| AC-P2-22 | `test_shop_buy_and_next_day_upgrade`, `test_max_level_and_buy_not_inherited` | Đạt |
| AC-P2-23 | `test_shop_buy_and_next_day_upgrade`, oxy Ngày kế = 2700 | Đạt |
| AC-P2-24 | `test_shop_done_on_last_step_is_done`, shop timer tests | Đạt |
| AC-P2-25 | `test_one_day_no_input`, smoke 22.200 tick | Đạt |
| AC-P2-26 | Upgrade/loop test kiểm trạng thái qua Ngày | Đạt |
| AC-P2-27 | `test_pause_gather_freezes_counters`, `test_pause_freezes_shop_timer` | Đạt |
| AC-P2-28 | `test_days_and_inventory_flags_exit_2`, `test_rejections`, attack/photo test | Đạt |
| AC-P2-29 | `test_five_days_complete_and_deterministic`; smoke Day 2 so byte | Đạt |
| AC-P2-30 | Day 1 chạy 22.200 tick trong 2.44 s | Đạt trên môi trường lần chạy này |
| AC-P2-31 | Gather → kho → Quan; tick 0 `stock` khớp file | Đạt; xem `docs/proof/phase-2/integration.md` |

## Kết quả chạy

- `PYTHONPATH=tests:. python3 -m unittest discover -s tests -v`: **103 test, OK, 2 skipped**. Một skip là test CLI contract cũ không áp dụng sau v1.1; skip còn lại là kiểm thanh toán chưa nối.
- `.agents/skills/pre-push-check/check.sh --save docs/proof/phase-2`: **PASS** — unittest; gather/quan cùng seed cho output từng byte; `--ticks -1` trả mã 2. Xem [`pre-push-check.txt`](../proof/phase-2/pre-push-check.txt).
- Gather → kho → Quan: exit 0; snapshot kho Quan tick 0 khớp file. Chi tiết và fixture ở [`docs/proof/phase-2/`](../proof/phase-2/integration.md).
- `day --days 1 --seed 1 --ticks 22200`: `days_complete`, `days_completed:1`, 22.200 tick, 2.44 s.
- `day --days 2 --seed 1 --ticks 44400`: `days_complete`, `days_completed:2`; hai lần chạy giống từng byte.

## Kết quả chạy lại (lần 2, `a5d5965`)

- Toàn bộ unittest: **xanh**, gồm `tests/test_p2_acceptance.py` (6 test mới). Số test và lệnh ở [phase-4.md](phase-4.md).
- Các file bằng chứng ở trên (`docs/proof/phase-2/`) giữ nguyên từ lần 1. Định dạng kho trong `kho.json` là **kho đếm v1.1** của lúc đó. Từ contract 1.2 kho là cá thể; xem phase-3.

## Kết luận

- **Lần 1 (`cd1c523`):** chưa báo xanh. Lúc đó AC cá P2-04/05 chưa có kiểm chứng, AC-P2-02 còn test bị skip.
- **Lần 2 (`a5d5965`):** cả 31 AC-P2 đều có kiểm chứng và **đạt**. Tag `phase-2` đã được TV1 gắn trước lần kiểm này. Kết quả lần 2 là kiểm hồi tố trên `main`, không phải trên đúng commit gắn tag.
