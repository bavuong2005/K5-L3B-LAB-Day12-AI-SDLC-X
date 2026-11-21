# Bằng chứng Phase 3 (sinh bởi `.agents/skills/phase-proof/proof.sh 3`)

- Thời điểm: 2026-11-21 22:27:31
- Commit: `a5d5965` trên `NguyenMinhPhuc`
- contract_version: `1.3`

## [PASS] AC-P3-08 scenario đề fresh 30 → spoiled tick 1

```
$ sh -c python3 -m chonoi.headless --mode gather --seed 1 --ticks 1 --scenario docs/proof/phase-3/scenario-spoiled.json --out docs/proof/phase-3/spoiled.jsonl && grep '"name":"spoiled"' docs/proof/phase-3/spoiled.jsonl | grep -q '"tick":1' && grep '"name":"spoiled"' docs/proof/phase-3/spoiled.jsonl
{"type":"event","tick":1,"phase":"gather","name":"spoiled","data":{"item_id":"I1","kind":"ca_linh","location":"hold"}}
(exit 0)
```

## [PASS] AC-P3-18 bàn giao: gather cập bến ghi kho.json

```
$ sh -c python3 -m chonoi.headless --mode gather --seed 1 --ticks 5 --scenario docs/proof/phase-3/scenario-handoff.json --inputs docs/proof/phase-3/inputs-dock.json --inventory-out docs/proof/phase-3/kho.json --out docs/proof/phase-3/handoff-gather.jsonl && cat docs/proof/phase-3/kho.json
{"items":[{"id":"I1","kind":"ca_linh","fresh":99.99166666666666}]}
(exit 0)
```

## [PASS] AC-P3-18 bàn giao: quan --inventory --ticks 0 khớp id/kind/fresh (±0.01)

```
$ sh -c python3 -m chonoi.headless --mode quan --seed 1 --ticks 0 --inventory docs/proof/phase-3/kho.json --out docs/proof/phase-3/handoff-quan.jsonl && python3 -c "
import json,sys
inv=json.load(open('docs/proof/phase-3/kho.json'))['items']
st=[json.loads(l) for l in open('docs/proof/phase-3/handoff-quan.jsonl') if '\"snapshot\"' in l][0]['stock']
ok=[(a['id'],a['kind']) for a in inv]==[(b['id'],b['kind']) for b in st] and all(abs(a['fresh']-b['fresh'])<=0.01 for a,b in zip(inv,st))
print('file :',inv);print('quan :',st);sys.exit(0 if ok else 1)"
file : [{'id': 'I1', 'kind': 'ca_linh', 'fresh': 99.99166666666666}]
quan : [{'id': 'I1', 'kind': 'ca_linh', 'fresh': 99.992}]
(exit 0)
```

## [PASS] AC-P3-03 kho đếm v1.0 → exit 2

```
$ sh -c echo '{"items":{"ca_loc":1}}' > docs/proof/phase-3/kho-dem.json; python3 -m chonoi.headless --mode quan --seed 1 --ticks 0 --inventory docs/proof/phase-3/kho-dem.json --out docs/proof/phase-3/x.jsonl; rc=$?; rm -f docs/proof/phase-3/x.jsonl; echo exit=$rc; [ $rc -eq 2 ]
đầu vào sai: contract từ v1.2 không nhận kho đếm; items phải là mảng cá thể
exit=2
(exit 0)
```

## [PASS] AC-P3-19 day --days 1 chạy hết Ngày

```
$ sh -c python3 -m chonoi.headless --mode day --days 1 --seed 1 --ticks 30000 --out docs/proof/phase-3/.day1.jsonl && tail -1 docs/proof/phase-3/.day1.jsonl; rc=$?; rm -f docs/proof/phase-3/.day1.jsonl; exit $rc
{"type":"end","ticks":22200,"sim_tick":22200,"mode":"day","state":"finished","reason":"days_complete","money":0,"earned":0,"reputation":3.0,"score":300,"days_completed":1}
(exit 0)
```

## [PASS] AC-P3-23 tất định: gather --ticks 600 (2 lần, cmp)

```
$ sh -c python3 -m chonoi.headless --mode gather --ticks 600 --seed 7 --out docs/proof/phase-3/.a.jsonl && python3 -m chonoi.headless --mode gather --ticks 600 --seed 7 --out docs/proof/phase-3/.b.jsonl && cmp docs/proof/phase-3/.a.jsonl docs/proof/phase-3/.b.jsonl && echo "giống hệt: $(wc -c < docs/proof/phase-3/.a.jsonl) byte"; rc=$?; rm -f docs/proof/phase-3/.a.jsonl docs/proof/phase-3/.b.jsonl; exit $rc
giống hệt:   111355 byte
(exit 0)
```

## [PASS] AC-P3-23 tất định: quan --ticks 600 (2 lần, cmp)

```
$ sh -c python3 -m chonoi.headless --mode quan --ticks 600 --seed 7 --out docs/proof/phase-3/.a.jsonl && python3 -m chonoi.headless --mode quan --ticks 600 --seed 7 --out docs/proof/phase-3/.b.jsonl && cmp docs/proof/phase-3/.a.jsonl docs/proof/phase-3/.b.jsonl && echo "giống hệt: $(wc -c < docs/proof/phase-3/.a.jsonl) byte"; rc=$?; rm -f docs/proof/phase-3/.a.jsonl docs/proof/phase-3/.b.jsonl; exit $rc
giống hệt:    37938 byte
(exit 0)
```

## [PASS] AC-P3-23 tất định: day --days 2 --ticks 30000 (2 lần, cmp)

```
$ sh -c python3 -m chonoi.headless --mode day --days 2 --ticks 30000 --seed 7 --out docs/proof/phase-3/.a.jsonl && python3 -m chonoi.headless --mode day --days 2 --ticks 30000 --seed 7 --out docs/proof/phase-3/.b.jsonl && cmp docs/proof/phase-3/.a.jsonl docs/proof/phase-3/.b.jsonl && echo "giống hệt: $(wc -c < docs/proof/phase-3/.a.jsonl) byte"; rc=$?; rm -f docs/proof/phase-3/.a.jsonl docs/proof/phase-3/.b.jsonl; exit $rc
giống hệt:  5162108 byte
(exit 0)
```

## [PASS] AC-P3-01…23 test chấp nhận hộp đen

```
$ env PYTHONPATH=tests:. python3 -m unittest tests.test_p3_acceptance
................
----------------------------------------------------------------------
Ran 16 tests in 6.296s

OK
(exit 0)
```

## Tổng kết

PASS — mọi bước đạt.
