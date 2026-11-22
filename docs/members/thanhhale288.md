# thanhhale288 — phản tư cá nhân

- Tôi đã làm: PO/UI P1–P4. HUD gather/quán (`96acdeb`, `88eb0ef`), menu/ngày/Shop/pause (`d724735`), HUD độ tươi (`f5d0a4e`), khung `day` (`2fd94cf`), brief + TICKET-04 (`4d86606`, `a7e2db4`), cảnh báo + tương phản cao, SFX + phụ đề (`4b97ddc`). Phiên cuối: đồ họa PixiJS thủ tục, hướng dẫn, cốt truyện (nhân vật "Trường con"), nhạc nền, chế độ terminal `chonoi/play.py` (`0f3ee74`); leaderboard, sửa lỗi UI live, viết lại 4 test skip (`822c850`); bench có render thật bằng Chrome headless (`603671c`).
- Tôi đã giúp: chép đề vào `docs/prd/`; gộp PR gather/quán; ghi clarify; gộp `origin/main` của TV5 (`8aab099`).
- AI sai ở đâu: chép TICKET-02 bị lọc trùng, mất ô bảng (đọc lại board mới thấy). Phiên cuối: chạy test thiếu `PYTHONPATH=tests:.` ra 21 lỗi giả; lỗi pause/Shop/hold/DayResult/Summary chỉ lộ khi tôi chơi thử, test xanh không bắt được; một bản "kiểm chứng" của agent nghe có vẻ bịa nên tôi cho chạy lại thật.
- Bài học: test xanh chưa đủ, phải chơi thật; checkbox khớp code; tag phase không để đến phút cuối. Mọi phần trên có AI hỗ trợ; tôi duyệt và chạy lại (265 test OK).
