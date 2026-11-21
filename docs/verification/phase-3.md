# Verification Phase 3 — Mùa Nước Nổi (độ tươi, kho cá thể, gameplay v1.2)

> TV5 kiểm trên `main` @ `a5d5965`, 2026-11-21. Tag `phase-3` = `bc868dd`; contract đang chạy là `1.3`, với gameplay, kho và JSONL giữ v1.2 (TICKET-04).
> Kiểm hồi tố: tag `phase-3` đã gắn trước lần kiểm này, nên kết quả dưới đây là của `main` hiện tại, không phải của đúng commit gắn tag.
> Bằng chứng CLI: [`docs/proof/phase-3/proof.md`](../proof/phase-3/proof.md), sinh bởi skill `.agents/skills/phase-proof/proof.sh 3`, gồm lệnh, đầu ra và mã thoát thật.
> Test hộp đen theo AC: [`tests/test_p3_acceptance.py`](../../tests/test_p3_acceptance.py) (16 test, chạy CLI với `game.contract.json` thật). Test đơn vị của TV1–TV4 ở `test_inventory_v12`, `test_freshness_frame`, `test_gather_phase3_freshness`, `test_quan_p3_freshness`.

| AC | Kiểm chứng | Kết quả |
|---|---|---|
| AC-P3-01 | `test_p3_acceptance…test_ac_p3_01_contract_freshness_va_quan_ticks_0` (freshness = 100 / 0.5 / 0.25 / 30) | Đạt |
| AC-P3-02 | `test_ac_p3_02_kho_ca_the_hop_le_gom_rong_va_hang_uon` | Đạt |
| AC-P3-03 | `test_ac_p3_03_kho_dem_v10_ma_2_khong_tao_out`; proof "kho đếm v1.0 → exit 2" | Đạt |
| AC-P3-04 | `test_ac_p3_04_kho_sai_ma_2` (7 file: id trùng/rỗng, kind lạ, fresh < 0, > 100, NaN, khóa gốc lạ); `test_stock_sai_schema_exit_2` | Đạt |
| AC-P3-05 | `test_ac_p3_05_cap_ben_ghi_mot_lan_nguyen_tu_sap_id`, `…_ngat_ghi_kho_rong`, `…_tick_limit_giu_nguyen_dich`; `test_ghi_nguyen_tu_sap_id_va_giu_nguong_30` | Đạt |
| AC-P3-06 | `test_gather_phase3_freshness…test_harvest_and_catch_allocate_ids_and_decay_from_next_tick` | Đạt |
| AC-P3-07 | `test_ac_p3_07_gio_hao_0_5_moi_giay` (99.5 sau 60 tick); `test_exact_8400_vs_8401_boundary_from_fresh_100` | Đạt |
| AC-P3-08 | `test_ac_p3_08_scenario_de_spoiled_tick_1_dung_mot_lan` (600 tick, 1 event); proof `proof.md` (dòng event spoiled) | Đạt |
| AC-P3-09 | `test_ac_p3_09_nhieu_ca_the_spoiled_theo_id`; `test_multiple_spoiled_sorted_by_id_already_spoiled_silent_and_clamp_zero` | Đạt |
| AC-P3-10 | `test_monster_hit_and_faint_lifo_individual_items_and_empty_v12_file`, `test_choke_faint_drops_all_hold_lifo_and_writes_empty_inventory` | Đạt |
| AC-P3-11 | `test_ac_p3_11_kho_quan_hao_0_25_va_spoiled_stock`; `test_hao_ke_ca_hang_dang_giu` | Đạt |
| AC-P3-12 | `test_khach_moi_giu_ca_the_toi_nhat`, `test_bang_do_tuoi_thi_lay_id_nho_hon`, `test_stock_va_reserved_dung_schema` | Đạt |
| AC-P3-13 | `test_nha_va_giu_lai_tu_ca_the_toi_nhat_con_lai`, `test_hai_don_cung_bi_anh_huong_uu_tien_order_tick_roi_id_ban` | Đạt |
| AC-P3-14 | `test_khong_con_hang_toi_thi_unfulfillable_va_cho_den_het_kien_nhan` | Đạt |
| AC-P3-15 | `test_ac_p3_15_16_items_sap_kind_roi_id_gia_theo_tuoi_va_boa` (món 4 nguyên liệu → `[I5, I2, I9, I10]`, I7 dư giữ lại) | Đạt (test mới của TV5) |
| AC-P3-16 | Như trên: base `floor(120×TB fresh/100)` = 59, boa `floor(59×0.2)` = 11, `money` 70; `test_reserved_item_sets_price_through_payment` | Đạt |
| AC-P3-17 | `test_reserved_troi_hang_uon_exit_2`, `…_trung_id_giua_2_don_exit_2`, `…_chi_id_khong_ton_tai_exit_2`, `…_khong_du_cong_thuc_exit_2`, `test_duplicate_hold_id_exit_bad_input` | Đạt |
| AC-P3-18 | `test_ac_p3_18_smoke_ban_giao_file_cua_de`; proof: `kho.json` I1 fresh 99.99166…, snapshot quán 99.992 (trong ±0.01) | Đạt |
| AC-P3-19 | `test_ac_p3_19_day_ban_giao_cung_tick_khong_hao_them`; `test_gather_end_quan_same_tick_no_extra_step` | Đạt |
| AC-P3-20 | `test_ac_p3_20_ngay_2_cap_id_moi_cho_mau_hold`; `test_day2_reallocates_hold_item_ids`, `test_reserve_existing_ids_hold_full_no_leak_and_multiday_continuity` | Đạt |
| AC-P3-21 | `test_pause_freezes_freshness_decay`, `test_shop_individual_stock_does_not_decay` | Đạt |
| AC-P3-22 | Toàn bộ unittest xanh (xem [phase-4.md](phase-4.md)); [phase-1.md](phase-1.md) và [phase-2.md](phase-2.md) chạy lại trên v1.3; test đổi được ghi lý do trong `CHANGELOG.md` | Đạt |
| AC-P3-23 | `test_ac_p3_23_chay_hai_lan_giong_tung_byte` (gather, quan, day); proof: `cmp` cho gather 600, quan 600, day 2 Ngày | Đạt |

## Mở rộng
- `extensions: ["burn"]` (TV4): bằng chứng ở [`docs/proof/phase-3/tv4-cooking.md`](../proof/phase-3/tv4-cooking.md) và [`docs/proof/phase-4/tv4-burn-2111.md`](../proof/phase-4/tv4-burn-2111.md); test `test_quan_p3_freshness…test_burn_boundary_and_re_reservation`.
- `current` và `reservations`: **không làm**, không khai trong `extensions`.

## Ghi chú QA
- JSONL làm tròn `fresh` tới 3 chữ số, file kho giữ đủ độ chính xác. Đề cho phép dung sai ±0.01 nên đúng, nhưng test so hai bên phải dùng dung sai, không so bằng. Lần đầu AI viết test so bằng và test fail; TV5 phát hiện qua traceback và sửa test, không sửa luật.
- File `--inventory-out` được tạo với quyền `0600` (vì tạo bằng `mkstemp` rồi `replace`). Không vi phạm đề, nhưng ai khác đọc file trên máy dùng chung sẽ bị chặn (`chonoi/inventory.py:140`). Cần báo TV1, vì file này là của TV1, TV5 không sửa.

## Kết luận
Cả 23 AC-P3 đều đạt trên `a5d5965`. Không có AC nào chưa đạt.
