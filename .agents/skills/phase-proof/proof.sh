#!/usr/bin/env bash
# phase-proof: sinh bằng chứng CLI cho phase 3 / 4 vào docs/proof/phase-N/.
# Dùng: .agents/skills/phase-proof/proof.sh <3|4>   (env: BENCH_S=30 SOAK_DAYS=2)
set -u
PHASE="${1:-}"
case "$PHASE" in 3|4) ;; *) echo "Dùng: $0 <3|4>" >&2; exit 2 ;; esac
[ -f game.contract.json ] || { echo "Chạy từ gốc repo" >&2; exit 2; }

DIR="docs/proof/phase-$PHASE"; mkdir -p "$DIR"
REPORT="$DIR/proof.md"
cfg() { python3 -c "import json;print(json.load(open('game.contract.json'))['$1'])"; }
H="$(cfg headless_cmd)"
FAILS=0
{
  echo "# Bằng chứng Phase $PHASE (sinh bởi \`.agents/skills/phase-proof/proof.sh $PHASE\`)"
  echo
  echo "- Thời điểm: $(date '+%Y-%m-%d %H:%M:%S')"
  echo "- Commit: \`$(git rev-parse --short HEAD 2>/dev/null)\` trên \`$(git rev-parse --abbrev-ref HEAD 2>/dev/null)\`$(git diff --quiet HEAD -- chonoi game.contract.json 2>/dev/null || echo ' (có thay đổi chưa commit trong chonoi/ hoặc contract)')"
  echo "- contract_version: \`$(cfg contract_version)\`"
  echo
} > "$REPORT"

step() { # $1 = mô tả, $2.. = lệnh
  local desc="$1"; shift
  local out rc
  out="$("$@" 2>&1)"; rc=$?
  local tag=PASS; [ $rc -eq 0 ] || { tag=FAIL; FAILS=$((FAILS+1)); }
  { echo "## [$tag] $desc"; echo; echo '```'; echo "\$ $*"; [ -n "$out" ] && echo "$out" | tail -15; echo "(exit $rc)"; echo '```'; echo; } >> "$REPORT"
  echo "[$tag] $desc"
}

if [ "$PHASE" = 3 ]; then
  echo '{"gather":{"hold":[{"id":"I1","kind":"ca_linh","fresh":30}],"random_fish":false,"monsters":[]}}' > "$DIR/scenario-spoiled.json"
  echo '{"gather":{"hold":[{"id":"I1","kind":"ca_linh","fresh":100}],"random_fish":false,"monsters":[]}}' > "$DIR/scenario-handoff.json"
  echo '{"frames":[{"tick":0,"interact":true}]}' > "$DIR/inputs-dock.json"
  rm -f "$DIR/kho.json"
  # shellcheck disable=SC2086
  step "AC-P3-08 scenario đề fresh 30 → spoiled tick 1" sh -c "$H --mode gather --seed 1 --ticks 1 --scenario $DIR/scenario-spoiled.json --out $DIR/spoiled.jsonl && grep '\"name\":\"spoiled\"' $DIR/spoiled.jsonl | grep -q '\"tick\":1' && grep '\"name\":\"spoiled\"' $DIR/spoiled.jsonl"
  step "AC-P3-18 bàn giao: gather cập bến ghi kho.json" sh -c "$H --mode gather --seed 1 --ticks 5 --scenario $DIR/scenario-handoff.json --inputs $DIR/inputs-dock.json --inventory-out $DIR/kho.json --out $DIR/handoff-gather.jsonl && cat $DIR/kho.json"
  step "AC-P3-18 bàn giao: quan --inventory --ticks 0 khớp id/kind/fresh (±0.01)" sh -c "$H --mode quan --seed 1 --ticks 0 --inventory $DIR/kho.json --out $DIR/handoff-quan.jsonl && python3 -c \"
import json,sys
inv=json.load(open('$DIR/kho.json'))['items']
st=[json.loads(l) for l in open('$DIR/handoff-quan.jsonl') if '\\\"snapshot\\\"' in l][0]['stock']
ok=[(a['id'],a['kind']) for a in inv]==[(b['id'],b['kind']) for b in st] and all(abs(a['fresh']-b['fresh'])<=0.01 for a,b in zip(inv,st))
print('file :',inv);print('quan :',st);sys.exit(0 if ok else 1)\""
  step "AC-P3-03 kho đếm v1.0 → exit 2" sh -c "echo '{\"items\":{\"ca_loc\":1}}' > $DIR/kho-dem.json; $H --mode quan --seed 1 --ticks 0 --inventory $DIR/kho-dem.json --out $DIR/x.jsonl; rc=\$?; rm -f $DIR/x.jsonl; echo exit=\$rc; [ \$rc -eq 2 ]"
  step "AC-P3-19 day --days 1 chạy hết Ngày" sh -c "$H --mode day --days 1 --seed 1 --ticks 30000 --out $DIR/.day1.jsonl && tail -1 $DIR/.day1.jsonl; rc=\$?; rm -f $DIR/.day1.jsonl; exit \$rc"
  for m in "gather --ticks 600" "quan --ticks 600" "day --days 2 --ticks 30000"; do
    step "AC-P3-23 tất định: $m (2 lần, cmp)" sh -c "$H --mode $m --seed 7 --out $DIR/.a.jsonl && $H --mode $m --seed 7 --out $DIR/.b.jsonl && cmp $DIR/.a.jsonl $DIR/.b.jsonl && echo \"giống hệt: \$(wc -c < $DIR/.a.jsonl) byte\"; rc=\$?; rm -f $DIR/.a.jsonl $DIR/.b.jsonl; exit \$rc"
  done
  step "AC-P3-01…23 test chấp nhận hộp đen" env PYTHONPATH=tests:. python3 -m unittest tests.test_p3_acceptance
fi

if [ "$PHASE" = 4 ]; then
  B="$(cfg bench_cmd)"; S="$(cfg soak_cmd)"
  step "AC-P4 bench: $B --seed 42 --duration ${BENCH_S:-30}" sh -c "$B --seed 42 --duration ${BENCH_S:-30} --out $DIR/bench.json && cat $DIR/bench.json && python3 -c \"
import json;r=json.load(open('$DIR/bench.json'));assert set(r)=={'avg_fps','p1_low_fps','frames','measured_s','load_ms'}
print('mốc: avg>=60',r['avg_fps']>=60,'| 1%low>=30',r['p1_low_fps']>=30,'| load<=10s',r['load_ms']<=10000)\""
  step "AC-P4 soak: $S --seed 7 --days ${SOAK_DAYS:-2}" sh -c "$S --seed 7 --days ${SOAK_DAYS:-2} --out $DIR/soak.json && cat $DIR/soak.json && python3 -c \"
import json;r=json.load(open('$DIR/soak.json'));assert r['days_completed']==r['days'] and r['crashes']==0\""
  step "AC-P4 regression P1–P3 + runner P4 (toàn bộ unittest)" env PYTHONPATH=tests:. python3 -m unittest discover -s tests
fi

{ echo "## Tổng kết"; echo; [ $FAILS -eq 0 ] && echo "PASS — mọi bước đạt." || echo "FAIL — $FAILS bước lỗi."; } >> "$REPORT"
echo "Đã ghi $REPORT"
[ $FAILS -eq 0 ]
