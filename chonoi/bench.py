"""Benchmark có render (TICKET-04). Út Sen đứng yên ở bến, cảnh gather 1280×720.

python3 -m chonoi.bench --seed 42 --duration 30 --out bench.json

Làm nóng 3 giây rồi đo `duration` giây đồng hồ. JSON có avg_fps, p1_low_fps,
frames, measured_s, load_ms. Mốc avg ≥ 60, 1% low ≥ 30, load ≤ 10 s chỉ để báo cáo.
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
from .sim.gather import GatherSim

WIDTH, HEIGHT = 1280, 720
WARMUP_S = 3.0
_IDLE = InputState((0.0, 0.0), frozenset(), frozenset())


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        sys.stderr.write(f"lỗi: {message}\n")
        sys.exit(2)


def _plot(buf, x, d, bounds, value):
    x0, x1 = bounds["x"]
    d0, d1 = bounds["d"]
    px = int((float(x) - x0) / (x1 - x0) * (WIDTH - 1))
    py = int((float(d) - d0) / (d1 - d0) * (HEIGHT - 1))
    for dy in range(-1, 2):
        yy = py + dy
        if yy < 0 or yy >= HEIGHT:
            continue
        row = yy * WIDTH
        for dx in range(-1, 2):
            xx = px + dx
            if 0 <= xx < WIDTH:
                buf[row + xx] = value


def _draw(buf, blank, sim):
    buf[:] = blank
    bounds = sim.t["bounds"]
    fresh = sim.tuning_fresh if sim.tuning_fresh else None
    if fresh:
        span = int(WIDTH * float(fresh["initial"]) / 100)
        buf[:span] = b"\x40" * span
    _plot(buf, sim.pos[0], sim.pos[1], bounds, 255)
    for fish in sim.fish:
        _plot(buf, fish["pos"][0], fish["pos"][1], bounds, 180)
    for monster in sim.monsters:
        _plot(buf, monster["pos"][0], monster["pos"][1], bounds, 220)


def measure(seed, duration_s, warmup_s=WARMUP_S, contract_path=None) -> dict:
    started = time.perf_counter()
    contract = load_contract(contract_path or DEFAULT_PATH)
    tuning = contract["tuning"]
    sim = GatherSim(tuning, {}, Streams(seed), IdAllocator(),
                    contract_version=contract.get("contract_version"))
    sim.tuning_fresh = tuning.get("freshness")
    blank = bytes(WIDTH * HEIGHT)
    buf = bytearray(blank)
    _draw(buf, blank, sim)
    load_ms = int(round((time.perf_counter() - started) * 1000))

    def frames_for(seconds):
        times = []
        end = time.perf_counter() + seconds
        while time.perf_counter() < end:
            t0 = time.perf_counter()
            sim.step(_IDLE)
            _draw(buf, blank, sim)
            times.append(time.perf_counter() - t0)
        return times

    if warmup_s > 0:
        frames_for(warmup_s)
    samples = frames_for(duration_s)
    frames = len(samples)
    measured_s = sum(samples)
    if frames == 0 or measured_s <= 0:
        raise BadInput("không đo được khung hình")
    slow_n = max(1, math.ceil(0.01 * frames))
    slowest = sorted(samples, reverse=True)[:slow_n]
    return {
        "avg_fps": frames / measured_s,
        "p1_low_fps": slow_n / sum(slowest),
        "frames": frames,
        "measured_s": measured_s,
        "load_ms": load_ms,
    }


def main(argv=None) -> int:
    p = _Parser(prog="chonoi.bench")
    p.add_argument("--seed", required=True, type=int)
    p.add_argument("--duration", required=True, type=float)
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    try:
        if a.duration <= 0:
            raise BadInput("--duration phải > 0")
        report = measure(a.seed, a.duration)
    except BadInput as e:
        sys.stderr.write(f"đầu vào sai: {e}\n")
        return 2
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(report, f, ensure_ascii=False)
        f.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
