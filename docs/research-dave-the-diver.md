# Research: Dave the Diver → Quán Ăn Chợ Nổi

> Người viết: TV6 (PO · UI), có dùng AI (Claude Code). Mục đích: lấy *Dave the Diver* làm tham chiếu thiết kế cho game, chuyển bối cảnh sang Đồng bằng sông Cửu Long và ẩm thực chợ nổi.
> Đây là tài liệu tham khảo. Yêu cầu chính thức vẫn là PRD/Ticket của từng phase và `game.contract.json`.

## 1. Project hiện tại đang ở đâu

| Phần | Trạng thái |
|---|---|
| `gather`: buổi sáng lặn, nhìn ngang, vị trí `[x, d]` | Khung đã có: bơi, chặn mép, đồng hồ, cập bến, xuất kho. **Còn TODO:** oxy, ngạt, Máu, ngất, hái nút, bắt cá, giỏ LIFO (`chonoi/sim/gather.py`). |
| `quan`: buổi tối mở quán, nhìn từ trên xuống, vị trí `[x, z]` | Khung có đi lại và nạp kho. **Còn TODO:** khách, giữ chỗ nguyên liệu, bếp, bưng món, tiền, boa, uy tín (`chonoi/sim/quan.py`). |
| Dữ liệu `game.contract.json` | 2 loại cá (cá linh, cá lóc), 2 loại bông (điên điển, súng), 3 món, 1 bếp, 1 bàn. |
| Phase sau | `docs/STARTER.md` ghi "chế độ `day` có từ phase sau", tức là sẽ nối sáng → tối thành vòng ngày. Đây chính là vòng lặp của Dave. |

Ràng buộc áp dụng cho mọi ý tưởng bên dưới:
- Phần thêm phải **tắt ở headless**.
- Số liệu chỉ đọc từ contract hoặc file dữ liệu.
- Ngẫu nhiên chỉ đi qua `Streams`.
- Rubric: "không cộng điểm cho độ phức tạp".

## 2. Dave the Diver được thiết kế thế nào

### 2.1 Vòng lặp chính (ghép hai thể loại)

```
Lặn ban ngày (phiêu lưu, roguelite nhẹ) → cá, nguyên liệu
      ↓
Quán sushi buổi tối (quản lý, phục vụ theo thời gian) → tiền, follower, uy tín
      ↓
Nâng cấp (đồ lặn, vũ khí, nhân viên, món) → lặn sâu hơn, gặp cá hiếm hơn, món đắt hơn
      ↺  cộng thêm cốt truyện theo chương để luôn có thứ mới
```

Mỗi ngày gồm lượt lặn sáng, lượt lặn chiều (không bắt buộc), rồi mở quán tối. Lặn đêm có loài cá khác lặn ngày. Mỗi nửa của vòng lặp tạo ra thứ nửa kia cần: cá cho quán, tiền cho đồ lặn.

### 2.2 Phần lặn

- **Oxy cũng là máu.** Bị cá cắn thì mất oxy. Hết oxy thì ngất, mất gần hết đồ, chỉ được giữ lại 1 món. Mọi quyết định xoay quanh việc nên lặn tiếp hay quay lên.
- **Giới hạn mang:** thùng hàng có tải trọng, mang quá thì bơi chậm. Có thể gửi đồ lên trước bằng drone hoặc thùng tiếp tế.
- **Cách bắt khác nhau cho chất lượng khác nhau:** dùng xiên hoặc súng thì cá chết. Bắt bằng lưới thì cá còn sống, nguyên liệu được nhiều sao hơn và có thể nuôi ở trại cá.
- **Blue Hole đổi địa hình mỗi lần lặn** (bán procedural).
- **Tầng biển chia theo độ sâu:** nông (khoảng 0–50m), giữa (khoảng 50–130m), rồi sâu hơn. Muốn xuống sâu phải nâng cấp bộ đồ lặn. Vùng băng và làng Sea People mở theo chương truyện.
- **Điểm nhấn:** boss (cá mập, mực khổng lồ...), cá huyền thoại, mini-game, bộ sưu tập loài cá.

### 2.3 Phần quán

- **Chọn menu trước giờ mở** từ kho cá đã bắt. Số slot món có giới hạn.
- **Phục vụ:** Bancho nấu, Dave bưng ra. Có mini-game rót trà, mang wasabi. Khách có thanh kiên nhẫn.
- **Nhân viên:** thuê, huấn luyện, có kỹ năng riêng, tự động hóa dần.
- **Phát triển dài hạn:**
  - Nâng cấp món bằng nguyên liệu trùng.
  - App Cooksta đếm follower để lên hạng quán.
  - Khách VIP và tiệc theo chủ đề đòi đúng món.

### 2.4 Thế giới và phần meta

- Mọi tính năng quản lý nằm trong **điện thoại của Dave** dưới dạng app: shop đồ, Cooksta, trại cá, nông trại, sổ cá.
- **Dàn nhân vật lập dị:** Cobra (ông chủ), Bancho (đầu bếp), Duff (thợ chế đồ), Dr. Bacon (nhà nghiên cứu), Sato (trại cá).
- **Cốt truyện** kết hợp hài và bí ẩn: động đất, nền văn minh dưới biển, chủ đề sinh thái.
- **Bài học thiết kế:**
  - Game liên tục mở thêm tính năng mới. Người khen gọi đó là sự mới lạ liên tục, người chê nói game "rộng mà không sâu".
  - Riêng vòng lặp lặn → quán → nâng cấp thì gần như ai cũng khen.

## 3. Ghép Dave the Diver vào miền Tây

| Dave the Diver | Bản Chợ Nổi đề xuất |
|---|---|
| Blue Hole đổi địa hình mỗi lần lặn | **Mùa nước** đổi loài cá. Mùa nước nổi (tháng 7–11) có cá linh và bông điên điển, khớp đúng dữ liệu đang có. Mùa khô có cá lóc tát đìa. Nước ròng/nước lớn làm đổi độ sâu và dòng chảy. |
| Các tầng độ sâu | Mặt sông (lục bình, bông súng) → nước đục phù sa (cá linh theo đàn) → đáy bùn và gốc cây ngập (cá lóc, tôm càng) → khu mở rộng: rừng tràm, rừng đước Cà Mau, cửa biển (cá kèo, ba khía). |
| Xiên, lưới, bắt sống | Chĩa (nhanh, cá chết), lưới hoặc nơm (bắt sống, nguyên liệu tốt hơn), **đặt lọp/lờ** (thả hôm nay, thu hôm sau). |
| Drone gửi đồ lên trước | Xuồng ba lá neo giữa sông làm điểm gửi giỏ, giảm rủi ro mất hết đồ khi ngất. |
| Boss, cá huyền thoại | Cá tra dầu khổng lồ, cá hô (cá có thật ở sông Mekong). Chướng ngại: dòng xiết, sóng ghe máy, lưới ma, rác nhựa. |
| Quán sushi Bancho | Quán trên ghe ở bến Ninh Kiều. Lưu ý: chợ nổi Cái Răng thật ra họp **sáng sớm**. Muốn đúng thực tế thì gọi là "quán ghe tối", hoặc thêm cảnh bán sáng ở chợ. |
| Bảng menu | **Cây bẹo**: treo món gì lên bẹo thì khách thấy món đó. Hợp với cơ chế chọn menu và rất đặc trưng chợ nổi. |
| Mini-game rót trà, wasabi | Pha nước mắm me, rót cà phê phin, nướng trui cho vừa lửa. Nướng cháy có thể nối với `burn_s` (hiện đang `null`, có lẽ phase sau sẽ dùng). |
| Khách đi bộ vào quán | Khách **chèo xuồng cập ghe**, hết kiên nhẫn thì chèo đi. Phần hình ảnh này làm hoàn toàn bên UI. |
| Cooksta | Fanpage hoặc nhóm Zalo "Ăn gì miền Tây", nối với `reputation` 0–5. |
| Trại cá, nông trại | Bè cá Châu Đốc, vườn rau, miệt vườn trái cây. |
| Dàn nhân vật | Út Sen (thay Dave), chú Tư thương lái (thay Cobra, đặt hàng), anh Hai thợ hàn chế đồ lặn (thay Duff), Má Út đứng bếp (thay Bancho), cô sinh viên Đại học Cần Thơ ngành thủy sản (thay Dr. Bacon). |
| Bí ẩn Sea People | Di tích Óc Eo – Phù Nam dưới lòng sông, truyền thuyết Hà Bá. |
| Chủ đề sinh thái | Xâm nhập mặn, sạt lở, đập thượng nguồn làm cá linh ít dần. Đây là vấn đề thật và có sức nặng. |

## 4. Áp dụng vào project, theo thứ tự ưu tiên

### Bước 0: làm đúng phần lõi trước (Phase 1)

Đề đã có sẵn phần "xương" của Dave: oxy, ngạt, mất giỏ khi ngất, giỏ giới hạn, chọn món theo kho, khách có kiên nhẫn, uy tín. Test ẩn chiếm 25 điểm và phase sau chấm lại cả phase trước, nên cứ làm đúng contract.

Contract **khác** Dave ở 3 chỗ sau, nên giữ nguyên:

| Dave the Diver | Contract của mình |
|---|---|
| Oxy và máu gộp làm một | Oxy và Máu tách riêng (`hp_max = 3`, ngạt mỗi `choke_interval_ticks`) |
| Thùng hàng tính theo tải trọng | Giỏ đếm theo món, LIFO, `hold_capacity = 12` |
| Ngất được giữ lại 1 món | Ngất là mất hết, kho rỗng |

### Bước 1: phần "chất Dave" chỉ ở lớp hiển thị

Bước này không đụng tới sim nên an toàn tuyệt đối với headless. Sửa trong `chonoi/web/index.html` hoặc client riêng của nhóm:
- Màu nước đục dần theo `d`, thanh oxy nhấp nháy khi thấp, rung màn khi `choke`.
- Cảnh chuyển "Sáng → Tối" kèm một câu thoại của Má Út.
- Khách chèo xuồng tới; cây bẹo treo các món nấu được với kho hiện tại.
- Sổ cá: mở khóa một loài khi có sự kiện `fish_caught` đầu tiên của loài đó.

### Bước 2: khi có chế độ `day`, làm đầy đủ vòng Dave

- Tiền buổi tối dùng để mua nâng cấp: bình hơi (tăng `oxygen_max_s`), giỏ lớn hơn (`hold_capacity`), thêm bếp.
- Đặt dữ liệu nâng cấp trong một file dữ liệu riêng của nhóm, chỉ đọc ở chế độ live, để không phải sửa `game.contract.json` trước khi cả nhóm đồng ý.

### Bước 3: chỉ làm nếu còn thời gian

Mỗi mục bật bằng cờ riêng (ví dụ `--creative`), mặc định tắt:
- Mùa nước đổi bảng cá. Ngẫu nhiên vẫn đi qua `Streams` để giữ tất định.
- Lọp thả qua ngày; bắt sống bằng lưới cho thêm sao.
- Cá tra dầu làm "boss" để né tránh.
- Ghi tất cả vào mục "Sáng tạo của nhóm" trong README.

### Nên tránh

- Đừng chạy theo độ rộng của Dave: nhân viên, nông trại, trại cá, cốt truyện nhiều chương.
- Lý do: lab chỉ có 3 giờ, rubric không cộng điểm cho độ phức tạp, và chính Dave cũng bị chê vì nhồi quá nhiều tính năng.
- Một vòng sáng → tối → nâng cấp thật mượt, cộng thêm không khí miền Tây, sẽ giá trị hơn nhiều.

> Lưu ý về nguồn: số mét của các tầng biển và số chương mở vùng băng mỗi nguồn ghi một khác. Tài liệu này dùng chúng để minh họa cấu trúc, không phải số liệu chính xác.

## Nguồn

- [Wikipedia: Dave the Diver](https://en.wikipedia.org/wiki/Dave_the_Diver)
- [Steam: DAVE THE DIVER](https://store.steampowered.com/app/1868140/DAVE_THE_DIVER)
- [Nintendo: Dive by day, serve sushi by night](https://nintendo.com/us/whatsnew/dive-by-day-serve-sushi-by-night-the-adventure-rpg-management-mashup-is-here)
- [AV Club: Dive, Gather, Filet: the gameplay loop](https://www.avclub.com/dave-the-diver-review-gameplay-loop-roguelike-fish-restaurant-management)
- [Destructoid review](https://www.destructoid.com/review-dave-the-diver/)
- [Shacknews review](https://www.shacknews.com/article/136261/dave-the-diver-review-score)
- [Game Developer: Dave the Diver design](https://gamedeveloper.com/design/dave-the-diver)
- [PC Gamer](https://pcgamer.com/dave-the-diver-is-exactly-the-kind-of-out-of-nowhere-hit-that-makes-gaming-exciting)
- [Epic: five things we adore](https://store.epicgames.com/news/dave-the-diver-five-things-we-adore)
- [Pro Game Guides: underwater map](https://progameguides.com/dave-the-diver/dave-the-diver-map-all-underwater-locations)
- [Fandom: Blue Hole Shallows](https://dave-the-diver.fandom.com/wiki/Blue_Hole_Shallows), [Glacial Area](https://dave-the-diver.fandom.com/wiki/Glacial_Area)
- [Earlyguides: maps](https://earlyguides.com/dave-the-diver/maps)
- [The Review Geek: Chapter 1 walkthrough](https://www.thereviewgeek.com/davethediver-walkthrough-chapter1/)
