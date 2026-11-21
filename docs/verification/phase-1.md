# Verification Phase 1 — Lặn & Hái + Mở Quán (Contract v1.0, nay chạy trên v1.3)

> TV5 kiểm lại trên `main` @ `a5d5965` (sau tag `v1.0.0` = `89a035d`), 2026-11-21. Bản đầu (ID tạm, chỉ baseline starter) được thay bằng ID chính thức `AC-P1-xx` của [`specs/001-phase-1-core/spec.md`](../../specs/001-phase-1-core/spec.md).
> Lệnh chung: `PYTHONPATH=tests:. python3 -m unittest discover -s tests -v` → **207 test, OK (skipped=4)**. 4 test bị skip là các ca dành cho contract v1.0/v1.1, nay đã thay bằng luật mới (xem phase-2).
> Lưu ý: số liệu chạy theo tuning hiện hành (P2 trở đi: 8 đàn, 4 bàn, 6 món), không còn theo tuning v1.0.

| AC | Kiểm chứng (test / lệnh) | Kết quả |
|---|---|---|
| AC-P1-01 | `test_rules_p1.Oxygen.test_oxy_giam_duoi_nuoc`, `test_oxy_hoi_o_mat_nuoc` | Đạt |
| AC-P1-02 | `test_rules_p1.DiveSurface.test_dive_roi_surface` | Đạt |
| AC-P1-03 | `test_rules_p1.Oxygen.test_oxy_can_ve_0_va_oxygen_empty` | Đạt |
| AC-P1-04 | `test_rules_p1.ChokeHp.test_choke_moi_choke_interval_tru_1_mau` | Đạt |
| AC-P1-05 | `test_rules_p1.ChokeHp.test_mau_ve_0_thi_faint`, `test_gather_slice2…test_faint_after_gathering_clears_hold_writes_empty_inventory_and_is_deterministic` | Đạt |
| AC-P1-06 | `test_gather_slice2…test_harvest_at_surface_sets_regrow_and_regrows` | Đạt |
| AC-P1-07 | `test_harvest_blocked_underwater_and_out_of_radius`, `test_catch_blocked_at_surface_and_out_of_radius` | Đạt |
| AC-P1-08 | `test_catch_underwater_yield_removal_and_cooldown` | Đạt |
| AC-P1-09 | `test_rules_p1.Hold.*`, `test_hold_capacity_never_exceeded`, `test_hold_full_contract_payload_and_atomic_fish_rejection` | Đạt |
| AC-P1-10 | `test_harvest_deterministic_distance_and_id_tiebreak`, `test_catch_deterministic_distance_and_id_tiebreak` | Đạt |
| AC-P1-11 | `test_dock_priority_over_harvest_and_writes_inventory_once` | Đạt |
| AC-P1-12 | `test_smoke_p1…test_time_ends_gather_and_keeps_hold`, `test_inv_01_not_written_when_tick_limit_first` | Đạt |
| AC-P1-13 | `test_smoke_p1…test_inv_01_gather_writes_inventory_quan_reads_it`, `test_rules_p1…test_quan_inventory_mau_nap_dung_kho` | Đạt |
| AC-P1-14 | `test_rules_p1.QuanCustomers.test_khach_den_theo_lich`, `test_quan_customers…test_den_dung_first_tick_va_lap_theo_interval` | Đạt |
| AC-P1-15 | `test_quan_customers…test_no_dish_khi_kho_rong` | Đạt |
| AC-P1-16 | `test_rules_p1…test_khach_bo_di_sau_patience_tru_uy_tin`, `test_uy_tin_kep_o_min` | Đạt |
| AC-P1-17 | `test_quan_p3_freshness…test_reserved_item_sets_price_through_payment` (cook_started → dish_ready → dish_picked) | Đạt |
| AC-P1-18 | `test_rules_p1.QuanServe.test_tra_tien_theo_gia_menu` (lúc P2 test này còn skip, nay đã chạy) | Đạt |
| AC-P1-19 | Có boa: `test_p3_acceptance…test_ac_p3_15_16_…_va_boa` (tip = floor(59×0.2)=11). Không boa khi kiên nhẫn < 50%: `test_reserved_item_sets_price_through_payment` (tip 0) | Đạt |
| AC-P1-20 | `test_p1_acceptance.AcP1_20_InteractPriority` (hai bếp cách đều → id nhỏ; bếp trước bàn; một interact/tick) | Đạt (test mới của TV5) |
| AC-P1-21 | `test_quan_customers…test_het_ca_closing_va_quan_end` | Đạt |
| AC-P1-22 | `test_rules_p1.Determinism.*`, `test_smoke_p1…test_con_02_deterministic_bytes`; `.agents/skills/pre-push-check/check.sh` | Đạt |
| AC-P1-23 | `test_quan_customers…test_reserved_vuot_stock_exit_2`, `test_headless_tra_ma_2` | Đạt |
| AC-P1-24 | `test_p1_acceptance.AcP1_24_CookOrder` (order_tick nhỏ trước, hòa → id bàn nhỏ) | Đạt (test mới của TV5) |

Hợp đồng CLI/JSONL của starter (CON-01..03, MOVE-01..03, INV-01) vẫn xanh trong `tests/test_smoke_p1.py`.

## Đánh giá ngắn
- Cả 24 AC-P1 đều có test chạy thật và đều xanh trên `a5d5965`. AC-P1-20 và AC-P1-24 trước đây chưa có test riêng, nay có `tests/test_p1_acceptance.py`.
- Không tạo `tests/test_p1_rules.py` như T006 ghi. Luật P1 đã được TV5 viết trong `tests/test_rules_p1.py` (`16bb5ad`), phần còn lại nằm trong các test theo module.
- Golden JSONL (T037) **chưa làm**. Lý do: tuning P1 đã đổi qua v1.1–v1.3 nên golden v1.0 không còn đúng. Tính tất định đang được kiểm bằng cách chạy 2 lần rồi `cmp`.
