"""Phase 2 TV3 (TICKET-02): plan_dishes theo kế hoạch Ngày, 4 bàn T1–T4, kho 6 loại v1.1.

Unit chạy trực tiếp trên QuanSim với tuning fixture v1.1 (4 bàn T1–T4, menu 6 món có ca_keo/keo_neo),
và end-to-end qua `headless --mode day` với biến môi trường CHONOI_CONTRACT trỏ fixture (đúng quy ước
của tests/test_day_mode.py, vì game.contract.json là việc của TV1).
Chạy: PYTHONPATH=tests:. python3 -m unittest discover -s tests -v
"""

import copy
import os
import subprocess
import unittest

from chonoi.contract import load_contract
from chonoi.errors import BadInput
from chonoi.ids import IdAllocator
from chonoi.inputs import InputState
from chonoi.inventory import KINDS_P1, menu_kinds
from chonoi.rng import Streams
from chonoi.scenario import load_scenario
from chonoi.sim.day import _kwargs_for
from chonoi.sim.quan import QuanSim

from helpers import ROOT, Workdir, events, frames, headless_cmd, read_jsonl, write_json

FIXTURE = os.path.join(ROOT, "tests", "fixtures", "contract-v1.1-day.json")
REAL = os.path.join(ROOT, "game.contract.json")
V11 = load_contract(FIXTURE)["tuning"]   # quan: 4 bàn T1–T4; menu: 6 món
MENU = V11["menu"]
Q = V11["quan"]
KINDS_V11 = KINDS_P1 + ("ca_keo", "keo_neo")
FULL = {k: 99 for k in KINDS_V11}
PLAN = {"ca_loc_nuong_trui", "goi_bong_sung"}                                  # kế hoạch Ngày 1 fixture
ONLY_LAU_MAM = {"ca_linh": 2, "ca_keo": 1, "keo_neo": 1, "bong_dien_dien": 1}  # chỉ lau_mam đủ liệu
IDLE = InputState((0, 0), frozenset(), frozenset())


def make_sim(scenario=None, seed=1, stock=None, plan=None, tuning=V11):
    sc = dict(scenario or {})
    if stock is not None:
        sc["stock"] = stock
    return QuanSim(tuning, sc, Streams(seed), IdAllocator(), plan_dishes=plan)


def run_steps(sim, n):
    evs = []
    for _ in range(n):
        evs.extend(sim.step(IDLE))
    return evs


def by_name(evs, name):
    return [d for nm, d in evs if nm == name]


def no_leave_tuning():
    """Bản sao fixture với patience dài hơn cửa sổ test (chỉ fixture, không đụng contract)."""
    t = copy.deepcopy(V11)
    t["quan"]["patience_s"] = 180  # 10800 ticks > 3720: không ai kịp rời bàn trong test
    return t


def waiting(cid, table, dish="ca_loc_nuong_trui", patience=1):
    return {"id": cid, "table_id": table, "dish_id": dish, "order_tick": 0, "state": "waiting",
            "order_status": "reserved", "patience_ticks_left": patience, "eat_ticks_left": 0,
            "reserved": dict(MENU[dish]["recipe"])}


class FourTables(unittest.TestCase):
    """4 bàn T1–T4 của contract v1.1: vào lần lượt T1→T4, full bàn bỏ lượt, rời theo id_key bàn."""

    def test_khach_lan_luot_t1_den_t4_va_khach_thu_5_bi_bo_qua(self):
        sim = make_sim(tuning=no_leave_tuning(), stock=FULL)
        evs = []
        for k, due in enumerate((120, 1020, 1920, 2820), 1):
            evs += run_steps(sim, due - sim.phase_tick)
            arr = by_name(evs, "customer_arrived")
            self.assertEqual(len(arr), k, f"tới tick {due}")
            self.assertEqual(arr[-1]["table_id"], f"T{k}")
            nc = next(c for c in sim.customers if c["id"] == arr[-1]["order_id"])
            self.assertEqual(nc["order_tick"], due)
        evs += run_steps(sim, 3720 - sim.phase_tick)  # lịch khách thứ 5 nhưng cả 4 bàn có người
        evs += run_steps(sim, 900)                    # lịch kế 4620: vẫn full
        self.assertEqual(len(by_name(evs, "customer_arrived")), 4, "không sinh khách thứ năm")
        self.assertEqual(by_name(evs, "no_dish"), [], "hết bàn là bỏ lượt im lặng, không no_dish")
        self.assertEqual(sorted(c["table_id"] for c in sim.customers), ["T1", "T2", "T3", "T4"])

    def test_roi_ban_theo_thu_tu_id_key_cua_ban(self):
        custs = [waiting("C4", "T4"), waiting("C3", "T3"), waiting("C2", "T2"), waiting("C1", "T1")]
        sim = make_sim({"customers": custs}, stock=FULL)
        evs = run_steps(sim, 1)
        left = by_name(evs, "customer_left")
        self.assertEqual([d["table_id"] for d in left], ["T1", "T2", "T3", "T4"])
        self.assertEqual([d["order_id"] for d in left], ["C1", "C2", "C3", "C4"])
        self.assertEqual([d["reputation"] for d in left],
                         [Q["reputation_initial"] + Q["left_reputation_delta"] * i for i in range(1, 5)])
        self.assertEqual(sim.customers, [])


class PlanDishes(unittest.TestCase):
    """plan_dishes lọc món khách được gọi theo kế hoạch Ngày (T230)."""

    def test_chi_go_mon_trong_ke_hoach_du_kho_du_cho_lau_mam(self):
        sim = make_sim(plan=PLAN, stock=FULL)  # kho đủ cho lau_mam và mọi món khác
        evs = run_steps(sim, 2820)             # 4 khách, 4 bàn; chưa ai rời (patience 3600)
        arr = by_name(evs, "customer_arrived")
        self.assertEqual(len(arr), 4)
        self.assertTrue({a["dish_id"] for a in arr} <= PLAN, f"có món ngoài kế hoạch: {arr}")
        self.assertTrue(all(a["dish_id"] in MENU for a in arr))

    def test_ke_hoach_khong_du_lieu_thi_no_dish_du_kho_du_cho_lau_mam(self):
        sim = make_sim(plan=PLAN, stock=dict(ONLY_LAU_MAM))  # chỉ lau_mam đủ nguyên liệu
        evs = run_steps(sim, 120)
        self.assertEqual(by_name(evs, "customer_arrived"), [])
        self.assertEqual(by_name(evs, "no_dish"), [{}], "món duy nhất đủ liệu nằm ngoài kế hoạch")
        self.assertEqual(sim.customers, [])

    def test_khong_plan_thi_lau_mam_duoc_chon_khi_chi_no_du_lieu(self):
        sim = make_sim(stock=dict(ONLY_LAU_MAM))  # control: không có plan_dishes
        evs = run_steps(sim, 120)
        arr = by_name(evs, "customer_arrived")
        self.assertEqual(len(arr), 1)
        self.assertEqual(arr[0]["dish_id"], "lau_mam")
        self.assertEqual(sim.customers[0]["reserved"], MENU["lau_mam"]["recipe"])

    def test_daysim_truyen_plan_dishes_qua_kwargs_for(self):
        self.assertEqual(_kwargs_for(QuanSim, plan_dishes=sorted(PLAN)), {"plan_dishes": sorted(PLAN)},
                         "QuanSim đã có plan_dishes -> day đi đường kw, không cần fallback lọc menu")


class DayModeCli(unittest.TestCase):
    """End-to-end: headless --mode day với CHONOI_CONTRACT=fixture."""

    def run_cli(self, *args, contract=FIXTURE):
        env = dict(os.environ, CHONOI_CONTRACT=contract)
        p = subprocess.run([*headless_cmd(), *args], cwd=ROOT, capture_output=True, text=True, env=env)
        return p.returncode, p.stderr

    def test_day_ke_hoach_lau_mam_kho_thieu_keo_thi_quan_no_dish(self):
        """Plan Ngày 1 = {lau_mam} (override qua scenario.day) nhưng kho quán chỉ có ca_loc.

        ca_loc_nuong_trui đủ liệu và KHÔNG nằm trong kế hoạch -> quán phải no_dish,
        không được gọi món ngoài kế hoạch. Bằng chứng plan_dishes đi tới được QuanSim.
        """
        with Workdir() as w:
            sc = write_json(w.path("s.json"), {
                "day": {"day_plan": [{"day": 1, "dishes": {"lau_mam": 1}}]},
                "gather": {"hold": ["ca_loc"], "random_fish": False}})
            inp = write_json(w.path("i.json"), frames({"tick": 0, "interact": True}))
            out = w.path("o.jsonl")
            code, err = self.run_cli("--mode", "day", "--days", "1", "--seed", "1", "--ticks", "30000",
                                     "--scenario", sc, "--inputs", inp, "--out", out)
            self.assertEqual(code, 0, err)
            rows = read_jsonl(out)
            plans = events(rows, "day_plan")
            self.assertEqual(plans[0]["data"]["dishes"], {"lau_mam": 1})
            self.assertEqual(plans[0]["data"]["ingredients"],
                             {"ca_linh": 2, "ca_keo": 1, "keo_neo": 1, "bong_dien_dien": 1})
            quan_names = [e["name"] for e in events(rows) if e["phase"] == "quan"]
            self.assertIn("no_dish", quan_names)
            self.assertEqual([e for e in events(rows, "customer_arrived")], [],
                             "không được gọi món ngoài kế hoạch dù ca_loc_nuong_trui đủ liệu")
            self.assertEqual(rows[-1]["reason"], "days_complete")
            self.assertEqual(rows[-1]["days_completed"], 1)

    def test_quan_inventory_6_loai_hop_le_voi_contract_that(self):
        with Workdir() as w:
            inv = write_json(w.path("inv.json"), {"items": [{"id": "I1", "kind": "ca_keo", "fresh": 100},
                                                            {"id": "I2", "kind": "keo_neo", "fresh": 100}]})
            code, err = self.run_cli("--mode", "quan", "--seed", "1", "--ticks", "0",
                                     "--inventory", inv, "--out", w.path("a.jsonl"), contract=REAL)
            self.assertEqual(code, 0, err)

    def test_quan_inventory_kind_la_bi_chan(self):
        with Workdir() as w:
            inv = write_json(w.path("inv.json"), {"items": [{"id": "I1", "kind": "ca_la", "fresh": 100}]})
            code, _ = self.run_cli("--mode", "quan", "--seed", "1", "--ticks", "0",
                                   "--inventory", inv, "--out", w.path("b.jsonl"), contract=REAL)
            self.assertEqual(code, 2)
            self.assertFalse(os.path.exists(w.path("b.jsonl")))


class KindsV11(unittest.TestCase):
    """Dải nguyên liệu suy ra từ menu: v1.0 = 4 loại, v1.1 = 6 loại (ca_keo, keo_neo)."""

    def test_menu_kinds_theo_contract(self):
        real = load_contract()["tuning"]
        self.assertEqual(set(menu_kinds(real["menu"])), set(KINDS_V11))
        self.assertEqual(set(menu_kinds(MENU)), set(KINDS_V11))

    def test_scenario_quan_v11_nhan_kho_va_reserved_6_loai(self):
        with Workdir() as w:
            block = {"stock": {"ca_keo": 2, "keo_neo": 1, "ca_linh": 2, "bong_dien_dien": 1},
                     "customers": [{"id": "C1", "table_id": "T1", "dish_id": "lau_mam"}]}
            b = load_scenario(write_json(w.path("s.json"), {"quan": block}), "quan", V11)
            self.assertEqual(b["customers"][0]["reserved"], MENU["lau_mam"]["recipe"])

    def test_scenario_quan_chap_nhan_ca_keo_nhung_chan_kind_la(self):
        real = load_contract()["tuning"]
        with Workdir() as w:
            ok = write_json(w.path("ok.json"), {"quan": {"stock": {"ca_keo": 1}}})
            self.assertEqual(load_scenario(ok, "quan", real)["stock"]["ca_keo"], 1)
            bad = write_json(w.path("bad.json"), {"quan": {"stock": {"ca_la": 1}}})
            with self.assertRaises(BadInput):
                load_scenario(bad, "quan", real)

    def test_scenario_gather_hold_v11_nhan_ca_keo_keo_neo(self):
        with Workdir() as w:
            hold = ["ca_loc", "ca_keo", "keo_neo", "bong_sung"]
            b = load_scenario(write_json(w.path("s.json"), {"gather": {"hold": hold}}),
                              "gather", V11)
            self.assertEqual(b["hold"], hold)


if __name__ == "__main__":
    unittest.main()
