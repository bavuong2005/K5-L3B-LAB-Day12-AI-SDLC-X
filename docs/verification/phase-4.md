# Verification Phase 4 — Phát hành v1.0.0 (Contract v1.3)

> TV5 (Bench/QA) kiểm trên `main` @ `a5d5965`, 2026-11-21. Tag `phase-4` = `v1.0.0` = `89a035d`. Từ `89a035d` tới `a5d5965` chỉ có commit docs của TV2 (`a5d5965`), không đổi `chonoi/`.
> Kiểm hồi tố: tag đã gắn trước lần kiểm này. Mục clean clone (AC-P4-04) kiểm trên **đúng `v1.0.0`**.
> Bằng chứng: [`docs/proof/phase-4/proof.md`](../proof/phase-4/proof.md), sinh bởi `SOAK_DAYS=10 .agents/skills/phase-proof/proof.sh 4`. Kèm theo [`bench.json`](../proof/phase-4/bench.json) và [`soak.json`](../proof/phase-4/soak.json).
> Đề không đặt ID AC cho P4. TV5 tự đánh số `AC-P4-01…11` theo mục DoD của [TICKET-04](../prd/phase-4-ticket-04.md).

| AC | Yêu cầu (DoD TICKET-04) | Kiểm chứng | Kết quả |
|---|---|---|---|
| AC-P4-01 | `contract_version:"1.3"`, khai `bench_cmd` và `soak_cmd` ở gốc | `tests/test_p4_runners.py…test_contract_1_3_khai_bench_va_soak` | Đạt |
| AC-P4-02 | `bench_cmd --seed 42 --duration 30` tạo `bench.json` đủ 5 trường, đúng công thức | `test_p4_runners.Bench.*` (5 trường, `avg = frames/measured_s`, 1% low, đối số sai → mã 2); proof: `avg_fps` 4159.7, `p1_low_fps` 1191.1, `frames` 124380, `measured_s` 29.90, `load_ms` 4 | **Một phần**: lệnh và cấu trúc JSON đạt, ba mốc (≥ 60 / ≥ 30 / ≤ 10 s) đạt. Nhưng bench vẽ vào bộ đệm CPU 1280×720, không mở cửa sổ và không chạy client PixiJS/WebGL thật. Vì vậy số FPS **không phản ánh** hiệu năng render thật mà người chơi thấy. |
| AC-P4-03 | Cảnh báo thủy quái gần / oxy sắp hết / khách sắp giận, chế độ tương phản cao | Bằng chứng của TV6: [`ui-warnings.md`](../proof/phase-4/ui-warnings.md), `warn-gather.png`, `warn-quan.png` | Đạt theo bằng chứng của TV6. TV5 chưa tự chơi thử |
| AC-P4-04 | Clone sạch chạy UI ≤ 3 lệnh | `git clone --branch v1.0.0` vào thư mục trống → `python3 -m chonoi.live --mode day` in `http://127.0.0.1:8000/`, `GET /` → 200; unittest trên clone: 173 test OK | Đạt (macOS, Python 3, không cài thêm gói) |
| AC-P4-05 | Release `v1.0.0` có bản đóng gói, release notes | [`docs/release-notes-v1.0.0.md`](../release-notes-v1.0.0.md) có điểm mới, cách chạy, giới hạn | **Chưa kiểm được**: máy kiểm không có `gh`, nên chưa xác nhận tệp đính kèm Release. T421 (artifact) còn mở trong `specs/004-release/tasks.md` |
| AC-P4-06 | `CHANGELOG.md` theo phase; rà `CREDITS.md` / `LICENSE` | `CHANGELOG.md` có mục Phase 1–4 (breaking change kho ở Phase 3); `CREDITS.md` có; không có `LICENSE` (starter không có, release notes đã ghi) | Đạt |
| AC-P4-07 | Regression P1–P3 còn hiệu lực | `PYTHONPATH=tests:. python3 -m unittest discover -s tests` → **207 test OK (skipped=4)**; [phase-1](phase-1.md), [phase-2](phase-2.md), [phase-3](phase-3.md) | Đạt |
| AC-P4-08 | `soak_cmd --seed 7 --days 10` sẵn sàng; `days_completed = days`, `crashes = 0`, tất định | proof: `days 10`, `days_completed 10`, `crashes 0`, 10 phần tử `results`, 11.6 s; `test_soak_tat_dinh_bo_duration` (2 lần giống nhau khi bỏ `duration_s`); `test_quan_soak…test_soak_10_ngay_lien_tiep_on_dinh` | Đạt. Ghi chú: bot đứng yên nên `earned` = 0 mọi Ngày. Soak chứng minh không crash và state chạy xuyên 10 Ngày, không đo được kinh tế |
| AC-P4-09 | Tag `phase-4` và Release `v1.0.0` cùng commit trên `main` | `git rev-parse phase-4^{} v1.0.0^{}` → cả hai `89a035d` | Đạt (tag). Release: xem AC-P4-05 |
| AC-P4-10 | Retro rà hành động P2; phản tư cá nhân đủ người | `docs/retro.md` (TV6); `docs/members/`: thanhhale288, thanhanbk02, haidangwork1411, dqk2210, bavuong2005, NgMinPhuc | Đạt (6/6) |
| AC-P4-11 | Mở rộng (nhóm 6: ≥ 2 mục cả lab) có test và bằng chứng, khai `extensions` | `extensions: ["burn"]`, có test và bằng chứng. Phụ đề SFX (T461) có bằng chứng [`sfx-captions.md`](../proof/phase-4/sfx-captions.md) nhưng **chưa khai** trong `extensions` | **Một phần**: chỉ 1 mục được khai |

## Kết luận
- Đạt: 01, 03, 04, 06, 07, 08, 09, 10.
- Một phần: AC-P4-02 (bench không render thật) và AC-P4-11 (thiếu khai mục mở rộng thứ 2).
- Chưa kiểm được: AC-P4-05 (artifact trên GitHub Release).
- Việc cần làm (không thuộc file của TV5): TV1 xác nhận và đính kèm artifact Release (T421), cân nhắc khai mục phụ đề SFX trong `extensions`. Nếu còn giờ, TV5 cùng TV2 làm bench chạy client WebGL thật (T411).

## Bổ sung của TV6 (2026-11-22, sau bản kiểm của TV5 — TV5 cần chạy lại trên commit bàn giao)
- **AC-P4-02 (bench):** `chonoi/bench.py` nay có `--mode browser` (mặc định `auto`): dựng client web thật trong Chrome headless 1280×720 và đo khung `requestAnimationFrame`. Số mới `docs/proof/phase-4/bench.json`: xem [`bench-notes.md`](../proof/phase-4/bench-notes.md) (phương pháp, giới hạn: vsync tắt): `avg_fps` 313.4, `p1_low_fps` 184.6, `load_ms` 1161. Không có Chrome thì rơi về `--mode sim` (không phải render).
- **AC-P4-11 (mở rộng):** thêm `leaderboard` (`chonoi/leaderboard.py`, `tests/test_leaderboard.py`, bằng chứng `docs/proof/phase-4/leaderboard.md`). **Chưa khai** trong `game.contract.json` (`extensions` vẫn `["burn"]`; chỉ TV1 sửa) — TV1 cần đổi thành `["burn","leaderboard"]`.
- Thêm ngoài DoD: đồ họa PixiJS thủ tục (`chonoi/web/art/`), hướng dẫn chơi, cốt truyện, nhạc nền, chế độ terminal `chonoi.play`. Test toàn bộ xem lần chạy cuối trong `docs/proof/phase-4/`.
