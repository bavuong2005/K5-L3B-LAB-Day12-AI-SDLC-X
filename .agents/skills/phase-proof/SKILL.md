---
name: phase-proof
description: Sinh bằng chứng thật cho docs/verification/phase-N.md. Dùng khi QA chốt một phase (trước khi báo TV1 gắn tag), khi cần điền ma trận AC → bằng chứng, hoặc khi được hỏi "AC này có chạy thật không". Chạy smoke CLI theo đề (bàn giao kho, day, cmp tất định, bench, soak) và lưu lệnh + đầu ra vào docs/proof/phase-N/.
---

# phase-proof

`pre-push-check` trả lời câu "được push chưa". Skill này trả lời câu khác: **AC của phase có bằng chứng chạy thật trên commit nào?**

## Lệnh (từ gốc repo)
```bash
.agents/skills/phase-proof/proof.sh 3      # TICKET-03: bàn giao file, spoiled, day, cmp
.agents/skills/phase-proof/proof.sh 4      # TICKET-04: bench seed 42, soak, regression
BENCH_S=30 .agents/skills/phase-proof/proof.sh 4   # bench đủ 30 s như đề (mặc định 30)
SOAK_DAYS=10 .agents/skills/phase-proof/proof.sh 4 # soak 10 Ngày như giảng viên (mặc định 2)
```

## Đầu ra
- `docs/proof/phase-N/proof.md`: commit, thời điểm, từng lệnh, mã thoát, `[PASS]/[FAIL]`.
- Các file thô cạnh đó (`*.jsonl`, `kho.json`, `bench.json`, `soak.json`) để người chấm mở ra xem.
- Exit 0 khi mọi bước PASS, ngược lại exit 1.

## Quy tắc khi điền verification
- Mỗi dòng AC trỏ tới **tên test** hoặc **file trong docs/proof/** + kết quả. Chỉ ghi "Đạt" khi đã chạy thật.
- FAIL thì ghi "Chưa đạt" kèm lý do. **Không sửa test cho xanh** (AGENTS.md).
- Commit trong `proof.md` phải khớp commit bàn giao. Nếu code đổi sau đó thì chạy lại skill.
