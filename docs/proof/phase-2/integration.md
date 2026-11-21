# Smoke tích hợp kho Phase 2

- Commit code được kiểm: `cd1c523` (`origin/main` tại lúc chạy).
- Gather: `python3 -m chonoi.headless --mode gather --seed 7 --ticks 1 --scenario docs/proof/phase-2/scenario.json --inputs docs/proof/phase-2/inputs.json --inventory-out docs/proof/phase-2/kho.json --out docs/proof/phase-2/integration-gather.jsonl` — exit 0, `gather_end` do cập bến.
- Quan: `python3 -m chonoi.headless --mode quan --seed 7 --ticks 0 --inventory docs/proof/phase-2/kho.json --out docs/proof/phase-2/integration-quan.jsonl` — exit 0.
- Kho xuất ra: `{"items":{"bong_sung":1,"ca_loc":1}}`; `stock` snapshot tick 0 của Quan khớp chính xác.

Fixture dùng `scenario.json` và `inputs.json` trong thư mục này.
