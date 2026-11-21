# haidangwork1411 — phản tư cá nhân

- **Tôi đã làm:** Phụ trách `sim/gather` lát 2 qua 4 phase: P1 hái nút, bắt cá và sửa payload sự kiện PRD-0 v1.0 (`ad7c83d`, `c9d2689`, `cfd5e43`, PR #2/#5); P2 Cá Sấu Năm Chèo (T220–T223) và ngữ cảnh Ngày (T246) (`561c1d9`, PR #7); P3 giỏ cá thể, hao tươi 240 đơn vị/điểm, `spoiled` và LIFO (T310–T312) ghép `chonoi.inventory` v1.2 (`0d156f2`, `27e7f99`, PR #11); P4 fixture benchmark T411 hỗ trợ TV5 (`94e9739`, PR #9).
- **Tôi đã review:** Rà ranh giới `try_add_hold` với TV1, kiểm diff `origin/main` (`b84a440`, `2ea863d`), chạy test TV2, toàn bộ suite và `pre-push-check` trước mỗi PR.
- **AI sai ở đâu và tôi phát hiện thế nào:** P2 cộng dồn float tuần tra 240 bước làm đổi hướng trễ 1 tick — phát hiện nhờ test biên, sửa bằng ngưỡng `1e-9`. P3 AI bật cá thể theo `tuning.freshness` dù `game.contract.json` v1.1 đã có khóa này — phát hiện khi rà `2ea863d` của TV1, đổi sang `uses_individuals(contract_version)`.
- **Điều tôi học được:** Luôn đọc diff `origin/main` trước khi ghép, viết test biên số học và giữ ranh giới module sạch để tích hợp không xung đột.
