# thanhanbk02 — phản tư cá nhân

- Tôi đã làm: lát 1 gather (`4d2752c`), contract v1.1 và cá bơi (`b84a440`), adapter kho hai schema (`2ea863d`). Trên main hiện tại: `Session` truyền `contract_version` vào sim, `game.contract.json` lên `"1.3"` (gameplay và kho vẫn theo v1.2).
- Tôi đã review: báo cáo tiến độ nhóm (main `2b3aee0`). Gather và quán đã bàn giao cá thể, nên bật schema là đúng phần TV1, không chờ thêm.
- AI sai ở đâu và tôi phát hiện thế nào: bản tóm tắt cũ nói giỏ vẫn là tên loại. Đọc `gather.py` / `quan.py` và test độ tươi trên main thì hai đầu đã xong. Bật `"1.3"` làm test P1 trỏ kho đếm thành mã 2; sửa kỳ vọng theo cá thể, không sửa luật cho xanh.
- Điều tôi học được: version trong file contract chỉ có tác dụng khi runner truyền nó vào sim. Để `None` thì sim tự suy và file `"1.3"` không đổi gì.
