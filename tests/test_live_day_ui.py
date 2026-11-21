"""Live mode day: nhịp giữ cho màn chờ UI, pause resume, mua/shop_done, kết quả ngày, bảng xếp hạng."""

import json
import os
import tempfile
import unittest

from chonoi.contract import load_contract
from chonoi.live import LiveGame
from chonoi.scenario import load_scenario


def _game(days=1, **kw):
    c = load_contract()
    t = c["tuning"]
    sc = load_scenario(None, "day", t, c["contract_version"])
    return LiveGame("day", t, sc, 1, days=days, contract=c, **kw)


def _tick(g, n=1, **inp):
    for _ in range(n):
        g.set_input(inp)
        g._tick_once()


def _state(g):
    return json.loads(g.state_json())


class HoldTest(unittest.TestCase):
    def test_hold_for_ui_freezes_sim_until_released(self):
        g = _game(hold_for_ui=True)
        _tick(g, 30)
        self.assertEqual(_state(g)["tick"], 0)
        self.assertTrue(_state(g)["held"])
        g.set_input({"hold": False})
        _tick(g, 5)
        self.assertEqual(_state(g)["tick"], 5)

    def test_hold_must_be_bool(self):
        g = _game()
        with self.assertRaises(ValueError):
            g.set_input({"hold": "yes"})

    def test_default_runs_immediately_and_never_holds(self):
        g = _game()
        _tick(g, 3)
        self.assertEqual(_state(g)["tick"], 3)
        self.assertFalse(_state(g)["held"])

    def test_phase_change_rehold(self):
        g = _game(hold_for_ui=True)
        g.set_input({"hold": False})
        _tick(g, 1, interact=False)
        # đứng ở bến: interact cập bến -> sang quán, server giữ lại cho EveningIntro
        _tick(g, 2, interact=True)
        _tick(g, 1, interact=False)
        st = _state(g)
        self.assertEqual(st["phase"], "quan")
        self.assertTrue(st["held"])
        t0 = st["tick"]
        _tick(g, 20)
        self.assertEqual(_state(g)["tick"], t0)


class PauseTest(unittest.TestCase):
    def test_pause_pulse_toggles_and_resumes(self):
        g = _game()
        _tick(g, 2, pause=True)
        _tick(g, 1, pause=False)
        self.assertTrue(_state(g)["paused"])
        before = _state(g)["sim_tick"]
        _tick(g, 20, pause=False)
        self.assertEqual(_state(g)["sim_tick"], before)
        _tick(g, 1, pause=True)
        _tick(g, 1, pause=False)
        st = _state(g)
        self.assertFalse(st["paused"])
        _tick(g, 5)
        self.assertGreater(_state(g)["sim_tick"], before)


class ShopAndResultTest(unittest.TestCase):
    def _to_shop(self, g):
        _tick(g, 1)
        _tick(g, 1, interact=True)
        _tick(g, 1, interact=False)
        self.assertEqual(_state(g)["phase"], "quan")
        # chạy hết ca tối bằng cách bỏ qua giờ
        while _state(g)["phase"] == "quan":
            _tick(g, 50)

    def test_day_result_and_shop_done(self):
        g = _game()
        self._to_shop(g)
        st = _state(g)
        self.assertEqual(st["phase"], "shop")
        self.assertIn("day_result", st)
        for k in ("served", "left", "money", "tip", "rep_delta", "reputation"):
            self.assertIn(k, st["day_result"])
        _tick(g, 1, buy="oxygen")  # không đủ tiền
        ev = [e for e in _state(g)["events"] if e["name"] in ("buy_failed", "bought")]
        self.assertTrue(ev)
        _tick(g, 1, shop_done=True)
        st = _state(g)
        self.assertTrue(st["finished"])
        self.assertEqual(st["reason"], "days_complete")
        self.assertEqual(st["summary"]["days_completed"], 1)

    def test_meta_has_spoiled_below(self):
        self.assertEqual(_state(_game())["meta"]["spoiled_below"], 30)


class LeaderboardTest(unittest.TestCase):
    def _play(self, days, **kw):
        g = _game(days=days, **kw)
        for _ in range(days):
            _tick(g, 1)
            _tick(g, 1, interact=True)
            _tick(g, 1, interact=False)
            while _state(g)["phase"] == "quan":
                _tick(g, 50)
            _tick(g, 1, shop_done=True)
            _tick(g, 1, shop_done=False)
        return g

    def test_records_one_entry_after_five_days(self):
        with tempfile.TemporaryDirectory() as d:
            store = os.path.join(d, "lb.json")
            g = self._play(5, leaderboard_path=store, player_name="Út Sen")
            self.assertTrue(_state(g)["finished"])
            data = json.load(open(store, encoding="utf-8"))
            self.assertEqual(len(data["entries"]), 1)
            self.assertEqual(data["entries"][0]["name"], "Út Sen")
            self.assertEqual(data["entries"][0]["days_completed"], 5)
            _tick(g, 5)
            self.assertEqual(len(json.load(open(store, encoding="utf-8"))["entries"]), 1)
            lb = json.loads(g.leaderboard_json())
            self.assertTrue(lb["enabled"])
            self.assertEqual(len(lb["entries"]), 1)

    def test_no_entry_for_fewer_days(self):
        with tempfile.TemporaryDirectory() as d:
            store = os.path.join(d, "lb.json")
            self._play(2, leaderboard_path=store, player_name="X")
            self.assertFalse(os.path.exists(store))

    def test_disabled_without_flag(self):
        self.assertFalse(json.loads(_game().leaderboard_json())["enabled"])


class WebStaticTest(unittest.TestCase):
    def test_client_sends_edge_buttons_and_hold(self):
        with open(os.path.join(os.path.dirname(__file__), "..", "chonoi", "web", "index.html"), encoding="utf-8") as f:
            html = f.read()
        for needle in ("body.shop_done", "body.buy", "body.pause", "hold:", "/leaderboard", 'setScreen("dayResult")', "function syncHold("):
            self.assertIn(needle, html)


if __name__ == "__main__":
    unittest.main()
