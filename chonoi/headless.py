"""Điểm vào headless: python3 -m chonoi.headless --mode gather --seed 1 --ticks 600 --out out.jsonl

Mã thoát: 0 bình thường; 2 tham số/đầu vào sai (kiểm TRƯỚC khi ghi đầu ra); 1 lỗi chạy/ghi.

v1.1 (TV6, T240): `--mode day [--days N]` (1–5, mặc định 1); `--days` với mode khác, `--inventory*` với day,
contract thiếu khóa v1.1 (`tuning.day_plan`, `tuning.shop`) → mã 2. Biến môi trường `CHONOI_CONTRACT` (tùy chọn)
trỏ tới contract khác `game.contract.json` — chỉ để test dùng fixture v1.1 khi TV1 chưa nâng contract.
"""

import argparse
import math
import os
import sys

from . import leaderboard
from .contract import DEFAULT_PATH, load_contract
from .errors import BadInput
from .inputs import buttons_for, load_frames
from .inventory import menu_kinds, read_inventory
from .runner import run
from .scenario import load_scenario
from .sim.day import missing_day_keys


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        sys.stderr.write(f"lỗi: {message}\n")
        sys.exit(2)


def _int(name):
    def conv(s):
        try:
            return int(s)
        except ValueError:
            raise argparse.ArgumentTypeError(f"{name} phải là số nguyên")
    return conv


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    exported = leaderboard.handle_export(argv, None)  # mở rộng `leaderboard`: chỉ khi có cờ xuất
    if exported is not None:
        return exported
    p = _Parser(prog="chonoi.headless")
    p.add_argument("--mode", required=True, choices=["gather", "quan", "day"])  # `day` có từ v1.1
    p.add_argument("--days", type=_int("days"), default=None)  # v1.1, chỉ với day
    p.add_argument("--seed", required=True, type=_int("seed"))
    p.add_argument("--ticks", required=True, type=_int("ticks"))
    p.add_argument("--out", required=True)
    p.add_argument("--scenario")
    p.add_argument("--inputs")
    p.add_argument("--inventory")
    p.add_argument("--inventory-out", dest="inventory_out")
    p.add_argument("--leaderboard")  # mở rộng `leaderboard`: đi cặp với --player-name, chỉ mode day
    p.add_argument("--player-name", dest="player_name")
    p.add_argument("--snapshot-every", dest="snapshot_every", type=_int("snapshot-every"), default=10)
    a = p.parse_args(argv)
    try:
        if (a.leaderboard is None) != (a.player_name is None):
            raise BadInput("--leaderboard và --player-name phải đi cặp")
        if a.leaderboard is not None:
            if a.mode != "day":
                raise BadInput("--leaderboard chỉ dùng với --mode day")
            if not a.player_name.strip():
                raise BadInput("--player-name phải khác rỗng")
            if os.path.abspath(a.leaderboard) in [os.path.abspath(x) for x in (a.out, a.scenario, a.inputs) if x]:
                raise BadInput("--leaderboard phải khác các đường dẫn khác")
            leaderboard.load(a.leaderboard)  # store hỏng -> mã 2 trước khi ghi đầu ra
        if a.days is not None and a.mode != "day":
            raise BadInput("--days chỉ dùng với --mode day")
        days = 1 if a.days is None else a.days
        if not (1 <= days <= 5):
            raise BadInput("--days phải là số nguyên từ 1 đến 5")
        if a.mode == "day" and (a.inventory or a.inventory_out):
            raise BadInput("--inventory/--inventory-out không dùng với day (day bàn giao kho trong bộ nhớ)")
        if a.ticks < 0:
            raise BadInput("--ticks phải >= 0")
        if a.snapshot_every <= 0:
            raise BadInput("--snapshot-every phải > 0")
        if a.inventory and a.mode != "quan":
            raise BadInput("--inventory chỉ dùng với quan")
        if a.inventory_out and a.mode != "gather":
            raise BadInput("--inventory-out chỉ dùng với gather")
        outs = [x for x in (a.out, a.inventory_out) if x]
        ins = [x for x in (a.scenario, a.inputs, a.inventory) if x]
        paths = [os.path.abspath(x) for x in outs + ins]
        if len(set(paths)) != len(paths):
            raise BadInput("các đường dẫn đầu vào/đầu ra phải khác nhau")
        contract = load_contract(os.environ.get("CHONOI_CONTRACT") or DEFAULT_PATH)
        tuning = contract["tuning"]
        if a.mode == "day":
            miss = missing_day_keys(tuning)
            if miss:
                raise BadInput(f"--mode day: contract chưa có khóa {', '.join(miss)} (chờ TV1)")
        buttons, strings = buttons_for(contract)
        scenario = load_scenario(a.scenario, a.mode, tuning, contract["contract_version"])
        frames = load_frames(a.inputs, buttons, strings)
        inventory = read_inventory(a.inventory, version=contract["contract_version"]) if a.inventory else None
        if inventory is not None and "stock" in scenario:
            raise BadInput("vừa có quan.stock vừa có --inventory")
    except BadInput as e:
        sys.stderr.write(f"đầu vào sai: {e}\n")
        return 2
    try:
        sim = run(a.mode, tuning, scenario, a.seed, frames, a.ticks, a.out, a.snapshot_every,
            inventory=inventory, inventory_out=a.inventory_out, days=days, buttons=buttons, strings=strings,
            contract_version=contract["contract_version"])
        # ghi đúng một mục: chạy đủ 5 Ngày chuẩn (không scenario), reason days_complete
        if (a.leaderboard and not a.scenario and days == 5 and sim.done
                and sim.reason == "days_complete" and sim.days_completed == 5):
            score = sim.earned + tuning["score"]["reputation_multiplier"] * math.floor(sim.reputation)
            leaderboard.add(a.leaderboard, a.player_name, score, sim.days_completed, a.seed)
    except BadInput as e:  # lỗi mức luật phát hiện lúc dựng sim
        sys.stderr.write(f"đầu vào sai: {e}\n")
        return 2
    except OSError as e:
        sys.stderr.write(f"lỗi ghi: {e}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
