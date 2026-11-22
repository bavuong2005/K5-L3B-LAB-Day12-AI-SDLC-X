# Day 12 — AI SDLC: Quán Ăn Chợ Nổi

> **Làm theo nhóm 4–6 người** · Dùng AI để xây game 2D qua **4 phase** trong **3 giờ**: Trường con lặn bắt cá, hái rau trên mặt nước rồi tối mở quán phục vụ khách.
> **Yêu cầu từng phase mở đúng mốc giờ tại lab board:** **[Chợ Nổi Lab](https://claude.ai/artifact/E35v787wSx2wDgPTNhMVDg)** (cần đăng nhập claude.ai; có trợ giảng AI cho từng phase).

## Bắt buộc (chỉ có thế)

Cách làm việc kỹ thuật là **tự do** (push thẳng, nhánh + PR, pair, có hay không CI…). Cái bắt buộc:

1. **Một repo chung:** trưởng nhóm **fork** repo này, đặt tên `K5-L3B-LAB-Day12-AI-SDLC-<ten-nhom>`, thêm mọi thành viên làm collaborator (*Settings → Collaborators*, quyền Write) và để repo **public** (giảng viên xem được, không cần mời).
2. **Cả nhóm cùng commit** bằng tài khoản GitHub của mình, mỗi người **≥ 3 commit có nội dung** (làm cặp thì ghi `Co-authored-by:`).
3. **Điền [`TEAM.md`](TEAM.md):** danh sách thành viên + thỏa thuận làm việc nhóm; sửa `team_size` trong [`game.contract.json`](game.contract.json). Commit của người không có trong `TEAM.md` không được tính.
4. **Gắn tag** `phase-1` … `phase-4` đúng hạn; chạy được tại từng tag.
5. **Ghi chép tối thiểu:** `docs/verification/phase-n.md`, `docs/clarify.md`, `docs/ai-usage-log.md`, `docs/retro.md`, `docs/members/<handle>.md`.

## Bắt đầu nhanh

Máy cần Python 3 (thư viện chuẩn, không cài thêm gói; kiểm trên macOS với Python 3.13). Đề yêu cầu macOS hoặc Linux; Windows chưa kiểm.

Từ clone sạch, bản có giao diện mở trong **tối đa 3 lệnh**:

```bash
git clone <fork-của-nhóm>
cd <fork-của-nhóm>
python3 -m chonoi.live --mode day
```

Trình duyệt mở địa chỉ in ra. Lần đầu chơi sẽ có **cốt truyện** (nhân vật chính Trường con) và **hướng dẫn tương tác** cho phần lặn và phần quán tối (mở lại bằng nút "Hướng dẫn" hoặc phím `?`); có nhạc nền tạo bằng code, chỉnh âm lượng ở màn tạm dừng. Hướng dẫn chi tiết: [`docs/how-to-play.md`](docs/how-to-play.md); cốt truyện: [`docs/story.md`](docs/story.md). Điều khiển: WASD di chuyển, E tương tác (kể cả nấu, lấy món, bưng món, về bến), Space bắt cá, R chơi lại (khi ván đã kết thúc hoặc lỗi), Esc hoặc P tạm dừng, **C** bật/tắt tương phản cao, **M** bật/tắt âm, **N** bật/tắt phụ đề SFX.
**Chơi trong terminal** (không cần trình duyệt): `python3 -m chonoi.play --mode day` (WASD/mũi tên, E, Space, P, H trợ giúp, Q thoát; `--demo` cho bot tự chơi, `--text` chạy từng dòng lệnh). Xem [`docs/play-cli.md`](docs/play-cli.md).
Cảnh báo bằng chữ: thủy quái gần, oxy sắp hết, khách sắp giận (xem [kiểm chứng](docs/proof/phase-4/ui-warnings.md); thử nhanh `?demo=warn`, `?demo=warnq`, `?contrast=1` sau địa chỉ).

```bash
PYTHONPATH=tests:. python3 -m unittest discover -s tests -v          # test
python3 -m chonoi.headless --mode day --seed 1 --days 1 --ticks 30000 --out out.jsonl
python3 -m chonoi.bench --seed 42 --duration 30 --out bench.json     # đo ~33 giây (3 giây làm nóng + 30 giây)
python3 tools/package.py                                             # tạo dist/chonoi-v1.0.0.zip đính kèm Release
python3 -m chonoi.soak --seed 7 --days 10 --out soak.json            # giảng viên chạy; nhóm có thể smoke --days 1
```

Game cần chế độ **headless** theo Test Contract (`python3 -m chonoi.headless --mode gather|quan …`) để được chạy và chấm tự động. **Công nghệ không ràng buộc**: khung Python trong `chonoi/` chỉ là gợi ý, chi tiết ở [`docs/STARTER.md`](docs/STARTER.md).

## Sáng tạo của nhóm

Mở rộng đã làm: `burn`, `leaderboard` (đã có test và bằng chứng), cộng phụ đề SFX và chế độ tương phản cao ở UI. Lõi vẫn đúng: regression 268 test xanh, JSONL mặc định không đổi (xem [verification P4](docs/verification/phase-4.md)).

Nhóm đã thêm **cháy món** (`burn`). Món để trên bếp quá 20 giây sẽ cháy. Quán thử giữ nguyên liệu mới cho đơn. Xem [kiểm chứng cháy món](docs/proof/phase-4/tv4-burn-2111.md).

Phụ đề SFX (`chonoi/web/`, WebAudio không asset ngoài): mỗi hiệu ứng âm thanh có phụ đề, hiện cả khi tắt tiếng. Xem [bảng SFX](docs/proof/phase-4/sfx-captions.md).

Nhóm cũng thêm **bảng xếp hạng cục bộ** (`leaderboard`), chỉ chạy khi có cờ, không đổi gameplay hay JSONL. Top 10 lưu trong file JSON; điểm giảm dần, hòa thì mục ghi trước đứng trước.

```bash
python3 -m chonoi.headless --mode day --days 5 --seed 42 --ticks 200000 --out out.jsonl --leaderboard lb.json --player-name "Út Sen"
python3 -m chonoi.live --mode day --leaderboard lb.json --player-name "Út Sen"   # UI: ghi 1 mục khi đủ 5 Ngày, top 3 hiện ở màn Tổng kết
python3 -m chonoi.live --export-leaderboard top.json --leaderboard lb.json   # xuất {"entries":[{name,score,days_completed,seed}]}
```

Server live (`GET /leaderboard`) khởi động ở trạng thái giữ (held) để UI chưa tính giờ: bot curl phải gửi `POST /input {"hold": false}` trước khi sim chạy. Chỉ ghi một mục khi chạy đủ 5 Ngày, không scenario, `reason:"days_complete"`. Thiếu một cờ trong cặp hoặc sai mode thì mã 2. Test: `tests/test_leaderboard.py`. Bằng chứng chạy thật: [leaderboard.md](docs/proof/phase-4/leaderboard.md).

Lưu ý bench: mặc định (`--mode auto`) `chonoi.bench` dựng client web thật trong Chrome headless (cần Chrome/Chromium, hoặc đặt `CHROME_BIN`) và đo nhịp khung với vsync tắt, nên số cao hơn FPS trên màn hình thật. Không có Chrome thì rơi về `--mode sim` (chỉ mô phỏng + bộ đệm CPU, không phải render). Chi tiết: `docs/proof/phase-4/bench-notes.md`.

Ngoài phần đề yêu cầu, nhóm được **thêm** nhân vật, loài cá/cây, sinh vật, món, bản đồ, cơ chế, câu chuyện, đồ họa, âm nhạc… với ba điều kiện: **không phá phần cố định** (tắt ở headless), ghi mục **"Sáng tạo của nhóm"** trong README của nhóm, và **làm lõi đúng trước**.

## Lịch 3 giờ

| Mốc | Phase | Hạn tag |
|---|---|---|
| 0:00 | Phase 1 (PRD-0) | `phase-1` trước 1:00 |
| 1:00 | Phase 2 | `phase-2` trước 1:55 |
| 1:55 | Phase 3 | `phase-3` trước 2:30 |
| 2:30 | Phase 4 | `phase-4` + Release `v1.0.0` trước 3:00 |

Hết giờ mỗi phase thì gắn tag rồi đi tiếp; chỗ chưa xong ghi trung thực trong bằng chứng.

## Đánh giá (100 điểm)

| Hạng mục | Điểm |
|---|---|
| Test tự động ẩn (headless, gồm kiểm tra lại phase trước) | 25 |
| Làm việc nhóm (một repo chung, chia việc, tích hợp, đổi yêu cầu) | 25 |
| Kiểm chứng & bằng chứng | 15 |
| Harness AI (AGENTS.md, skill, nhật ký dùng AI) | 10 |
| Đánh giá & retro | 10 |
| Chất lượng sản phẩm (đúng yêu cầu, mở rộng/sáng tạo) | 10 |
| Demo | 5 |

## Quy định

- Dùng AI thoải mái; **không sao chép repo của nhóm khác**; bằng chứng phải thật.
- Nhân vật, bối cảnh là bản gốc của lab; asset ngoài chỉ dùng CC0/CC-BY/MIT hoặc tự tạo, ghi nguồn trong `CREDITS.md`. Không commit API key, token, `.env`.
