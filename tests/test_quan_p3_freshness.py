"""Phase 3 TV3 (TICKET-03 "Mùa Nước Nổi", v1.2): kho cá thể + độ tươi ở Quán.

Phủ: hao tươi kho 0.25/s (1 đơn vị nguyên/tick, 240 đơn vị/điểm), spoiled đúng 1 lần theo id;
giữ chỗ theo id cá thể (tươi nhất, hòa id_key); phần giữ ươn -> nhả & thử giữ lại đúng 1 lần,
thiếu -> unfulfillable; snapshot schema v1.2; scenario v1.2 sai -> BadInput (mã 2).
Chạy: PYTHONPATH=tests:. python3 -m unittest discover -s tests -v
"""

import copy
import os
import unittest

from chonoi.contract import load_contract
from chonoi.errors import BadInput
from chonoi.ids import IdAllocator
from chonoi.inputs import InputState
from chonoi.rng import Streams
from chonoi.scenario import load_scenario
from chonoi.sim.quan import QuanSim

from helpers import ROOT, Workdir, write_json

FIXTURE = os.path.join(ROOT, "tests", "fixtures", "contract-v1.1-day.json")
V11 = load_contract(FIXTURE)["tuning"]
MENU = V11["menu"]


def v12_tuning():
    """Tuning fixture v1.1 + khóa freshness của contract v1.2 (đề §1: 100 / 0.5 / 0.25 / 30)."""
    t = copy.deepcopy(V11)
    t["freshness"] = {"initial": 100, "gather_decay_per_s": 0.5,
                      "quan_decay_per_s": 0.25, "spoiled_below": 30}
    return t


T12 = v12_tuning()
IDLE = InputState((0, 0), frozenset(), frozenset())


def items(*specs):
    """(id, kind, fresh) -> mảng cá thể {id, kind, fresh}."""
    return [{"id": i, "kind": k, "fresh": f} for i, k, f in specs]


def make_sim(scenario=None, seed=1, stock=None, tuning=T12):
    sc = dict(scenario or {})
    if stock is not None:
        sc["stock"] = stock
    return QuanSim(tuning, sc, Streams(seed), IdAllocator())


def run_steps(sim, n):
    evs = []
    for _ in range(n):
        evs.extend(sim.step(IDLE))
    return evs


def by_name(evs, name):
    return [d for nm, d in evs if nm == name]


def item(sim, iid):
    return next(it for it in sim.stock if it["id"] == iid)


def waiting(cid, table, dish="ca_loc_nuong_trui", patience=60, reserved=None):
    c = {"id": cid, "table_id": table, "dish_id": dish, "order_tick": 0, "state": "waiting",
         "order_status": "reserved", "patience_ticks_left": patience, "eat_ticks_left": 0}
    if reserved is not None:
        c["reserved"] = list(reserved)
    return c


class CookingWithFreshStock(unittest.TestCase):
    def test_burn_boundary_and_re_reservation(self):
        tuning = v12_tuning()
        tuning["quan"]["burn_s"] = 20
        interact = InputState((0, 0), frozenset(), frozenset({"interact"}))
        for stock, reserved, expected in (
            (items(("I1", "ca_loc", 100)), ["I1"], "reserved"),
            ([], [], "unfulfillable"),
        ):
            customer = waiting("C1", "T1", patience=1000, reserved=[])
            customer["order_status"] = "assigned"
            sim = make_sim({"customers": [customer], "random_customers": False},
                           stock=stock, tuning=tuning)
            stove = sim.stoves[0]
            dish = {"order_id": "C1", "dish_id": customer["dish_id"], "base_price": 60}
            stove.update(state="ready", dish=dish, ready_ticks=1199)
            sim.pos = list(stove["pos"])
            picked, = by_name(sim.step(interact), "dish_picked")
            self.assertEqual(picked["order_id"], "C1")
            sim.hand = None
            stove.update(state="ready", dish=dish, ready_ticks=1200)
            burnt, = by_name(sim.step(IDLE), "dish_burnt")
            self.assertEqual(burnt["order_status"], expected)
            self.assertEqual(stove["state"], "idle")
            self.assertEqual(sim.customers[0]["reserved"], reserved)

    def test_reserved_item_sets_price_through_payment(self):
        sim = make_sim({"random_customers": False,
                        "customers": [waiting("C1", "T1", patience=1000, reserved=["I2"])]},
                       stock=items(("I1", "ca_loc", 100), ("I2", "ca_loc", 50)))
        interact = InputState((0, 0), frozenset(), frozenset({"interact"}))
        sim.pos = list(sim.stoves[0]["pos"])
        started, = by_name(sim.step(interact), "cook_started")
        self.assertEqual([entry["id"] for entry in started["items"]], ["I2"])
        self.assertEqual([entry["id"] for entry in sim.stock], ["I1"])
        # Tick tương tác làm hao một đơn vị trước khi chốt giá: floor(60 * (50 - 1/240) / 100).
        self.assertEqual(started["base_price"], 29)
        run_steps(sim, sim.stoves[0]["cook_ticks_left"])
        picked, = by_name(sim.step(interact), "dish_picked")
        self.assertEqual(picked["base_price"], 29)
        sim.pos = list(sim.tables[0]["pos"])
        served, = by_name(sim.step(interact), "served")
        self.assertEqual(served["base_price"], 29)
        paid, = by_name(run_steps(sim, sim.customers[0]["eat_ticks_left"]), "paid")
        self.assertEqual((paid["base_price"], paid["tip"], sim.money), (29, 0, 29))


class DecayAndSpoiled(unittest.TestCase):
    """Kho quán hao 0.25/s kể cả hàng đang giữ; spoiled đúng 1 lần, theo id."""

    def test_hao_1_don_vi_tick_va_spoiled_dung_mot_lan_tai_nguong(self):
        stock = items(("I2", "ca_linh", 30.0), ("I1", "ca_loc", 100.0))
        sim = make_sim({"random_customers": False}, stock=stock)
        evs = run_steps(sim, 1)
        spoiled = by_name(evs, "spoiled")
        self.assertEqual(spoiled, [{"item_id": "I2", "kind": "ca_linh", "location": "stock"}],
                         "I2 đi từ 30 (7200 đơn vị) xuống dưới ngưỡng đúng ở bước đầu")
        self.assertAlmostEqual(item(sim, "I2")["fresh"], 7199 / 240, places=9)
        self.assertAlmostEqual(item(sim, "I1")["fresh"], (24000 - 1) / 240, places=9)
        evs += run_steps(sim, 600)
        self.assertEqual(len(by_name(evs, "spoiled")), 1, "spoiled đúng MỘT lần")
        self.assertAlmostEqual(item(sim, "I1")["fresh"], (24000 - 601) / 240, places=9,
                               msg="I1 hao đủ 601 tick (1 tick đầu + 600 tick sau)")

    def test_kho_khong_bao_gio_am(self):
        stock = items(("I1", "ca_loc", 1.0))
        sim = make_sim({"random_customers": False}, stock=stock)
        run_steps(sim, 500)  # 240 đơn vị hết sau 240 tick
        self.assertEqual(item(sim, "I1")["fresh"], 0.0)
        self.assertEqual(sim._units["I1"], 0)

    def test_ca_the_bat_dau_duoi_nguong_khong_phat_spoiled(self):
        stock = items(("I1", "ca_loc", 29.0))
        sim = make_sim({"random_customers": False}, stock=stock)
        evs = run_steps(sim, 5)
        self.assertEqual(by_name(evs, "spoiled"), [], "không đi qua ngưỡng thì không spoiled")

    def test_nhieu_ca_the_uon_cung_tick_phat_theo_id(self):
        stock = items(("I2", "ca_linh", 30.0), ("I1", "bong_sung", 30.0))
        sim = make_sim({"random_customers": False}, stock=stock)
        evs = run_steps(sim, 1)
        self.assertEqual([d["item_id"] for d in by_name(evs, "spoiled")], ["I1", "I2"],
                         "cùng vượt ngưỡng -> phát theo id")

    def test_hao_ke_ca_hang_dang_giu(self):
        stock = items(("I1", "ca_loc", 30.5))
        c1 = waiting("C1", "T1", reserved=["I1"])
        sim = make_sim({"customers": [c1], "random_customers": False}, stock=stock)
        run_steps(sim, 1)
        self.assertAlmostEqual(item(sim, "I1")["fresh"], (30.5 * 240 - 1) / 240, places=9,
                               msg="hàng đang giữ chỗ vẫn hao tươi")


class ReReserve(unittest.TestCase):
    """Phần giữ có cá thể vừa ươn: nhả toàn bộ, thử giữ lại đúng 1 lần; thiếu -> unfulfillable."""

    def test_nha_va_giu_lai_tu_ca_the_toi_nhat_con_lai(self):
        stock = items(("I1", "ca_loc", 30.0), ("I3", "ca_loc", 80.0))
        c1 = waiting("C1", "T1", reserved=["I1"])
        sim = make_sim({"customers": [c1], "random_customers": False}, stock=stock)
        evs = run_steps(sim, 1)
        c = sim.customers[0]
        self.assertEqual(c["order_status"], "reserved", "còn cá thể tươi thay thế -> giữ lại thành công")
        self.assertEqual(c["reserved"], ["I3"], "giữ lại cá thể tươi duy nhất còn lại")
        self.assertEqual(by_name(evs, "customer_left"), [], "khách vẫn chờ")

    def test_khong_con_hang_toi_thi_unfulfillable_va_cho_den_het_kien_nhan(self):
        stock = items(("I1", "ca_loc", 30.0))
        c1 = waiting("C1", "T1", reserved=["I1"], patience=60)
        sim = make_sim({"customers": [c1], "random_customers": False}, stock=stock)
        evs = run_steps(sim, 1)
        c = sim.customers[0]
        self.assertEqual(c["order_status"], "unfulfillable")
        self.assertEqual(c["reserved"], [])
        evs += run_steps(sim, 58)  # tổng 59 tick: vẫn chờ (còn 1 tick kiên nhẫn)
        self.assertEqual(len(sim.customers), 1, "khách unfulfillable vẫn chờ tới hết kiên nhẫn")
        evs += run_steps(sim, 1)   # tick 60: hết kiên nhẫn -> rời
        left = by_name(evs, "customer_left")
        self.assertEqual(len(left), 1)
        self.assertEqual(left[0]["reason"], "patience")
        self.assertEqual(sim.customers, [])

    def test_hai_don_cung_bi_anh_huong_uu_tien_order_tick_roi_id_ban(self):
        # C2 (order_tick 0, bàn T2) khai trước C1 (order_tick 1, bàn T1) trong mảng scenario:
        # khi cả hai vừa ươn và chỉ còn 1 cá thể tươi thay thế, đơn (0, T2) phải được ưu tiên.
        stock = items(("I1", "ca_loc", 30.0), ("I2", "ca_loc", 30.0), ("I3", "ca_loc", 80.0))
        customers = [waiting("C2", "T2", reserved=["I1"]), waiting("C1", "T1", reserved=["I2"])]
        customers[0]["order_tick"], customers[1]["order_tick"] = 0, 1
        sim = make_sim({"customers": customers, "random_customers": False}, stock=stock)
        run_steps(sim, 1)
        by_id = {c["id"]: c for c in sim.customers}
        self.assertEqual(by_id["C2"]["reserved"], ["I3"], "đơn (order_tick 0, T2) giữ lại trước")
        self.assertEqual(by_id["C2"]["order_status"], "reserved")
        self.assertEqual(by_id["C1"]["order_status"], "unfulfillable", "đơn sau hết cá thể thay thế")
        self.assertEqual(by_id["C1"]["reserved"], [])

    def test_dang_ban_giay_kho_ca_the_thi_giu_cho_khong_he_do_dem(self):
        # Kho đếm v1.0/v1.1 (không freshness bắt buộc): hành vi Phase 1/2 giữ nguyên.
        sim = make_sim({"random_customers": False}, stock={"ca_loc": 2}, tuning=V11)
        evs = run_steps(sim, 10)
        self.assertEqual(by_name(evs, "spoiled"), [], "kho đếm không có luật độ tươi")


class SpawnPicksFreshest(unittest.TestCase):
    """Khách mới giữ các cá thể tươi nhất (hòa id_key); hàng ươn không tính là nấu được."""

    def test_khach_moi_giu_ca_the_toi_nhat(self):
        stock = items(("I1", "ca_loc", 90.0), ("I2", "ca_loc", 95.0))
        sim = make_sim(stock=stock)  # chỉ ca_loc_nuong_trui nấu được -> tất định
        evs = run_steps(sim, 120)
        arr = by_name(evs, "customer_arrived")
        self.assertEqual(len(arr), 1)
        self.assertEqual(arr[0]["dish_id"], "ca_loc_nuong_trui")
        self.assertEqual(sim.customers[0]["reserved"], ["I2"], "tươi nhất trước (95 > 90)")

    def test_bang_do_tuoi_thi_lay_id_nho_hon(self):
        stock = items(("I2", "ca_loc", 90.0), ("I1", "ca_loc", 90.0))
        sim = make_sim(stock=stock)
        run_steps(sim, 120)
        self.assertEqual(sim.customers[0]["reserved"], ["I1"], "hòa độ tươi theo id_key")

    def test_hang_uon_khong_tinh_la_nau_duoc(self):
        stock = items(("I1", "ca_loc", 10.0))  # chỉ có hàng ươn
        sim = make_sim(stock=stock)
        evs = run_steps(sim, 120)
        self.assertEqual(by_name(evs, "customer_arrived"), [], "không món nào nấu được")
        self.assertEqual(by_name(evs, "no_dish"), [{}])

    def test_khach_dang_giu_do_tru_khoi_cac_the_kha_dung(self):
        stock = items(("I1", "ca_loc", 90.0), ("I2", "ca_loc", 95.0))
        c1 = waiting("C1", "T1", reserved=["I2"], patience=3600)  # chưa rời trước tick 120
        sim = make_sim({"customers": [c1]}, stock=stock)
        run_steps(sim, 120)  # khách mới đến bàn trống kế tiếp (fixture có T1–T4)
        newcomers = [c for c in sim.customers if c["id"] != "C1"]
        self.assertEqual(len(newcomers), 1)
        self.assertEqual(newcomers[0]["reserved"], ["I1"], "không được mượn cá thể đơn C1 đang giữ")
        self.assertEqual(sim.customers[0]["reserved"], ["I2"])


class SnapshotSchema(unittest.TestCase):
    """snapshot v1.2: stock mảng cá thể sắp theo id (đúng 3 khóa); reserved mảng id sắp theo id."""

    def test_stock_va_reserved_dung_schema(self):
        stock = items(("I2", "ca_linh", 80.0), ("I1", "ca_loc", 30.0))
        c1 = waiting("C1", "T1", reserved=["I1"])
        sim = make_sim({"customers": [c1], "random_customers": False}, stock=stock)
        snap = sim.snapshot()
        self.assertEqual([it["id"] for it in snap["stock"]], ["I1", "I2"])
        for it in snap["stock"]:
            self.assertEqual(set(it), {"id", "kind", "fresh"})
        cust = snap["customers"][0]
        self.assertEqual(cust["reserved"], ["I1"])
        # sau khi I1 ươn và giữ lại từ cá thể mới, reserved trong snapshot vẫn sắp theo id
        stock2 = items(("I1", "ca_loc", 30.0), ("I3", "ca_loc", 80.0))
        sim2 = make_sim({"customers": [waiting("C1", "T1", reserved=["I1"])],
                         "random_customers": False}, stock=stock2)
        run_steps(sim2, 1)
        snap2 = sim2.snapshot()
        self.assertEqual(snap2["customers"][0]["reserved"], ["I3"])

    def test_kho_dem_van_snapshot_dang_count(self):
        sim = make_sim({"random_customers": False}, stock={"ca_loc": 2}, tuning=V11)
        snap = sim.snapshot()
        self.assertEqual(snap["stock"], {"ca_loc": 2})


class ScenarioV12(unittest.TestCase):
    """scenario quan v1.2: reserved mảng id; sai/mâu thuẫn -> BadInput (mã 2 qua CLI)."""

    def _load(self, block):
        with Workdir() as w:
            load_scenario(write_json(w.path("s.json"), {"quan": block}), "quan", T12)

    def test_kho_ca_the_hop_le_va_reserved_dung_id(self):
        with Workdir() as w:
            block = {"stock": items(("I1", "ca_loc", 30.0), ("I2", "ca_loc", 80.0)),
                     "customers": [waiting("C1", "T1", reserved=["I1"])]}
            b = load_scenario(write_json(w.path("s.json"), {"quan": block}), "quan", T12)
            self.assertEqual(b["customers"][0]["reserved"], ["I1"])

    def test_reserved_troi_hang_uon_exit_2(self):
        block = {"stock": items(("I1", "ca_loc", 29.9)),
                 "customers": [waiting("C1", "T1", reserved=["I1"])]}
        with self.assertRaises(BadInput):
            self._load(block)

    def test_reserved_trung_id_giua_2_don_exit_2(self):
        block = {"stock": items(("I1", "ca_loc", 100.0)),
                 "customers": [waiting("C1", "T1", reserved=["I1"]),
                               waiting("C2", "T2", reserved=["I1"])]}
        with self.assertRaises(BadInput):
            self._load(block)

    def test_reserved_chi_id_khong_ton_tai_exit_2(self):
        block = {"stock": items(("I1", "ca_loc", 100.0)),
                 "customers": [waiting("C1", "T1", reserved=["I9"])]}
        with self.assertRaises(BadInput):
            self._load(block)

    def test_reserved_khong_du_cong_thuc_exit_2(self):
        block = {"stock": items(("I1", "ca_loc", 100.0)),
                 "customers": [waiting("C1", "T1", dish="canh_chua_ca_loc", reserved=["I1"])]}
        with self.assertRaises(BadInput):
            self._load(block)  # canh_chua cần thêm bong_dien_dien

    def test_thieu_reserved_tu_cap_toi_nhat_roi_id_nho(self):
        block = {"stock": items(("I1", "ca_loc", 50.0), ("I2", "ca_loc", 80.0)),
                 "customers": [waiting("C1", "T1")]}  # không khai reserved
        with Workdir() as w:
            b = load_scenario(write_json(w.path("s.json"), {"quan": block}), "quan", T12)
        self.assertEqual(b["customers"][0]["reserved"], ["I2"], "tự cấp cá thể tươi nhất")

    def test_thieu_reserved_khong_du_hang_toi_exit_2(self):
        block = {"stock": items(("I1", "ca_loc", 20.0)),
                 "customers": [waiting("C1", "T1")]}  # chỉ có hàng ươn
        with self.assertRaises(BadInput):
            self._load(block)

    def test_kho_dem_van_hop_le_va_reserved_sai_kieu_exit_2(self):
        block = {"stock": {"ca_loc": 1},
                 "customers": [waiting("C1", "T1", reserved=["I1"])]}  # reserved mảng nhưng kho đếm
        with self.assertRaises(BadInput):
            self._load(block)
        block2 = {"stock": items(("I1", "ca_loc", 100.0)),
                  "customers": [waiting("C1", "T1", reserved={"ca_loc": 1})]}  # reserved đếm nhưng kho cá thể
        with self.assertRaises(BadInput):
            self._load(block2)

    def test_stock_sai_schema_exit_2(self):
        bad_stocks = (
            [{"id": "I1", "kind": "ca_loc", "fresh": 101}],          # fresh > 100
            [{"id": "I1", "kind": "ca_loc", "fresh": -1}],           # fresh < 0
            [{"id": "I1", "kind": "ca_loc"}],                        # thiếu fresh
            [{"id": "I1", "kind": "ca_loc", "fresh": 50, "x": 1}],   # khóa lạ
            [{"id": "I1", "kind": "ca_loc", "fresh": 50}, {"id": "I1", "kind": "ca_linh", "fresh": 50}],  # id trùng
            [{"id": "", "kind": "ca_loc", "fresh": 50}],             # id rỗng
            [{"id": "I1", "kind": "pho_bo", "fresh": 50}],           # kind lạ
            [{"id": "I1", "kind": "ca_loc", "fresh": "50"}],         # fresh không phải số
        )
        for bad in bad_stocks:
            with self.assertRaises(BadInput, msg=str(bad)):
                self._load({"stock": bad})

    def test_headless_quan_v12_ma_0_va_sai_ma_2(self):
        import subprocess
        from helpers import headless_cmd
        with Workdir() as w:
            good = write_json(w.path("s.json"), {"quan": {"stock": items(("I1", "ca_loc", 100.0)),
                                                                      "random_customers": False}})
            code, err = subprocess.run([*headless_cmd(), "--mode", "quan", "--seed", "1", "--ticks", "1",
                                        "--scenario", good, "--out", w.path("a.jsonl")],
                                       cwd=ROOT, capture_output=True, text=True).returncode, None
            self.assertEqual(code, 0, "quan với kho cá thể v1.2 qua scenario chạy được (mã 0)")
            bad = write_json(w.path("b.json"), {"quan": {"stock": [{"id": "I1", "kind": "ca_loc", "fresh": 101.0}]}})
            code2 = subprocess.run([*headless_cmd(), "--mode", "quan", "--seed", "1", "--ticks", "1",
                                    "--scenario", bad, "--out", w.path("c.jsonl")],
                                   cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(code2.returncode, 2, "scenario v1.2 sai -> CLI mã 2")


if __name__ == "__main__":
    unittest.main()
