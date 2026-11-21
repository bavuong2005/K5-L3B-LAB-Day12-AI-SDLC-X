# Bằng chứng Phase 4 (sinh bởi `.agents/skills/phase-proof/proof.sh 4`)

- Thời điểm: 2026-11-21 22:25:21
- Commit: `a5d5965` trên `NguyenMinhPhuc`
- contract_version: `1.3`

## [PASS] AC-P4 bench: python3 -m chonoi.bench --seed 42 --duration 30

```
$ sh -c python3 -m chonoi.bench --seed 42 --duration 30 --out docs/proof/phase-4/bench.json && cat docs/proof/phase-4/bench.json && python3 -c "
import json;r=json.load(open('docs/proof/phase-4/bench.json'));assert set(r)=={'avg_fps','p1_low_fps','frames','measured_s','load_ms'}
print('mốc: avg>=60',r['avg_fps']>=60,'| 1%low>=30',r['p1_low_fps']>=30,'| load<=10s',r['load_ms']<=10000)"
{"avg_fps": 4159.715211109234, "p1_low_fps": 1191.1222126424657, "frames": 124380, "measured_s": 29.901085455999933, "load_ms": 4}
mốc: avg>=60 True | 1%low>=30 True | load<=10s True
(exit 0)
```

## [PASS] AC-P4 soak: python3 -m chonoi.soak --seed 7 --days 10

```
$ sh -c python3 -m chonoi.soak --seed 7 --days 10 --out docs/proof/phase-4/soak.json && cat docs/proof/phase-4/soak.json && python3 -c "
import json;r=json.load(open('docs/proof/phase-4/soak.json'));assert r['days_completed']==r['days'] and r['crashes']==0"
{"days": 10, "days_completed": 10, "crashes": 0, "results": [{"day": 1, "earned": 0, "reputation": 3.0, "score": 300}, {"day": 2, "earned": 0, "reputation": 3.0, "score": 300}, {"day": 3, "earned": 0, "reputation": 3.0, "score": 300}, {"day": 4, "earned": 0, "reputation": 3.0, "score": 300}, {"day": 5, "earned": 0, "reputation": 3.0, "score": 300}, {"day": 6, "earned": 0, "reputation": 3.0, "score": 300}, {"day": 7, "earned": 0, "reputation": 3.0, "score": 300}, {"day": 8, "earned": 0, "reputation": 3.0, "score": 300}, {"day": 9, "earned": 0, "reputation": 3.0, "score": 300}, {"day": 10, "earned": 0, "reputation": 3.0, "score": 300}], "duration_s": 11.559813201999999}
(exit 0)
```

## [PASS] AC-P4 regression P1–P3 + runner P4 (toàn bộ unittest)

```
$ env PYTHONPATH=tests:. python3 -m unittest discover -s tests
..s.................................................................................................................s..s.s..........................................................................
----------------------------------------------------------------------
Ran 196 tests in 64.664s

OK (skipped=4)
(exit 0)
```

## Tổng kết

PASS — mọi bước đạt.
