# TEAM

**Tên nhóm:** Quán Trường con  **Số người:** 6  (khớp `team_size` trong `game.contract.json`; TV1 sửa số này)

| Thành viên | GitHub handle | Module chính | Vai quy trình | Người dự phòng cho |
|---|---|---|---|---|
| Phạm Thanh An | thanhanbk02 | `sim/gather` (lát 1: oxy, ngạt, Máu, giỏ) | Integrator | TV2 |
| Tăng Nguyễn Hải Đăng | haidangwork1411 | `sim/gather` (lát 2: P1 hái/bắt cá/bến/kho; P2 Cá Sấu T220–T223 & ngày T246; P3 giỏ cá thể/độ tươi T310–T312; P4 fixture bench T411) | | TV1 |
| Đỗ Quốc Khánh | dqk2210 | `sim/quan` (khách, giữ chỗ, uy tín) | | TV4 |
| Mai Lê Bá Vương | bavuong2005 | `sim/quan` (bếp, bưng, tiền, boa) | | TV3 |
| Nguyễn Minh Phúc | NgMinPhuc | `qa` (test, verification, harness AI) | QA lead | TV6 |
| Lê Thanh Hà | thanhhale288 | `client/ui` (`chonoi/web/`) | PO · Scrum/Release | TV5 |

> Mỗi thành viên **tự điền tên + handle thật** vào dòng của mình (commit bằng tài khoản của mình). Kiểm: `python3 tools/check_team.py`.

**Vai quy trình:** PO (đầu mối hỏi giảng viên, giữ `docs/clarify.md`) · Integrator (giữ `docs/contracts/`, gắn tag) · QA lead · Scrum/Release. Có thể kiêm.

## Thỏa thuận làm việc nhóm (điền trong 15 phút kickoff, ≤ 10 dòng)

- Kênh liên lạc: nhóm chat chung của lab; việc gấp thì nói trực tiếp tại bàn.
- Khi bất đồng về thiết kế: mỗi bên nói 2 phút; chưa xong thì PO quyết về yêu cầu, Integrator quyết về kỹ thuật/hợp đồng, ghi lý do vào `docs/clarify.md`.
- Khi ai đó trễ hoặc vướng quá 10 phút: báo ngay trong kênh; người dự phòng (cột cuối) vào ngồi cặp, commit ghi `Co-authored-by:`.
- Câu hỏi về đề: gửi PO, chỉ PO hỏi Anh Năm trên board (đỡ tốn lượt), câu trả lời ghi `docs/clarify.md`.
- Giờ standup giữa phase: Phase 1 lúc ~0:30 (mỗi người 1 dòng vào `docs/standup.md`), các phase sau ở giữa phase.
- Mốc đóng băng: hết phút 45 của mỗi phase ngừng thêm tính năng, chỉ tích hợp + sửa lỗi.
- Cách đọc code của nhau: cặp cùng module đọc chéo lát của nhau (TV1↔TV2, TV3↔TV4); TV5 chạy test sau mỗi lần gộp.
- Cách làm việc với Git: push thẳng `main`, commit nhỏ; `git pull --rebase` trước khi sửa, chạy test trước khi push. File chung (`game.contract.json`, `docs/contracts/`) chỉ TV1 sửa; chỉ TV1 gắn tag sau khi TV5 báo xanh.
