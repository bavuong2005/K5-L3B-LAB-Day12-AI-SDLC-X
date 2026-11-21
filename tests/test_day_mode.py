"""Lát 4 Phase 2 (TV6): --mode day, Shop, pause, sự kiện đổi pha (T240–T245, T248).

Chạy với contract fixture `tests/fixtures/contract-v1.1-day.json` (copy contract hiện tại + khóa v1.1
`day_plan`, `shop`, menu 6 món, B2, T2–T4) qua biến môi trường CHONOI_CONTRACT, vì game.contract.json là
việc của TV1 (T210) và có thể chưa lên v1.1. fish_initial/nodes giữ kiểu v1.0 do contract.py (T211) chưa đổi.
"""

import json
import os
import subprocess
import unittest

from helpers import ROOT, Workdir, events, frames, headless_cmd, read_jsonl, snapshots, write_json

FIXTURE = os.path.join(ROOT, "tests", "fixtures", "contract-v1.1-day.json")
REAL = os.path.join(ROOT, "game.contract.json")

# Lịch khách của ca quan trong fixture v1.1: first_customer_tick + k * customer_interval_s*60
_Q = json.load(open(FIXTURE, encoding="utf-8"))["tuning"]["quan"]
Q_FIRST = _Q["first_customer_tick"]
Q_INTERVAL = int(round(_Q["customer_interval_s"] * 60))
Q_LAST_DUE = Q_FIRST + ((int(round(_Q["duration_s"] * 60)) - Q_FIRST) // Q_INTERVAL) * Q_INTERVAL


def run(*args, contract=FIXTURE):
    env = dict(os.environ, CHONOI_CONTRACT=contract)
    p = subprocess.run([*headless_cmd(), *args], cwd=ROOT, capture_output=True, text=True, env=env)
    return p.returncode, p.stderr


# Mở một Ngày nhanh: tương tác ở bến tick 0 đóng ca sáng; quán còn 1 tick → Shop từ tick 2.
FAST = {"gather": {"hold": ["ca_loc", "bong_sung", "bong_sung"], "random_fish": False},
        "quan": {"time_left_ticks": 1}}


def fast(**day):
    sc = json.loads(json.dumps(FAST))
    if day:
        sc["day"] = day
    return sc


class DayCliTest(unittest.TestCase):
    def test_days_and_inventory_flags_exit_2(self):
        with Workdir() as w:
            out = w.path("o.jsonl")
            inv = write_json(w.path("inv.json"), {"items": {}})
            cases = [
                ("--mode", "day", "--days", "0"),
                ("--mode", "day", "--days", "6"),
                ("--mode", "day", "--days", "x"),
                ("--mode", "gather", "--days", "1"),
                ("--mode", "quan", "--days", "2"),
                ("--mode", "day", "--inventory", inv),
                ("--mode", "day", "--inventory-out", w.path("k.json")),
            ]
            for c in cases:
                self.assertEqual(run(*c, "--seed", "1", "--ticks", "5", "--out", out)[0], 2, c)
            self.assertFalse(os.path.exists(out))

    def test_contract_without_day_plan_exit_2_clear_message(self):
        """Contract thiếu khóa v1.1 (day_plan) bị từ chối rõ ràng, không tạo file out."""
        with open(REAL, encoding="utf-8") as f:
            c = json.load(f)
        c["tuning"].pop("day_plan")
        with Workdir() as w:
            bad = write_json(w.path("no-plan.json"), c)
            code, err = run("--mode", "day", "--seed", "1", "--ticks", "5", "--out", w.path("o.jsonl"), contract=bad)
            self.assertEqual(code, 2)
            self.assertIn("day_plan", err)
            self.assertFalse(os.path.exists(w.path("o.jsonl")))

    def test_attack_photo_ignored_with_v11(self):
        with Workdir() as w:
            inp = write_json(w.path("i.json"), frames({"tick": 0, "attack": True, "photo": True}))
            self.assertEqual(run("--mode", "gather", "--seed", "1", "--ticks", "5", "--inputs", inp,
                                 "--out", w.path("o.jsonl"))[0], 0)
            bad = write_json(w.path("b.json"), frames({"tick": 0, "buy": ""}))
            self.assertEqual(run("--mode", "gather", "--seed", "1", "--ticks", "5", "--inputs", bad,
                                 "--out", w.path("o.jsonl"))[0], 2)


class DayLoopTest(unittest.TestCase):
    def test_one_day_no_input(self):
        with Workdir() as w:
            self.assertEqual(run("--mode", "day", "--seed", "1", "--ticks", "30000", "--out", w.path("o.jsonl"))[0], 0)
            rows = read_jsonl(w.path("o.jsonl"))
            first = [(r["name"], r["tick"], r["phase"], r["day"]) for r in rows[:3]]
            self.assertEqual(first, [("day_start", 0, "gather", 1), ("day_plan", 0, "gather", 1),
                                     ("phase_start", 0, "gather", 1)])
            self.assertEqual(rows[1]["data"], {"dishes": {"ca_loc_nuong_trui": 3, "goi_bong_sung": 3},
                                               "ingredients": {"ca_loc": 3, "bong_sung": 6}})
            self.assertEqual(rows[3]["type"], "snapshot")
            names = [(e["name"], e["phase"]) for e in events(rows)]
            # TICKET-02: kho bàn giao rỗng mà vẫn có bàn thì mỗi lượt khách là no_dish.
            self.assertTrue(names and all(p == "quan" for n, p in names if n == "no_dish"))
            core = [n for n in names if n[0] != "no_dish"]
            self.assertEqual(core, [("day_start", "gather"), ("day_plan", "gather"), ("phase_start", "gather"),
                                    ("gather_end", "gather"), ("phase_start", "quan"),
                                    ("quan_end", "quan"), ("phase_start", "shop"), ("shop_end", "shop")])
            ev = {e["name"] + e["phase"]: e for e in events(rows)}
            self.assertEqual(ev["gather_endgather"]["tick"], ev["phase_startquan"]["tick"])
            self.assertEqual(ev["quan_endquan"]["tick"], ev["phase_startshop"]["tick"])
            self.assertEqual(ev["shop_endshop"]["data"], {"reason": "time"})
            for s in snapshots(rows):
                for k in ("day", "day_plan", "upgrades", "active_upgrades"):
                    self.assertIn(k, s)
            by_tick = {s["tick"]: s for s in snapshots(rows)}
            sq = by_tick[ev["phase_startquan"]["tick"]]
            self.assertEqual((sq["phase"], sq["phase_tick"]), ("quan", 0))
            ss = by_tick[ev["phase_startshop"]["tick"]]
            self.assertEqual((ss["phase"], ss["phase_tick"], ss["time_left_ticks"]), ("shop", 0, 600))
            self.assertIn("stock", ss)
            end = rows[-1]
            self.assertEqual(end["type"], "end")
            self.assertEqual((end["reason"], end["days_completed"]), ("days_complete", 1))
            self.assertLessEqual(end["ticks"], 22200)

    def test_tick_limit_reports_days_completed_0(self):
        with Workdir() as w:
            self.assertEqual(run("--mode", "day", "--seed", "1", "--ticks", "50", "--out", w.path("o.jsonl"))[0], 0)
            end = read_jsonl(w.path("o.jsonl"))[-1]
            self.assertEqual((end["reason"], end["days_completed"], end["ticks"]), ("tick_limit", 0, 50))

    def test_dock_hands_inventory_to_quan_same_tick(self):
        with Workdir() as w:
            sc = write_json(w.path("s.json"), fast())
            inp = write_json(w.path("i.json"), frames({"tick": 0, "interact": True}))
            self.assertEqual(run("--mode", "day", "--seed", "1", "--ticks", "5", "--scenario", sc, "--inputs", inp,
                                 "--out", w.path("o.jsonl"))[0], 0)
            rows = read_jsonl(w.path("o.jsonl"))
            ge = events(rows, "gather_end")[0]
            self.assertEqual(ge["data"]["inventory"]["items"], {"bong_sung": 2, "ca_loc": 1})
            snap1 = [s for s in snapshots(rows) if s["tick"] == ge["tick"]][0]
            self.assertEqual(snap1["phase"], "quan")
            self.assertEqual(snap1["stock"], {"bong_sung": 2, "ca_loc": 1})

    def test_shop_buy_and_next_day_upgrade(self):
        with Workdir() as w:
            sc = write_json(w.path("s.json"), fast(money=250, earned=300))
            inp = write_json(w.path("i.json"), frames(
                {"tick": 0, "interact": True},
                {"tick": 2, "buy": "oxygen"},
                {"tick": 3, "buy": "oxygen"},     # còn 50 < 400 → funds
                {"tick": 4, "buy": "xyz"},        # lệnh lạ → unknown
                {"tick": 5, "shop_done": True}))
            self.assertEqual(run("--mode", "day", "--days", "2", "--seed", "1", "--ticks", "8", "--scenario", sc,
                                 "--inputs", inp, "--out", w.path("o.jsonl"), "--snapshot-every", "1")[0], 0)
            rows = read_jsonl(w.path("o.jsonl"))
            b = events(rows, "bought")
            self.assertEqual([e["data"] for e in b], [{"upgrade": "oxygen", "level": 1, "price": 200, "money": 50}])
            self.assertEqual([e["data"] for e in events(rows, "buy_failed")],
                             [{"action": "oxygen", "reason": "funds"}, {"action": "xyz", "reason": "unknown"}])
            snap = {s["tick"]: s for s in snapshots(rows)}
            after = snap[b[0]["tick"]]
            self.assertEqual((after["money"], after["earned"]), (50, 300))
            self.assertEqual((after["upgrades"], after["active_upgrades"]), ({"oxygen": 1}, {}))
            se = events(rows, "shop_end")[0]
            self.assertEqual((se["data"], se["day"]), ({"reason": "done"}, 1))
            starts = [e for e in events(rows) if e["tick"] == se["tick"] and e["day"] == 2]
            self.assertEqual([e["name"] for e in starts], ["day_start", "day_plan", "phase_start"])
            d2 = snap[se["tick"]]
            self.assertEqual((d2["day"], d2["phase"], d2["phase_tick"]), (2, "gather", 0))
            self.assertEqual(d2["active_upgrades"], {"oxygen": 1})
            self.assertEqual(d2["player"]["oxygen_max_ticks"], 2700)
            self.assertEqual(d2["player"]["oxygen_ticks"], 2700)
            self.assertEqual(d2["hold"], ["ca_loc", "bong_sung", "bong_sung"])  # mẫu gather mỗi Ngày
            self.assertEqual(rows[-1]["days_completed"], 1)

    def test_max_level_and_buy_not_inherited(self):
        with Workdir() as w:
            sc = write_json(w.path("s.json"), fast(money=1000, earned=1000, upgrades={"oxygen": 2}))
            inp = write_json(w.path("i.json"), frames(
                {"tick": 0, "interact": True},
                {"tick": 2, "buy": "oxygen"},
                {"tick": 3, "move": [0, 0]},      # frame không có buy: không kế thừa
                {"tick": 4, "buy": "hp"}))
            self.assertEqual(run("--mode", "day", "--seed", "1", "--ticks", "8", "--scenario", sc,
                                 "--inputs", inp, "--out", w.path("o.jsonl"))[0], 0)
            rows = read_jsonl(w.path("o.jsonl"))
            self.assertEqual([e["data"] for e in events(rows, "buy_failed")], [{"action": "oxygen", "reason": "max_level"}])
            self.assertEqual([e["data"] for e in events(rows, "bought")],
                             [{"upgrade": "hp", "level": 1, "price": 250, "money": 750}])
            self.assertEqual(snapshots(rows)[0]["active_upgrades"], {"oxygen": 2})

    def test_shop_done_on_last_step_is_done(self):
        with Workdir() as w:
            sc = write_json(w.path("s.json"), fast())
            inp = write_json(w.path("i.json"), frames({"tick": 0, "interact": True}, {"tick": 601, "shop_done": True}))
            self.assertEqual(run("--mode", "day", "--seed", "1", "--ticks", "1000", "--scenario", sc,
                                 "--inputs", inp, "--out", w.path("o.jsonl"))[0], 0)
            rows = read_jsonl(w.path("o.jsonl"))
            se = events(rows, "shop_end")[0]
            self.assertEqual((se["tick"], se["data"]), (602, {"reason": "done"}))

    def test_five_days_complete_and_deterministic(self):
        with Workdir() as w:
            for o in ("a.jsonl", "b.jsonl"):
                self.assertEqual(run("--mode", "day", "--days", "2", "--seed", "7", "--ticks", "50000",
                                     "--out", w.path(o))[0], 0)
            with open(w.path("a.jsonl"), "rb") as a, open(w.path("b.jsonl"), "rb") as b:
                self.assertEqual(a.read(), b.read())
            sc = write_json(w.path("s.json"), fast())
            fr = []
            for d in range(5):  # mỗi Ngày nhanh: 1 bước gather (cập bến), 1 bước quán, 1 bước Shop
                fr.append({"tick": 3 * d, "interact": True, "shop_done": False})
                fr.append({"tick": 3 * d + 1, "interact": False})
                fr.append({"tick": 3 * d + 2, "shop_done": True})
            inp = write_json(w.path("i.json"), {"frames": fr})
            self.assertEqual(run("--mode", "day", "--days", "5", "--seed", "1", "--ticks", "200000", "--scenario", sc,
                                 "--inputs", inp, "--out", w.path("o.jsonl"))[0], 0)
            rows = read_jsonl(w.path("o.jsonl"))
            self.assertEqual([e["day"] for e in events(rows, "day_start")], [1, 2, 3, 4, 5])
            self.assertEqual((rows[-1]["reason"], rows[-1]["days_completed"]), ("days_complete", 5))
            plans = [e["data"]["dishes"] for e in events(rows, "day_plan")]
            self.assertEqual(plans[2], {"goi_bong_sung": 2, "canh_chua_ca_loc": 2, "ca_keo_nuong": 2})


class PauseTest(unittest.TestCase):
    def test_pause_gather_freezes_counters(self):
        with Workdir() as w:
            inp = write_json(w.path("i.json"), frames(
                {"tick": 0, "move": [1, 0]},
                {"tick": 5, "pause": True}, {"tick": 6, "pause": False},
                {"tick": 7, "interact": True},  # cạnh hành động trong pause: bỏ qua
                {"tick": 10, "pause": True}))
            self.assertEqual(run("--mode", "gather", "--seed", "1", "--ticks", "15", "--inputs", inp,
                                 "--out", w.path("o.jsonl"), "--snapshot-every", "1")[0], 0)
            rows = read_jsonl(w.path("o.jsonl"))
            self.assertEqual([(e["name"], e["tick"]) for e in events(rows)], [("paused", 6), ("resumed", 11)])
            snap = {s["tick"]: s for s in snapshots(rows)}
            self.assertEqual(snap[6]["state"], "paused")
            for t in range(6, 11):
                self.assertEqual((snap[t]["sim_tick"], snap[t]["phase_tick"]), (5, 5))
                self.assertEqual(snap[t]["time_left_ticks"], snap[5]["time_left_ticks"])
                self.assertEqual(snap[t]["player"]["pos"], snap[5]["player"]["pos"])
            self.assertEqual((snap[11]["state"], snap[11]["sim_tick"]), ("playing", 6))  # chạy ngay bước resumed
            self.assertGreater(snap[11]["player"]["pos"][0], snap[10]["player"]["pos"][0])
            self.assertEqual(rows[-1]["ticks"], 15)
            self.assertEqual(rows[-1]["sim_tick"], 10)

    def test_pause_freezes_shop_timer(self):
        with Workdir() as w:
            sc = write_json(w.path("s.json"), fast())
            inp = write_json(w.path("i.json"), frames(
                {"tick": 0, "interact": True},
                {"tick": 10, "pause": True}, {"tick": 11, "pause": False, "shop_done": True},
                {"tick": 110, "pause": True, "shop_done": False}))
            self.assertEqual(run("--mode", "day", "--seed", "1", "--ticks", "2000", "--scenario", sc,
                                 "--inputs", inp, "--out", w.path("o.jsonl"))[0], 0)
            rows = read_jsonl(w.path("o.jsonl"))
            se = events(rows, "shop_end")[0]
            self.assertEqual(se["data"], {"reason": "time"})  # shop_done trong pause bị bỏ qua
            self.assertEqual(se["tick"], 2 + 600 + 100)       # 100 tick pause không tính vào 600 tick hoạt động


class DayScenarioTest(unittest.TestCase):
    def bad(self, sc):
        with Workdir() as w:
            p = write_json(w.path("s.json"), sc)
            return run("--mode", "day", "--seed", "1", "--ticks", "5", "--scenario", p, "--out", w.path("o.jsonl"))[0]

    def test_rejections(self):
        self.assertEqual(self.bad({"quan": {"stock": {"ca_loc": 1}}}), 2)
        self.assertEqual(self.bad({"quan": {"reputation": 4}}), 2)
        self.assertEqual(self.bad({"day": {"money": 300, "earned": 200}}), 2)
        self.assertEqual(self.bad({"day": {"money": 100}}), 2)
        self.assertEqual(self.bad({"day": {"upgrades": {"oxygen": 3}}}), 2)
        self.assertEqual(self.bad({"day": {"upgrades": {"weapon": 1}}}), 2)
        self.assertEqual(self.bad({"day": {"foo": 1}}), 2)
        self.assertEqual(self.bad({"day": {"day_plan": [{"day": 1, "dishes": {"goi_bong_sung": 1},
                                                          "ingredients": {"bong_sung": 1}}]}}), 2)
        self.assertEqual(self.bad({"day": {"day_plan": [{"day": 1, "dishes": {"pho": 1}}]}}), 2)
        self.assertEqual(self.bad({"river": {}}), 2)

    def test_day_plan_override(self):
        with Workdir() as w:
            p = write_json(w.path("s.json"), {"day": {"money": 0, "earned": 0, "reputation": 4.5,
                                                      "day_plan": [{"day": 1, "dishes": {"lau_mam": 2}}]}})
            self.assertEqual(run("--mode", "day", "--seed", "1", "--ticks", "1", "--scenario", p,
                                 "--out", w.path("o.jsonl"))[0], 0)
            rows = read_jsonl(w.path("o.jsonl"))
            self.assertEqual(events(rows, "day_plan")[0]["data"]["ingredients"],
                             {"ca_linh": 4, "ca_keo": 2, "keo_neo": 2, "bong_dien_dien": 2})
            self.assertEqual(snapshots(rows)[0]["reputation"], 4.5)


class LiveDayTest(unittest.TestCase):
    def test_live_game_day_meta_and_inputs(self):
        from chonoi.contract import load_contract
        from chonoi.live import LiveGame
        from chonoi.scenario import load_scenario
        c = load_contract(FIXTURE)
        g = LiveGame("day", c["tuning"], load_scenario(None, "day", c["tuning"]), 1, days=2, contract=c)
        st = json.loads(g.state_json())
        self.assertEqual((st["mode"], st["phase"], st["day"], st["paused"]), ("day", "gather", 1, False))
        self.assertEqual(st["day_plan"]["dishes"], {"ca_loc_nuong_trui": 3, "goi_bong_sung": 3})
        for k in ("menu", "day_plan", "shop", "phase", "upgrades", "active_upgrades"):
            self.assertIn(k, st["meta"])
        self.assertIn("swim_speed", st["meta"])  # tuning của pha hiện tại
        self.assertEqual([e["name"] for e in st["events"]], ["day_start", "day_plan", "phase_start"])
        g.set_input({"pause": True})
        g._tick_once()
        st = json.loads(g.state_json())
        self.assertTrue(st["paused"])
        self.assertEqual(st["state"], "paused")
        g.set_input({"pause": False, "buy": "oxygen", "shop_done": True})
        with self.assertRaises(ValueError):
            g.set_input({"buy": ""})


if __name__ == "__main__":
    unittest.main()
