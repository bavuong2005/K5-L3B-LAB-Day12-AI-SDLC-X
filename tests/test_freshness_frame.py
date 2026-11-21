"""TV6 khung Phase 3 (T306/T330/T331 + gather.hold load): day/shop/bàn giao + API TV1.

quan.stock/reserved v1.2: nguồn sự thật là TV3 (`_validate_quan`) — không kiểm lại ở đây.
"""

import filecmp
import json
import os
import shutil
import subprocess
import tempfile
import unittest

from chonoi.errors import BadInput
from chonoi.ids import IdAllocator
from chonoi.inventory import (FRESH_SCALE, fresh_to_units, read_inventory, uses_individuals,
                              validate_individuals, write_inventory)
from chonoi.runner import Session
from chonoi.scenario import UNITS_PER_POINT, fresh_units, is_v12, load_scenario
from chonoi.sim.day import DaySim, DayState
from chonoi.sim.shop import ShopSim
from helpers import ROOT, Workdir, events, frames, headless_cmd, read_jsonl, snapshots, write_json

FIXTURE_V11 = os.path.join(ROOT, "tests", "fixtures", "contract-v1.1-day.json")
FIXTURE_V12 = os.path.join(ROOT, "tests", "fixtures", "contract-v1.2-freshness.json")
SC_GATHER_V12 = os.path.join(ROOT, "tests", "fixtures", "scenario-gather-hold-v12.json")
INV_V12 = os.path.join(ROOT, "tests", "fixtures", "inventory-items-v12.json")


def _tuning_v12():
    with open(FIXTURE_V12, encoding="utf-8") as f:
        return json.load(f)["tuning"]


def run_headless(*args, contract=None):
    env = dict(os.environ)
    if contract:
        env["CHONOI_CONTRACT"] = contract
    p = subprocess.run([*headless_cmd(), *args], cwd=ROOT, capture_output=True, text=True, env=env)
    return p.returncode, p.stderr


class Tv1ApiHelpersTest(unittest.TestCase):
    def test_is_v12_delegates_to_uses_individuals(self):
        self.assertFalse(is_v12("1.1"))
        self.assertTrue(is_v12("1.2"))
        self.assertEqual(is_v12("1.2"), uses_individuals("1.2"))
        self.assertEqual(UNITS_PER_POINT, FRESH_SCALE)
        self.assertEqual(fresh_units(30), fresh_to_units(30))
        self.assertEqual(fresh_units(30), 7200)

    def test_validate_individuals_and_roundtrip_file(self):
        with open(INV_V12, encoding="utf-8") as f:
            raw = json.load(f)["items"]
        items = validate_individuals(raw)
        self.assertEqual([it["id"] for it in items], ["I1", "I2"])
        with Workdir() as w:
            path = w.path("inv.json")
            write_inventory(path, items, version="1.2")
            loaded = read_inventory(path, version="1.2")
            self.assertEqual(loaded, items)
            with self.assertRaises(BadInput):
                read_inventory(path, version="1.1")  # mảng cá thể bị từ chối ở v1.1


class GatherHoldScenarioTest(unittest.TestCase):
    """gather.hold cá thể qua load_scenario (không đụng quan — TV3)."""

    def test_load_keeps_individual_hold(self):
        t = _tuning_v12()
        sc = load_scenario(SC_GATHER_V12, "gather", t, "1.2")
        self.assertEqual(sc["hold"][0]["id"], "I1")
        self.assertEqual(sc["hold"][0]["kind"], "ca_linh")

    def test_duplicate_hold_id_exit_bad_input(self):
        t = _tuning_v12()
        with Workdir() as w:
            path = write_json(w.path("sc.json"), {"gather": {
                "hold": [{"id": "I1", "kind": "ca_loc", "fresh": 100},
                         {"id": "I1", "kind": "ca_linh", "fresh": 90}],
                "random_fish": False,
            }})
            with self.assertRaises(BadInput) as cm:
                load_scenario(path, "gather", t, "1.2")
            self.assertIn("trùng", str(cm.exception))


class SessionContractVersionTest(unittest.TestCase):
    """T306: Session nhận `contract_version` (TV1), ghi kho qua write_inventory(version=)."""

    def test_gather_inventory_out_v12_writes_individuals(self):
        from chonoi.inputs import InputState
        t = _tuning_v12()
        with Workdir() as w:
            inv = w.path("inv.json")
            sc = {"hold": [{"id": "I1", "kind": "ca_loc", "fresh": 100}], "random_fish": False}
            sess = Session("gather", t, sc, 1, contract_version="1.2")
            idle = InputState((0, 0), frozenset(), frozenset())
            dock = InputState((0, 0), frozenset(), frozenset({"interact"}))
            while not sess.done and sess.tick < 5:
                sess.step(dock if sess.tick == 0 else idle)
            self.assertTrue(sess.done)
            sess.write_inventory_if_done(inv)
            loaded = read_inventory(inv, version="1.2")
            self.assertIsInstance(loaded, list)
            self.assertEqual(loaded[0]["id"], "I1")
            self.assertEqual(loaded[0]["kind"], "ca_loc")
            self.assertLess(loaded[0]["fresh"], 100)

    def test_tick_limit_does_not_write_inventory(self):
        from chonoi.inputs import InputState
        t = _tuning_v12()
        with Workdir() as w:
            inv = w.path("inv.json")
            write_json(inv, {"sentinel": True})
            sess = Session("gather", t, {"hold": [{"id": "I1", "kind": "ca_loc", "fresh": 100}],
                                         "random_fish": False}, 1, contract_version="1.2")
            idle = InputState((0, 0), frozenset(), frozenset())
            for _ in range(3):
                sess.step(idle)
            self.assertFalse(sess.done)
            sess.write_inventory_if_done(inv)
            with open(inv, encoding="utf-8") as f:
                self.assertEqual(json.load(f), {"sentinel": True})


class DayHandoffTest(unittest.TestCase):
    def test_gather_end_quan_same_tick_no_extra_step(self):
        """AC-P3-19 khung: gather_end và phase_start quan cùng tick; stock = inventory."""
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {
                "gather": {"hold": ["ca_loc", "bong_sung"], "random_fish": False},
                "quan": {"time_left_ticks": 1},
            })
            inp = write_json(w.path("i.json"), frames({"tick": 0, "interact": True}))
            out = w.path("o.jsonl")
            code, err = run_headless("--mode", "day", "--seed", "1", "--ticks", "5",
                                     "--scenario", sc, "--inputs", inp, "--out", out,
                                     contract=FIXTURE_V11)
            self.assertEqual(code, 0, err)
            rows = read_jsonl(out)
            ge = events(rows, "gather_end")[0]
            ps = [e for e in events(rows, "phase_start") if e["phase"] == "quan"][0]
            self.assertEqual(ge["tick"], ps["tick"])
            snap = next(s for s in snapshots(rows) if s["tick"] == ge["tick"] and s["phase"] == "quan")
            self.assertEqual(snap["phase_tick"], 0)
            self.assertEqual(snap["stock"], ge["data"]["inventory"]["items"])
            self.assertEqual(snap["stock"], {"bong_sung": 1, "ca_loc": 1})

    def test_day2_reallocates_hold_item_ids(self):
        t = _tuning_v12()
        from chonoi.rng import Streams
        ids = IdAllocator()
        sc = {"day": {}, "gather": {
            "hold": [{"id": "I1", "kind": "ca_linh", "fresh": 100},
                     {"id": "I2", "kind": "ca_loc", "fresh": 90}],
            "random_fish": False,
        }, "quan": {}}
        # version=None: suy từ hold cá thể (runner chưa truyền contract_version)
        day = DaySim(t, sc, Streams(1), ids, days=2, version=None)
        d1 = day._gather_scenario_for_day()
        self.assertEqual([it["id"] for it in d1["hold"]], ["I1", "I2"])
        day.day = 2
        d2 = day._gather_scenario_for_day()
        self.assertEqual([it["id"] for it in d2["hold"]], ["I3", "I4"])
        self.assertEqual([it["kind"] for it in d2["hold"]], ["ca_linh", "ca_loc"])
        self.assertEqual([it["fresh"] for it in d2["hold"]], [100, 90])
        self.assertEqual([it["id"] for it in day.tpl_gather["hold"]], ["I1", "I2"])

    def test_shop_individual_stock_does_not_decay(self):
        st = DayState(_tuning_v12(), {"money": 100, "earned": 100})
        items = [{"id": "I1", "kind": "ca_loc", "fresh": 50.0}]
        shop = ShopSim(_tuning_v12()["shop"], st, items)

        class _Inp:
            buy = None
            def pressed(self, _):
                return False
        for _ in range(10):
            shop.step(_Inp())
        self.assertEqual(shop.stock[0]["fresh"], 50.0)
        self.assertEqual(shop.snapshot()["stock"][0]["id"], "I1")


class RealContractSmokeTest(unittest.TestCase):
    def test_headless_gather_quan_day_real_contract(self):
        with Workdir() as w:
            g = w.path("g.jsonl")
            self.assertEqual(run_headless("--mode", "gather", "--seed", "1", "--ticks", "30",
                                          "--out", g)[0], 0)
            q = w.path("q.jsonl")
            inv = write_json(w.path("inv.json"), {"items": [{"id": "I1", "kind": "ca_loc", "fresh": 100}]})
            self.assertEqual(run_headless("--mode", "quan", "--seed", "1", "--ticks", "0",
                                          "--inventory", inv, "--out", q)[0], 0)
            d = w.path("d.jsonl")
            self.assertEqual(run_headless("--mode", "day", "--seed", "1", "--days", "1",
                                          "--ticks", "100", "--out", d)[0], 0)

    def test_day_two_runs_byte_identical(self):
        with Workdir() as w:
            a, b = w.path("a.jsonl"), w.path("b.jsonl")
            args = ["--mode", "day", "--seed", "1", "--days", "2", "--ticks", "50000", "--out"]
            for out in (a, b):
                code, err = run_headless(*args, out)
                self.assertEqual(code, 0, err)
            self.assertTrue(filecmp.cmp(a, b, shallow=False))


if __name__ == "__main__":
    unittest.main()
