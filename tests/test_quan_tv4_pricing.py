"""TV4 (T320/T323) bổ sung: cook_started.items sắp (kind, id); giá chốt = floor(giá × tươi TB / 100);
boa tính trên giá chốt; món chín/đang nấu không hao; pause không hao kho quán."""

import unittest

from chonoi.inputs import InputState
from chonoi.runner import Session

from test_quan_p3_freshness import (IDLE, T12, by_name, items, make_sim, run_steps, waiting)

INTERACT = InputState((0, 0), frozenset(), frozenset({"interact"}))


def cook(stock, dish, reserved, patience=1000):
    sim = make_sim({"random_customers": False,
                    "customers": [waiting("C1", "T1", dish=dish, patience=patience, reserved=reserved)]},
                   stock=stock)
    sim.pos = list(sim.stoves[0]["pos"])
    started, = by_name(sim.step(INTERACT), "cook_started")
    return sim, started


class Pricing(unittest.TestCase):
    def test_items_sorted_by_kind_then_id_and_price_is_floor_of_mean(self):
        stock = items(("I9", "ca_loc", 100), ("I3", "bong_dien_dien", 60), ("I1", "ca_loc", 100))
        # canh_chua_ca_loc: ca_loc x1 + bong_dien_dien x1 (giá 90); reserved cố ý không sắp
        sim, started = cook(stock, "canh_chua_ca_loc", ["I3", "I1"])
        self.assertEqual([(e["kind"], e["id"]) for e in started["items"]],
                         [("bong_dien_dien", "I3"), ("ca_loc", "I1")])
        # tick tương tác hao 1 đơn vị: tổng = 100*240-1 + 60*240-1 ; floor(90 * mean / 100)
        mean = ((100 * 240 - 1) + (60 * 240 - 1)) / (2 * 240)
        self.assertEqual(started["base_price"], int(90 * mean // 100))
        self.assertEqual([e["id"] for e in sim.stock], ["I9"], "chỉ tiêu đúng id đang giữ")

    def test_two_same_kind_items_sorted_by_id_key(self):
        stock = items(("I10", "bong_sung", 100), ("I2", "bong_sung", 100))
        _, started = cook(stock, "goi_bong_sung", ["I10", "I2"])
        self.assertEqual([e["id"] for e in started["items"]], ["I2", "I10"], "id_key: I2 < I10")

    def test_tip_is_on_fixed_price_not_fresh_at_pay_time(self):
        sim, started = cook(items(("I1", "ca_loc", 100)), "ca_loc_nuong_trui", ["I1"], patience=5000)
        price = started["base_price"]
        self.assertEqual(price, 59)  # floor(60 * (24000-1)/24000 / 100 * 100)
        run_steps(sim, sim.stoves[0]["cook_ticks_left"])
        sim.step(INTERACT)  # lấy món
        sim.pos = list(sim.tables[0]["pos"])
        sim.step(INTERACT)  # phục vụ
        paid, = by_name(run_steps(sim, sim.customers[0]["eat_ticks_left"]), "paid")
        self.assertEqual(paid["base_price"], price)
        self.assertEqual(paid["tip"], int(price * 0.2))
        self.assertEqual(sim.money, price + paid["tip"])

    def test_cooked_and_cooking_dishes_do_not_decay(self):
        sim, started = cook(items(("I1", "ca_loc", 100)), "ca_loc_nuong_trui", ["I1"])
        run_steps(sim, sim.stoves[0]["cook_ticks_left"] + 30)
        self.assertEqual(sim.stoves[0]["dish"]["base_price"], started["base_price"])
        self.assertEqual(sim.stock, [], "không còn cá thể nào để hao")

    def test_pause_stops_quan_decay(self):
        stock = items(("I1", "ca_loc", 100))
        s = Session("quan", T12, {"random_customers": False, "stock": stock}, 1, contract_version="1.2")
        s.step(IDLE)
        before = s.sim.stock[0]["fresh"]
        pause = InputState((0, 0), frozenset(), frozenset({"pause"}))
        s.step(pause)
        for _ in range(50):
            s.step(IDLE)
        self.assertEqual(s.sim.stock[0]["fresh"], before, "đang pause: kho quán đứng yên")
        s.step(pause)  # resumed + chạy gameplay ngay
        self.assertAlmostEqual(s.sim.stock[0]["fresh"], before - 1 / 240, places=9)


if __name__ == "__main__":
    unittest.main()
