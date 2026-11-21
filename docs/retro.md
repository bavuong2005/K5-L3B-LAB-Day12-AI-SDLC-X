# Retro nhóm

## Phase 2 (nhanh) — TV6 ghi nháp, cả nhóm bổ sung
- Điều tốt: spec/plan/tasks (Spec Kit) và research có trước khi code, nên số chuẩn TICKET-02 đối chiếu nhanh (sửa được 2 giả định sai trong `clarify.md`: boa `floor`, bếp chọn đơn theo `order_tick`); UI menu/HUD/Shop xong sớm với dữ liệu demo; tích hợp qua `main` không vỡ test (32/32), PR #1 (QuanSim) gộp không conflict.
- Điều tệ: lõi P1 (gather lát 2, phần quán) xong muộn nên P2 xây trên nền chưa chắc; tag `phase-1` trễ hạn; các file khung (`headless`, `inputs`, `scenario`, `runner`, `live`) phải sửa cho v1.1 nhưng nhận việc muộn; AI không đọc được lab board lúc đầu → phải chép đề vào `docs/prd/`; luật `quan.py` mới chưa có test bao phủ.
- 1 hành động cho Phase 3: **làm adapter kho trước, chốt schema trong 7 phút đầu (ADR-0001), mỗi lát push sớm theo schema đã chốt** — người nhận: TV1 (adapter), TV6 (dẫn buổi chốt, theo dõi ở standup phút 20).

## Phase 4 (cuối) — TV6 ghi, cả nhóm bổ sung số token

- Rà hành động Phase 2 ("adapter kho trước, schema trong 7 phút, push sớm"): **làm một phần**. ADR-0001 và research P3 có trước code; HUD độ tươi (T335/T336) và khung `day` đã lên `main`. Chưa xong vì contract vẫn chưa lên v1.2 do TV1 (schema `inventory.py`) và lát gather/quan độ tươi chưa khép — standup phút 20 P3 không kịp đổi người sang adapter.
- Điều tốt: PO chép được TICKET-02/03/04 vào repo nên agent đọc đề được; UI P1–P2 và cảnh báo P4 nằm ở `chonoi/web/` không đụng sim; PR #2/#4/#5 đã vào `main`.
- Điều tệ: tag `phase-1`…`phase-3` gắn muộn và gắn một lượt (cùng 16:33 ngày 2026-11-21, sau `phase-4`), không đúng hạn từng phase; checkbox task từng bị lệch so với code (UI P2 đã có mà `tasks.md` còn `[ ]`); id cá thể xuyên Ngày (T331) chưa có `ItemIds`.
- Số liệu commit trên `main` (2026-11-21, `git shortlog -sn`): thanhhale288 27, Hai Duong 9, Hela 5 (merge), dqk2210 5, Hải Đăng 4, MinPhuc 4, noobpyno 3, thanhanbk02 1. Đọc chéo: TV6 review PR quán/gather khi merge. Token: từng người chưa điền `/cost` — ô nhật ký còn trống.
- Một lần AI sai:
  - Bản chép TICKET-02 lọc trùng làm rơi ô bảng và chuỗi trong ngoặc kép; phát hiện khi đối chiếu board lần 2, chép lại không lọc (`docs/ai-usage-log.md`).
  - TV3: AI báo soak 10 Ngày đỏ vì kỳ vọng "5 khách/Ngày" — đối chiếu JSONL thấy kho nhỏ + `plan_dishes` khiến `no_dish` từ lượt 3 là đúng luật; bài học: sửa kỳ vọng test theo luật, không sửa luật theo kỳ vọng, và dùng `git stash` xác nhận lỗi không có sẵn trên HEAD trước khi đụng test người khác.
- Nếu làm lại: phút 0 mỗi phase một người khóa `game.contract.json` và gắn tag dù lõi còn nợ, ghi nợ trung thực trong verification — đừng chờ "xanh hết" rồi trễ hạn.
