# bavuong2005 — phản tư cá nhân

- Tôi làm luồng nấu, bưng, giao món, tính tiền và boa trong quán. Khi nối với phần khách của TV3, tôi dùng cùng mã đơn cho món và cho thao tác dọn món. Các thay đổi về quán và giao diện có trong `be6a3c7` và `bcfaf6e`.
- Tôi bổ sung phần chốt giá theo độ tươi cho kho cá thể, dựa trên các ID mà logic giữ chỗ của TV3 đã chọn.
- AI ban đầu yêu cầu bên gọi truyền sẵn `base_price`, nhưng không nối giá vào đường tương tác. Khi rà lời gọi từ `_interact()`, tôi thấy đơn kho cá thể bị chặn ngay lúc bắt đầu nấu.
- Tôi học được cách kiểm tra tính năng từ điểm vào thật của game và đối chiếu dữ liệu giữa các phần trước khi kết luận đã tích hợp xong.
