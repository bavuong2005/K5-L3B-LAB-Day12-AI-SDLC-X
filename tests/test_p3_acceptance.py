"""TV5 — Kiểm thử chấp nhận Phase 3 (TICKET-03, gameplay v1.2) dạng hộp đen.

Mọi ca chạy `headless_cmd` thật với `game.contract.json` thật (không fixture contract),
để ma trận `docs/verification/phase-3.md` trỏ được tới lệnh CLI giảng viên sẽ chạy.
Test đơn vị chi tiết nằm ở test_gather_phase3_freshness / test_quan_p3_freshness /
test_inventory_v12 / test_freshness_frame; file này chỉ chốt hành vi ở biên CLI.
Chạy: PYTHONPATH=tests:. python3 -m unittest tests.test_p3_acceptance -v
"""

import json
import os
import unittest

from chonoi.contract import load_contract
from chonoi.ids import IdAllocator
from chonoi.inputs import InputState
from chonoi.rng import Streams
from chonoi.sim.quan import QuanSim

from helpers import ROOT, Workdir, events, read_jsonl, run_headless, snapshots, write_json

TOL = 0.01  # đề: dung sai quan sát độ tươi ±0.01


def contract():
    with open(os.path.join(ROOT, "game.contract.json"), encoding="utf-8") as f:
        return json.load(f)


def items(*specs):
    return [{"id": i, "kind": k, "fresh": f} for i, k, f in specs]


def assert_items_close(tc, got, want):
    """So id/kind chính xác, fresh trong ±0.01 (JSONL làm tròn hiển thị; file kho giữ đủ độ chính xác)."""
    tc.assertEqual([(i["id"], i["kind"]) for i in got], [(i["id"], i["kind"]) for i in want])
    for g, e in zip(got, want):
        tc.assertAlmostEqual(g["fresh"], e["fresh"], delta=TOL)


def gather_sc(hold, **extra):
    return {"gather": {"hold": hold, "random_fish": False, "monsters": [], **extra}}


DOCK = {"frames": [{"tick": 0, "interact": True}]}


class AcP3Contract(unittest.TestCase):
    def test_ac_p3_01_contract_freshness_va_quan_ticks_0(self):
        c = contract()
        self.assertIn(c["contract_version"], ("1.2", "1.3"))  # P4 nâng 1.3, gameplay giữ v1.2
        self.assertEqual(c["tuning"]["freshness"], {"initial": 100, "gather_decay_per_s": 0.5,
                                                    "quan_decay_per_s": 0.25, "spoiled_below": 30})
        with Workdir() as w:
            self.assertEqual(run_headless("--mode", "quan", "--seed", "1", "--ticks", "0",
                                          "--out", w.path("q.jsonl"))[0], 0)


class AcP3InventoryFile(unittest.TestCase):
    def _quan_inv(self, w, inv):
        path = write_json(w.path("inv.json"), inv)
        out = w.path("q.jsonl")
        code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "0",
                                 "--inventory", path, "--out", out)
        return code, err, out

    def test_ac_p3_02_kho_ca_the_hop_le_gom_rong_va_hang_uon(self):
        for inv in ({"items": []},
                    {"items": items(("I1", "ca_linh", 100), ("I2", "ca_loc", 12.5))}):
            with Workdir() as w:
                code, err, out = self._quan_inv(w, inv)
                self.assertEqual(code, 0, err)
                self.assertEqual(snapshots(read_jsonl(out))[0]["stock"], inv["items"])

    def test_ac_p3_03_kho_dem_v10_ma_2_khong_tao_out(self):
        with Workdir() as w:
            code, _, out = self._quan_inv(w, {"items": {"ca_loc": 1}})
            self.assertEqual(code, 2)
            self.assertFalse(os.path.exists(out))

    def test_ac_p3_04_kho_sai_ma_2(self):
        bad = {
            "id trùng": {"items": items(("I1", "ca_loc", 50), ("I1", "ca_linh", 50))},
            "id rỗng": {"items": items(("", "ca_loc", 50))},
            "kind lạ": {"items": items(("I1", "pho_bo", 50))},
            "fresh < 0": {"items": items(("I1", "ca_loc", -0.5))},
            "fresh > 100": {"items": items(("I1", "ca_loc", 100.5))},
            "fresh NaN": {"items": items(("I1", "ca_loc", float("nan")))},
            "khóa gốc lạ": {"items": [], "stock": []},
        }
        for name, inv in bad.items():
            with self.subTest(name), Workdir() as w:
                code, _, out = self._quan_inv(w, inv)
                self.assertEqual(code, 2, name)
                self.assertFalse(os.path.exists(out), name)


class AcP3InventoryOut(unittest.TestCase):
    def _gather(self, w, sc, inputs=None, ticks=5, dest_seed=None):
        dest = w.path("kho.json")
        if dest_seed is not None:
            write_json(dest, dest_seed)
        args = ["--mode", "gather", "--seed", "1", "--ticks", str(ticks), "--out", w.path("g.jsonl"),
                "--scenario", write_json(w.path("sc.json"), sc), "--inventory-out", dest]
        if inputs:
            args += ["--inputs", write_json(w.path("in.json"), inputs)]
        code, err = run_headless(*args)
        self.assertEqual(code, 0, err)
        return dest, read_jsonl(w.path("g.jsonl"))

    def test_ac_p3_05_cap_ben_ghi_mot_lan_nguyen_tu_sap_id(self):
        with Workdir() as w:
            dest, rows = self._gather(w, gather_sc(items(("I10", "ca_loc", 100), ("I2", "ca_linh", 80))), DOCK)
            with open(dest, encoding="utf-8") as f:
                inv = json.load(f)
            self.assertEqual([it["id"] for it in inv["items"]], ["I2", "I10"])  # sắp theo id (khóa số)
            self.assertEqual(len(events(rows, "gather_end")), 1)
            assert_items_close(self, events(rows, "gather_end")[0]["data"]["inventory"]["items"], inv["items"])
            self.assertEqual(sorted(os.listdir(os.path.dirname(dest))),
                             ["g.jsonl", "in.json", "kho.json", "sc.json"])  # không còn file tạm

    def test_ac_p3_05_ngat_ghi_kho_rong(self):
        sc = gather_sc(items(("I1", "ca_linh", 100)),
                       player={"pos": [20, 10], "hp": 1, "oxygen_ticks": 0, "zero_oxy_ticks": 59})
        with Workdir() as w:
            dest, rows = self._gather(w, sc, ticks=1)
            self.assertEqual(events(rows, "gather_end")[0]["data"]["reason"], "fainted")
            with open(dest, encoding="utf-8") as f:
                self.assertEqual(json.load(f), {"items": []})

    def test_ac_p3_05_tick_limit_giu_nguyen_dich(self):
        old = {"items": items(("I9", "ca_loc", 42))}
        with Workdir() as w:
            dest, rows = self._gather(w, gather_sc(items(("I1", "ca_linh", 100))), ticks=3, dest_seed=old)
            self.assertEqual(events(rows, "gather_end"), [])
            with open(dest, encoding="utf-8") as f:
                self.assertEqual(json.load(f), old)


class AcP3Freshness(unittest.TestCase):
    def _gather_rows(self, w, sc, ticks):
        out = w.path("g.jsonl")
        code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", str(ticks), "--out", out,
                                 "--scenario", write_json(w.path("sc.json"), sc))
        self.assertEqual(code, 0, err)
        return read_jsonl(out)

    def test_ac_p3_07_gio_hao_0_5_moi_giay(self):
        with Workdir() as w:
            rows = self._gather_rows(w, gather_sc(items(("I1", "ca_linh", 100))), 60)
            self.assertAlmostEqual(snapshots(rows)[-1]["hold"][0]["fresh"], 99.5, delta=TOL)

    def test_ac_p3_08_scenario_de_spoiled_tick_1_dung_mot_lan(self):
        with Workdir() as w:
            rows = self._gather_rows(w, gather_sc(items(("I1", "ca_linh", 30))), 600)
            sp = events(rows, "spoiled")
            self.assertEqual(sp, [{"type": "event", "tick": 1, "phase": "gather", "name": "spoiled",
                                   "data": {"item_id": "I1", "kind": "ca_linh", "location": "hold"}}])

    def test_ac_p3_09_nhieu_ca_the_spoiled_theo_id(self):
        with Workdir() as w:
            rows = self._gather_rows(w, gather_sc(items(("I2", "ca_loc", 30), ("I1", "ca_linh", 30))), 1)
            self.assertEqual([e["data"]["item_id"] for e in events(rows, "spoiled")], ["I1", "I2"])

    def test_ac_p3_11_kho_quan_hao_0_25_va_spoiled_stock(self):
        with Workdir() as w:
            out = w.path("q.jsonl")
            inv = write_json(w.path("inv.json"), {"items": items(("I1", "ca_loc", 30), ("I2", "ca_linh", 100))})
            code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "60", "--out", out,
                                     "--inventory", inv, "--scenario",
                                     write_json(w.path("sc.json"), {"quan": {"random_customers": False}}))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(out)
            sp = events(rows, "spoiled")
            self.assertEqual([(e["tick"], e["data"]) for e in sp],
                             [(1, {"item_id": "I1", "kind": "ca_loc", "location": "stock"})])
            last = {it["id"]: it["fresh"] for it in snapshots(rows)[-1]["stock"]}
            self.assertAlmostEqual(last["I2"], 99.75, delta=TOL)


IDLE = InputState((0, 0), frozenset(), frozenset())
PRESS = InputState((0, 0), frozenset(), frozenset({"interact"}))


def by_name(evs, name):
    return [d for nm, d in evs if nm == name]


class AcP3CookAndPrice(unittest.TestCase):
    """Dùng QuanSim với tuning của game.contract.json thật (món nhiều nguyên liệu + boa)."""

    def test_ac_p3_15_16_items_sap_kind_roi_id_gia_theo_tuoi_va_boa(self):
        tuning = load_contract(os.path.join(ROOT, "game.contract.json"))["tuning"]
        stock = items(("I9", "ca_linh", 50), ("I10", "ca_linh", 50), ("I2", "ca_linh", 50),
                      ("I5", "bong_dien_dien", 50), ("I7", "ca_linh", 90))
        customer = {"id": "C1", "table_id": "T1", "dish_id": "lau_ca_linh_dien_dien", "order_tick": 0,
                    "state": "waiting", "order_status": "reserved", "patience_ticks_left": 3600,
                    "eat_ticks_left": 0, "reserved": ["I9", "I10", "I2", "I5"]}
        sim = QuanSim(tuning, {"random_customers": False, "customers": [customer], "stock": stock},
                      Streams(1), IdAllocator())
        sim.pos = list(sim.stoves[0]["pos"])
        started, = by_name(sim.step(PRESS), "cook_started")
        # AC-P3-15: mảng cá thể sắp theo kind rồi id; tiêu đúng id đang giữ, I7 dư còn trong kho
        self.assertEqual([i["id"] for i in started["items"]], ["I5", "I2", "I9", "I10"])
        self.assertEqual([i["id"] for i in sim.stock], ["I7"])
        # AC-P3-16: floor(120 × TB fresh / 100); tick tương tác đã hao 1/240 điểm → floor(59.99…) = 59
        self.assertEqual(started["base_price"], 59)
        for _ in range(sim.stoves[0]["cook_ticks_left"]):
            sim.step(IDLE)
        by_name(sim.step(PRESS), "dish_picked")
        sim.pos = list(sim.tables[0]["pos"])
        served, = by_name(sim.step(PRESS), "served")
        self.assertEqual(served["base_price"], 59)
        evs = []
        for _ in range(sim.customers[0]["eat_ticks_left"]):
            evs.extend(sim.step(IDLE))
        paid, = by_name(evs, "paid")
        self.assertEqual((paid["base_price"], paid["tip"]), (59, 59 * 20 // 100))  # boa floor(59×0.2)=11
        self.assertEqual(sim.money, 70)


class AcP3Handoff(unittest.TestCase):
    def test_ac_p3_18_smoke_ban_giao_file_cua_de(self):
        """Đề: mẫu fresh 100 + interact frame 0 → quan --inventory --ticks 0 khớp id/kind/fresh."""
        with Workdir() as w:
            kho = w.path("kho.json")
            g = w.path("g.jsonl")
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "5", "--out", g,
                                     "--scenario", write_json(w.path("sc.json"), gather_sc(items(("I1", "ca_linh", 100)))),
                                     "--inputs", write_json(w.path("in.json"), DOCK), "--inventory-out", kho)
            self.assertEqual(code, 0, err)
            with open(kho, encoding="utf-8") as f:
                inv = json.load(f)
            self.assertEqual(inv["items"][0]["id"], "I1")
            self.assertAlmostEqual(inv["items"][0]["fresh"], 100 - 0.5 / 60, delta=1e-9)  # hao đúng 1 bước
            q = w.path("q.jsonl")
            self.assertEqual(run_headless("--mode", "quan", "--seed", "1", "--ticks", "0",
                                          "--inventory", kho, "--out", q)[0], 0)
            assert_items_close(self, snapshots(read_jsonl(q))[0]["stock"], inv["items"])


class AcP3Day(unittest.TestCase):
    def test_ac_p3_19_day_ban_giao_cung_tick_khong_hao_them(self):
        with Workdir() as w:
            out = w.path("d.jsonl")
            code, err = run_headless("--mode", "day", "--days", "1", "--seed", "1", "--ticks", "3",
                                     "--out", out, "--inputs", write_json(w.path("in.json"), DOCK),
                                     "--scenario", write_json(w.path("sc.json"),
                                                              gather_sc(items(("I1", "ca_linh", 100)))))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(out)
            end = events(rows, "gather_end")[0]
            quan0 = next(s for s in snapshots(rows) if s["phase"] == "quan")
            self.assertEqual(quan0["tick"], end["tick"])
            self.assertEqual(quan0["stock"], end["data"]["inventory"]["items"])

    def test_ac_p3_20_ngay_2_cap_id_moi_cho_mau_hold(self):
        with Workdir() as w:
            out = w.path("d.jsonl")
            code, err = run_headless("--mode", "day", "--days", "2", "--seed", "1", "--ticks", "22300",
                                     "--out", out, "--scenario",
                                     write_json(w.path("sc.json"), gather_sc(items(("I1", "ca_linh", 100)))))
            self.assertEqual(code, 0, err)
            gsnaps = [s for s in snapshots(read_jsonl(out)) if s["phase"] == "gather" and s["phase_tick"] == 0]
            self.assertEqual(len(gsnaps), 2, "cần snapshot gather đầu Ngày 1 và Ngày 2")
            self.assertEqual(gsnaps[0]["hold"][0]["id"], "I1")
            d2 = gsnaps[1]["hold"][0]
            self.assertNotEqual(d2["id"], "I1")
            self.assertGreater(int(d2["id"][1:]), 1)
            self.assertEqual((d2["kind"], d2["fresh"]), ("ca_linh", 100))


class AcP3Determinism(unittest.TestCase):
    def test_ac_p3_23_chay_hai_lan_giong_tung_byte(self):
        cases = {
            "gather": ["--mode", "gather", "--ticks", "600"],
            "quan": ["--mode", "quan", "--ticks", "600"],
            "day": ["--mode", "day", "--days", "1", "--ticks", "3000"],
        }
        for name, args in cases.items():
            with self.subTest(name), Workdir() as w:
                blobs = []
                for i in (1, 2):
                    out = w.path(f"{i}.jsonl")
                    self.assertEqual(run_headless(*args, "--seed", "7", "--out", out)[0], 0)
                    with open(out, "rb") as f:
                        blobs.append(f.read())
                self.assertEqual(blobs[0], blobs[1])


if __name__ == "__main__":
    unittest.main()
