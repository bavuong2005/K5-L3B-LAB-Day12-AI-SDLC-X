"""TV5 — bổ sung AC Phase 2 còn thiếu bằng chứng (verification phase-2: AC-P2-03…06, 16).

Chạy headless thật với game.contract.json thật; số liệu đọc từ tuning, không hard-code luật.
Chạy: PYTHONPATH=tests:. python3 -m unittest tests.test_p2_acceptance -v
"""

import json
import math
import os
import unittest

from chonoi.contract import load_contract
from chonoi.ids import IdAllocator
from chonoi.inputs import InputState
from chonoi.rng import Streams
from chonoi.sim.quan import QuanSim

from helpers import ROOT, Workdir, events, read_jsonl, run_headless, snapshots, write_json

TUNING = load_contract(os.path.join(ROOT, "game.contract.json"))["tuning"]
G = TUNING["gather"]
EPS = 0.002  # JSONL làm tròn 3 chữ số


def gather_rows(w, ticks, seed=3, scenario=None, every=1):
    out = w.path("g.jsonl")
    args = ["--mode", "gather", "--seed", str(seed), "--ticks", str(ticks), "--out", out,
            "--snapshot-every", str(every)]
    if scenario is not None:
        args += ["--scenario", write_json(w.path("sc.json"), scenario)]
    code, err = run_headless(*args)
    assert code == 0, err
    return read_jsonl(out)


class AcP2Fish(unittest.TestCase):
    def test_ac_p2_03_tick_0_co_8_dan_o_8_diem_khac_nhau_dung_dai(self):
        for seed in (1, 2, 3, 42):
            with self.subTest(seed=seed), Workdir() as w:
                fish = snapshots(gather_rows(w, 0, seed=seed))[0]["fish"]
                self.assertEqual(len(fish), G["fish_initial"])
                self.assertEqual(len({tuple(f["pos"]) for f in fish}), len(fish))
                for f in fish:
                    self.assertIn(f["pos"][0], G["fish_spawn_x"])
                    self.assertIn(f["pos"][1], G["fish_spawn_depths"][f["kind"]])

    def test_ac_p2_04_boi_1_5_ms_doi_huong_moi_120_tick_va_o_trong_dai(self):
        step = G["fish_speed"] / 60
        x_lo, x_hi = G["fish_x"]
        with Workdir() as w:
            snaps = snapshots(gather_rows(w, 600, scenario={"gather": {"monsters": []}}))
        initial = {f["id"] for f in snaps[0]["fish"]}
        reflected = 0
        for prev, cur in zip(snaps, snaps[1:]):
            before = {f["id"]: f for f in prev["fish"]}
            for f in cur["fish"]:
                if f["id"] not in initial or f["id"] not in before:
                    continue
                p = before[f["id"]]
                d_lo, d_hi = G["fish_depths"][f["kind"]]
                self.assertTrue(x_lo - EPS <= f["pos"][0] <= x_hi + EPS and d_lo - EPS <= f["pos"][1] <= d_hi + EPS)
                near_edge = (min(f["pos"][0] - x_lo, x_hi - f["pos"][0]) <= step + EPS
                             or min(f["pos"][1] - d_lo, d_hi - f["pos"][1]) <= step + EPS)
                moved = math.dist(p["pos"], f["pos"])
                if near_edge:
                    reflected += 1
                    self.assertLessEqual(moved, step + EPS)
                    continue
                self.assertAlmostEqual(moved, step, delta=EPS)
                if abs(f["heading_deg"] - p["heading_deg"]) > 1e-6:
                    age_before = p["age_ticks"]
                    self.assertTrue(age_before > 0 and age_before % G["fish_turn_ticks"] == 0,
                                    f"{f['id']} đổi hướng ở age {age_before}")
        self.assertGreater(reflected, 0, "kịch bản 600 tick nên có ít nhất một lần chạm mép")

    def test_ac_p2_05_sinh_ca_moi_360_tick_tran_12_clearance(self):
        with Workdir() as w:
            rows = gather_rows(w, 4000, scenario={"gather": {"monsters": []}}, every=360)
        spawned = events(rows, "fish_spawned")
        self.assertGreater(len(spawned), 0)
        self.assertEqual(len(spawned), G["fish_max"] - G["fish_initial"],
                         "4000 tick đủ 11 lượt; trần 12 phải chặn đúng ở 4 lần sinh")
        for e in spawned:
            self.assertEqual(e["tick"] % G["fish_spawn_ticks"], 0)
            self.assertIn(e["data"]["pos"][0], G["fish_spawn_x"])
            self.assertIn(e["data"]["pos"][1], G["fish_spawn_depths"][e["data"]["kind"]])
        for s in snapshots(rows):
            self.assertLessEqual(len(s["fish"]), G["fish_max"])

    def test_ac_p2_06_random_fish_false_dung_yen_khong_sinh(self):
        fixture = [{"id": "F1", "kind": "ca_loc", "pos": [50, 12]}]
        with Workdir() as w:
            rows = gather_rows(w, 1000, every=100, scenario={"gather": {"random_fish": False, "fish": fixture,
                                                                         "monsters": []}})
        self.assertEqual(events(rows, "fish_spawned"), [])
        for s in snapshots(rows):
            self.assertEqual([(f["id"], f["pos"]) for f in s["fish"]], [("F1", [50, 12])])


    def test_ac_p2_07_bat_dung_vi_tri_truoc_khi_boi_va_keo_yield_2(self):
        r = G["catch_radius"]
        sc = {"gather": {"player": {"pos": [50, 25]}, "monsters": [],
                         "fish": [{"id": "F1", "kind": "ca_keo", "pos": [50 + r, 25], "heading_deg": 0}]}}
        with Workdir() as w:  # đối chứng: không bắt thì đàn bơi ra ngoài tầm sau 1 bước
            idle = snapshots(gather_rows(w, 1, scenario=sc))[-1]["fish"][0]
        self.assertGreater(idle["pos"][0] - 50, r)
        with Workdir() as w:
            out = w.path("g.jsonl")
            code, err = run_headless("--mode", "gather", "--seed", "3", "--ticks", "1", "--out", out,
                                     "--scenario", write_json(w.path("sc.json"), sc),
                                     "--inputs", write_json(w.path("in.json"), {"frames": [{"tick": 0, "catch": True}]}))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(out)
        caught, = events(rows, "fish_caught")
        self.assertEqual(caught["data"], {"fish_id": "F1", "kind": "ca_keo", "yield": G["fish_yield"]["ca_keo"]})
        self.assertEqual([i["kind"] for i in snapshots(rows)[-1]["hold"]], ["ca_keo"] * G["fish_yield"]["ca_keo"])


class AcP2Quan(unittest.TestCase):
    def test_ac_p2_16_hai_bep_nau_song_song(self):
        def waiting(cid, table, iid):
            return {"id": cid, "table_id": table, "dish_id": "ca_loc_nuong_trui", "order_tick": 0,
                    "state": "waiting", "order_status": "reserved", "patience_ticks_left": 3600,
                    "eat_ticks_left": 0, "reserved": [iid]}
        stock = [{"id": "I1", "kind": "ca_loc", "fresh": 100}, {"id": "I2", "kind": "ca_loc", "fresh": 100}]
        sim = QuanSim(TUNING, {"random_customers": False, "stock": stock,
                               "customers": [waiting("C1", "T1", "I1"), waiting("C2", "T2", "I2")]},
                      Streams(1), IdAllocator())
        press = InputState((0, 0), frozenset(), frozenset({"interact"}))
        b1, b2 = sim.stoves
        sim.pos = list(b1["pos"])
        first = [d for n, d in sim.step(press) if n == "cook_started"]
        sim.pos = list(b2["pos"])
        second = [d for n, d in sim.step(press) if n == "cook_started"]
        self.assertEqual([(d["stove_id"], d["order_id"]) for d in first + second], [("B1", "C1"), ("B2", "C2")])
        self.assertEqual((b1["state"], b2["state"]), ("cooking", "cooking"))
        self.assertEqual(b2["cook_ticks_left"] - b1["cook_ticks_left"], 1)  # B1 bắt đầu trước đúng 1 tick


if __name__ == "__main__":
    unittest.main()
