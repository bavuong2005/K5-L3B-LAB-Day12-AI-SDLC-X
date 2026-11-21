"""TV5 — bổ sung AC Phase 1 chưa có test riêng: AC-P1-20 (ưu tiên tương tác), AC-P1-24 (bếp chọn đơn).

Dùng QuanSim với tuning thật của game.contract.json. Bố cục chuẩn không có điểm cách đều
bếp–bàn trong `interact_radius`, nên ca bếp-trước-bàn dời một bàn trên bản sao tuning.
Chạy: PYTHONPATH=tests:. python3 -m unittest tests.test_p1_acceptance -v
"""

import copy
import os
import unittest

from chonoi.contract import load_contract
from chonoi.ids import IdAllocator
from chonoi.inputs import InputState
from chonoi.rng import Streams
from chonoi.sim.quan import QuanSim

from helpers import ROOT

TUNING = load_contract(os.path.join(ROOT, "game.contract.json"))["tuning"]
PRESS = InputState((0, 0), frozenset(), frozenset({"interact"}))
STOCK = [{"id": "I1", "kind": "ca_loc", "fresh": 100}, {"id": "I2", "kind": "ca_loc", "fresh": 100}]


def customer(cid, table, order_tick, iid, **kw):
    c = {"id": cid, "table_id": table, "dish_id": "ca_loc_nuong_trui", "order_tick": order_tick,
         "state": "waiting", "order_status": "reserved", "patience_ticks_left": 3600,
         "eat_ticks_left": 0, "reserved": [iid]}
    c.update(kw)
    return c


def sim_with(customers, tuning=TUNING, stock=STOCK):
    return QuanSim(tuning, {"random_customers": False, "stock": copy.deepcopy(stock),
                            "customers": customers}, Streams(1), IdAllocator())


def names(evs):
    return [(n, d.get("order_id")) for n, d in evs]


class AcP1_20_InteractPriority(unittest.TestCase):
    def test_hai_bep_cach_deu_chon_id_nho(self):
        sim = sim_with([customer("C1", "T1", 0, "I1")])
        b1, b2 = sim.stoves
        sim.pos = [(b1["pos"][0] + b2["pos"][0]) / 2, b1["pos"][1]]
        self.assertEqual(names(sim.step(PRESS)), [("cook_started", "C1")])
        self.assertEqual((b1["state"], b2["state"]), ("cooking", "idle"))

    def test_bep_va_ban_cach_deu_thi_bep_truoc(self):
        tuning = copy.deepcopy(TUNING)
        quan = tuning["quan"]
        b2 = quan["stoves"][1]["pos"]
        quan["tables"][0]["pos"] = [b2[0], b2[1] + 2]  # T1 cách B2 đúng 2 m theo trục z
        dish = {"dish_id": "ca_loc_nuong_trui", "order_id": "C1", "base_price": 60}
        sim = sim_with([customer("C1", "T1", 0, "I1", order_status="assigned", reserved=[])],
                       tuning=tuning, stock=STOCK[1:])
        sim.hand = dict(dish)
        stove = sim.stoves[1]
        stove.update(state="ready", dish={**dish, "order_id": "CX"}, ready_ticks=0)
        sim.pos = [b2[0], b2[1] + 1]  # cách B2 và T1 đều 1 m
        evs = sim.step(PRESS)
        # Bếp được ưu tiên: tay đang bận nên không bưng được → không có sự kiện, và KHÔNG giao món ở bàn.
        self.assertEqual(names(evs), [])
        self.assertIsNotNone(sim.hand)
        self.assertEqual(stove["state"], "ready")

    def test_mot_interact_moi_tick(self):
        sim = sim_with([customer("C1", "T1", 0, "I1"), customer("C2", "T2", 0, "I2")])
        b1, b2 = sim.stoves
        sim.pos = [(b1["pos"][0] + b2["pos"][0]) / 2, b1["pos"][1]]  # cả hai bếp trong tầm
        started = [n for n, _ in sim.step(PRESS) if n == "cook_started"]
        self.assertEqual(len(started), 1)


class AcP1_24_CookOrder(unittest.TestCase):
    def test_bep_chon_order_tick_nho_truoc(self):
        sim = sim_with([customer("C1", "T1", 5, "I1"), customer("C2", "T2", 3, "I2")])
        sim.pos = list(sim.stoves[0]["pos"])
        self.assertEqual(names(sim.step(PRESS)), [("cook_started", "C2")])

    def test_hoa_order_tick_thi_id_ban_nho(self):
        sim = sim_with([customer("C2", "T2", 3, "I2"), customer("C1", "T1", 3, "I1")])
        sim.pos = list(sim.stoves[0]["pos"])
        self.assertEqual(names(sim.step(PRESS)), [("cook_started", "C1")])


if __name__ == "__main__":
    unittest.main()
