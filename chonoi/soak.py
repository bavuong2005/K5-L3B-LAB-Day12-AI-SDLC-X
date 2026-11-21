"""Soak headless (TICKET-04). Mỗi Ngày đi gather → quan → shop, không pause.

python3 -m chonoi.soak --seed 7 --days 10 --out soak.json

Kế hoạch D1–D5 lặp ở Ngày 6–10. Bot đứng yên (không input) nên ca hết giờ vẫn đóng.
soak.json: days, days_completed, crashes, results[], duration_s.
Mỗi results[] có day, earned, reputation, score lúc Shop đóng.
"""

import argparse
import json
import math
import sys
import time

from .contract import DEFAULT_PATH, load_contract
from .errors import BadInput
from .ids import IdAllocator
from .inputs import InputState
from .rng import Streams
from .sim.day import DaySim, missing_day_keys

_IDLE = InputState((0.0, 0.0), frozenset(), frozenset())
_TICKS_PER_DAY_CAP = 30000


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        sys.stderr.write(f"lỗi: {message}\n")
        sys.exit(2)


def run_soak(seed, days, contract_path=None) -> dict:
    started = time.perf_counter()
    contract = load_contract(contract_path or DEFAULT_PATH)
    tuning = contract["tuning"]
    miss = missing_day_keys(tuning)
    if miss:
        raise BadInput(f"soak: contract chưa có khóa {', '.join(miss)}")
    if isinstance(days, bool) or not isinstance(days, int) or days < 1:
        raise BadInput("--days phải là số nguyên >= 1")
    sim = DaySim(tuning, {}, Streams(seed), IdAllocator(), days=days,
                 version=contract.get("contract_version"))
    mult = tuning["score"]["reputation_multiplier"]
    results = []
    crashes = 0
    steps = 0
    cap = days * _TICKS_PER_DAY_CAP
    try:
        while not sim.done and steps < cap:
            steps += 1
            closed_day = None
            for name, _data, _phase, day in sim.step(_IDLE):
                if name == "shop_end":
                    closed_day = day
            if closed_day is not None:
                earned = sim.state.earned
                reputation = sim.state.reputation
                results.append({
                    "day": closed_day,
                    "earned": earned,
                    "reputation": reputation,
                    "score": earned + mult * math.floor(reputation),
                })
        if not sim.done:
            crashes += 1
    except Exception:
        crashes += 1
    return {
        "days": days,
        "days_completed": sim.days_completed,
        "crashes": crashes,
        "results": results,
        "duration_s": time.perf_counter() - started,
    }


def main(argv=None) -> int:
    p = _Parser(prog="chonoi.soak")
    p.add_argument("--seed", required=True, type=int)
    p.add_argument("--days", required=True, type=int)
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    try:
        if a.days < 1:
            raise BadInput("--days phải là số nguyên >= 1")
        report = run_soak(a.seed, a.days)
    except BadInput as e:
        sys.stderr.write(f"đầu vào sai: {e}\n")
        return 2
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(report, f, ensure_ascii=False)
        f.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
