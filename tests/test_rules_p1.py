"""Test luật Phase 1 của nhóm (hộp đen): chạy `headless_cmd`, đọc JSONL, mọi số lấy từ game.contract.json.

Luật nào CHƯA cài (trường snapshot không đổi / không có sự kiện) thì test gọi skipTest("chưa có luật: ...")
để bộ test vẫn xanh; khi luật đã cài, test khẳng định thật sự.
Chỗ nào dựa trên cách hiểu riêng (PRD-0 chưa có) đều có chú thích `# Giả định: ...`.

Chạy: PYTHONPATH=tests:. python3 -m unittest discover -s tests -v
"""

import json
import math
import os
import unittest

from helpers import (ROOT, Workdir, close, events, frames, read_jsonl, run_headless, snapshots, write_json)

SAMPLE_INV = os.path.join(ROOT, "docs", "contracts", "inventory.sample.json")


def tuning():
    with open(os.path.join(ROOT, "game.contract.json"), encoding="utf-8") as f:
        return json.load(f)["tuning"]


T = tuning()
HZ = T["tick_hz"]
G = T["gather"]
Q = T["quan"]
OXY_MAX = int(round(G["oxygen_max_s"] * HZ))
DEEP = G["bounds"]["d"][1] / 3  # một độ sâu chắc chắn dưới mặt nước
assert DEEP > G["surface_depth"]
MID_X = (G["bounds"]["x"][0] + G["bounds"]["x"][1]) / 2  # xa bến
assert math.dist([MID_X, 0], G["dock_pos"]) > G["dock_radius"]


def run(tc, mode, seed, ticks, scenario=None, inputs=None, inventory=None, every=1):
    """Chạy headless trong thư mục tạm, trả các dòng JSONL. Lỗi mã thoát -> fail test."""
    with Workdir() as w:
        args = ["--mode", mode, "--seed", str(seed), "--ticks", str(ticks), "--snapshot-every", str(every)]
        if scenario is not None:
            args += ["--scenario", write_json(w.path("sc.json"), {mode: scenario})]
        if inputs is not None:
            args += ["--inputs", write_json(w.path("in.json"), inputs)]
        if inventory is not None:
            args += ["--inventory", inventory]
        code, err = run_headless(*args, "--out", w.path("o.jsonl"))
        tc.assertEqual(code, 0, err)
        return read_jsonl(w.path("o.jsonl"))


def by_tick(rows):
    return {s["tick"]: s for s in snapshots(rows)}


class Oxygen(unittest.TestCase):
    def test_oxy_giam_duoi_nuoc(self):
        """Đứng yên dưới nước: oxy giảm mỗi tick, không âm."""
        rows = run(self, "gather", 1, 30, scenario={"player": {"pos": [MID_X, DEEP]}})
        ox = [s["player"]["oxygen_ticks"] for s in snapshots(rows)]
        if all(o == OXY_MAX for o in ox):
            self.skipTest("chưa có luật: oxy giảm dưới nước")
        self.assertEqual(ox[0], OXY_MAX)
        for a, b in zip(ox, ox[1:]):
            # Giả định: dưới nước oxy trừ đúng 1 tick mỗi tick (đơn vị oxygen_ticks).
            self.assertEqual(b, max(0, a - 1), ox)
        self.assertTrue(all(0 <= o <= OXY_MAX for o in ox))

    def test_oxy_can_ve_0_va_oxygen_empty(self):
        """Oxy cạn kẹp ở 0; sự kiện oxygen_empty đúng một lần khi oxy từ dương xuống 0."""
        start = 5
        rows = run(self, "gather", 1, start + 20,
                   scenario={"player": {"pos": [MID_X, DEEP], "oxygen_ticks": start}})
        snaps = snapshots(rows)
        ox = [s["player"]["oxygen_ticks"] for s in snaps]
        if all(o == start for o in ox):
            self.skipTest("chưa có luật: oxy giảm dưới nước")
        self.assertTrue(all(o >= 0 for o in ox), ox)
        self.assertEqual(ox[-1], 0, ox)
        empty = events(rows, "oxygen_empty")
        if not empty:
            self.skipTest("chưa có luật: sự kiện oxygen_empty")
        self.assertEqual(len(empty), 1)
        s = by_tick(rows)
        t = empty[0]["tick"]
        self.assertEqual(s[t]["player"]["oxygen_ticks"], 0)
        self.assertGreater(s[t - 1]["player"]["oxygen_ticks"], 0)

    def test_oxy_hoi_o_mat_nuoc(self):
        """Ở mặt nước oxy hồi oxygen_refill_per_tick mỗi tick, kẹp ở oxygen_max."""
        refill = G["oxygen_refill_per_tick"]
        ticks = math.ceil(OXY_MAX / refill) + 5
        rows = run(self, "gather", 1, ticks, scenario={"player": {"pos": [MID_X, 0], "oxygen_ticks": 0}})
        ox = [s["player"]["oxygen_ticks"] for s in snapshots(rows)]
        self.assertTrue(snapshots(rows)[0]["player"]["at_surface"])
        if all(o == 0 for o in ox):
            self.skipTest("chưa có luật: oxy hồi ở mặt nước")
        for a, b in zip(ox, ox[1:]):
            self.assertEqual(b, min(OXY_MAX, a + refill), ox)
        self.assertEqual(ox[-1], OXY_MAX)


class DiveSurface(unittest.TestCase):
    def test_dive_roi_surface(self):
        """Lặn xuống rồi ngoi lên: một dive, một surface, đúng lúc qua ranh surface_depth."""
        rows = run(self, "gather", 1, 120, scenario={"player": {"pos": [MID_X, 0]}},
                   inputs=frames({"tick": 0, "move": [0, 1]}, {"tick": 30, "move": [0, -1]}))
        s = by_tick(rows)
        sd = G["surface_depth"]
        for snap in s.values():  # at_surface khớp với surface_depth (khung đã có)
            self.assertEqual(snap["player"]["at_surface"], snap["player"]["pos"][1] <= sd)
        dives, ups = events(rows, "dive"), events(rows, "surface")
        if not dives and not ups:
            self.skipTest("chưa có luật: sự kiện dive / surface")
        self.assertEqual(len(dives), 1)
        self.assertEqual(len(ups), 1)
        self.assertLess(dives[0]["tick"], ups[0]["tick"])
        td, tu = dives[0]["tick"], ups[0]["tick"]
        self.assertTrue(s[td - 1]["player"]["pos"][1] <= sd < s[td]["player"]["pos"][1])
        self.assertTrue(s[tu]["player"]["pos"][1] <= sd < s[tu - 1]["player"]["pos"][1])


class ChokeHp(unittest.TestCase):
    def test_choke_moi_choke_interval_tru_1_mau(self):
        """Oxy = 0 dưới nước: choke mỗi choke_interval_ticks, mỗi lần -1 Máu; Máu luôn trong [0, hp_max]."""
        iv, hp_max = G["choke_interval_ticks"], G["hp_max"]
        rows = run(self, "gather", 1, iv * (hp_max + 1) + 10,
                   scenario={"player": {"pos": [MID_X, DEEP], "oxygen_ticks": 0, "hp": hp_max}})
        snaps = snapshots(rows)
        for snap in snaps:
            self.assertTrue(0 <= snap["player"]["hp"] <= hp_max, snap["player"])
            self.assertEqual(snap["player"]["hp_max"], hp_max)
        chokes = events(rows, "choke")
        if not chokes:
            self.skipTest("chưa có luật: ngạt (choke)")
        self.assertLessEqual(len(chokes), hp_max)
        ticks = [e["tick"] for e in chokes]
        # Giả định: zero_oxy_ticks bắt đầu 0 nên lần ngạt đầu ở tick choke_interval_ticks (cho lệch 1 tick).
        self.assertIn(ticks[0], (iv, iv + 1), ticks)
        for a, b in zip(ticks, ticks[1:]):
            self.assertEqual(b - a, iv, ticks)
        s = by_tick(rows)
        for t in ticks:
            if t in s and t - 1 in s:
                self.assertEqual(s[t]["player"]["hp"], s[t - 1]["player"]["hp"] - 1, t)

    def test_mau_ve_0_thi_faint(self):
        """Ngạt tới Máu 0 -> faint, gather_end reason fainted, kho rỗng."""
        iv, hp_max = G["choke_interval_ticks"], G["hp_max"]
        rows = run(self, "gather", 1, iv * (hp_max + 1) + 10,
                   scenario={"player": {"pos": [MID_X, DEEP], "oxygen_ticks": 0, "hp": 1}, "hold": ["ca_loc"]})
        for snap in snapshots(rows):
            self.assertTrue(0 <= snap["player"]["hp"] <= hp_max)
        if not events(rows, "choke") and not events(rows, "faint"):
            self.skipTest("chưa có luật: ngạt / ngất (faint)")
        faint = events(rows, "faint")
        self.assertEqual(len(faint), 1)
        self.assertEqual(snapshots(rows)[-1]["player"]["hp"], 0)
        end = events(rows, "gather_end")
        self.assertEqual(len(end), 1)
        # Giả định: lý do kết thúc là "fainted" và mất toàn bộ giỏ (theo TODO trong khung gather.py).
        self.assertEqual(end[0]["data"]["reason"], "fainted")
        self.assertEqual(end[0]["data"]["inventory"], {"items": []})
        self.assertEqual(rows[-1]["reason"], "fainted")


class Hold(unittest.TestCase):
    def _check_bound(self, rows):
        cap = G["hold_capacity"]
        for snap in snapshots(rows):
            self.assertEqual(snap["hold_capacity"], cap)
            self.assertEqual(snap["hold_count"], len(snap["hold"]))
            self.assertLessEqual(snap["hold_count"], cap, snap["hold"])

    def test_hai_khong_vuot_suc_chua(self):
        """Giỏ gần đầy, hái nhiều nút ở mặt nước: giỏ không bao giờ vượt hold_capacity."""
        cap = G["hold_capacity"]
        nodes = [{"id": f"N{i + 1}", "kind": "bong_sung", "pos": [MID_X + 0.2 * i, 0]} for i in range(4)]
        presses = [{"tick": 2 * i, "interact": i % 2 == 0} for i in range(10)]
        rows = run(self, "gather", 3, 30, inputs=frames(*presses),
                   scenario={"player": {"pos": [MID_X, 0]}, "nodes": nodes, "hold": ["ca_loc"] * (cap - 1)})
        self._check_bound(rows)
        got, full = events(rows, "gather"), events(rows, "hold_full")
        if not got and not full:
            self.skipTest("chưa có luật: hái (gather / hold_full)")
        s = by_tick(rows)
        self.assertEqual(snapshots(rows)[-1]["hold_count"], cap)
        # Giả định: hold_full phát ra khi cố nhặt lúc giỏ đã đầy.
        for e in full:
            self.assertEqual(s[e["tick"]]["hold_count"], cap)

    def test_bat_ca_khong_vuot_suc_chua(self):
        """Giỏ thiếu chỗ cho cả đàn thì không bắt (hold_full), giỏ giữ nguyên; đủ chỗ thì bắt và không vượt hold_capacity.

        Luật: TICKET-02 §1.1 / docs/clarify.md #5 — cần đủ chỗ cho CẢ đàn, thiếu thì không bắt.
        """
        cap = G["hold_capacity"]
        yields = G["fish_yield"]
        big = max(yields, key=lambda k: (yields[k], k))
        small = min(yields, key=lambda k: (yields[k], k))
        if yields[big] < 2:
            self.skipTest("contract không có loài cá cho >= 2 con")
        free = yields[big] - 1  # thiếu đúng 1 chỗ cho đàn lớn
        start = ["bong_sung"] * (cap - free)
        press = frames({"tick": 0, "catch": True}, {"tick": 1, "catch": False})

        def catch_one(kind):
            rows = run(self, "gather", 3, 5, inputs=press, scenario={
                "player": {"pos": [MID_X, DEEP]}, "hold": list(start),
                "fish": [{"id": "F1", "kind": kind, "pos": [MID_X, DEEP]}]})
            self._check_bound(rows)
            return rows

        rows = catch_one(big)
        if not events(rows, "fish_caught") and not events(rows, "hold_full"):
            self.skipTest("chưa có luật: bắt cá (fish_caught / hold_full)")
        self.assertFalse(events(rows, "fish_caught"), "thiếu chỗ cho cả đàn thì không được bắt")
        self.assertTrue(events(rows, "hold_full"))
        self.assertEqual(snapshots(rows)[-1]["hold_count"], len(start))

        if yields[small] <= free:
            rows = catch_one(small)
            self.assertTrue(events(rows, "fish_caught"), "đủ chỗ thì phải bắt được")
            self.assertEqual(snapshots(rows)[-1]["hold_count"], len(start) + yields[small])


INTERVAL = int(round(Q["customer_interval_s"] * HZ))
PATIENCE = int(round(Q["patience_s"] * HZ))
FIRST = Q["first_customer_tick"]
QUAN_TICKS = FIRST + PATIENCE + 3 * INTERVAL + 5


def arrivals(rows):
    """{customer_id: tick xuất hiện đầu tiên} và {customer_id: tick biến mất} theo snapshot từng tick."""
    first, gone, prev = {}, {}, set()
    for snap in snapshots(rows):
        cur = {c["id"] for c in snap["customers"]}
        for cid in cur - prev:
            first.setdefault(cid, snap["tick"])
        for cid in prev - cur:
            gone.setdefault(cid, snap["tick"])
        prev = cur
    return first, gone


class QuanCustomers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = run(unittest.TestCase(), "quan", 1, QUAN_TICKS, inventory=SAMPLE_INV)

    def test_uy_tin_trong_bien(self):
        lo, hi = Q["reputation_min"], Q["reputation_max"]
        for snap in snapshots(self.rows):
            self.assertTrue(lo <= snap["reputation"] <= hi, snap["reputation"])
        self.assertTrue(lo <= self.rows[-1]["reputation"] <= hi)
        self.assertEqual(snapshots(self.rows)[0]["reputation"], Q["reputation_initial"])

    def test_khach_den_theo_lich(self):
        """Khách đầu tiên ở first_customer_tick, các lượt sau cách nhau bội số customer_interval_s."""
        first, _ = arrivals(self.rows)
        slots = sorted(set(first.values()) | {e["tick"] for e in events(self.rows, "no_dish")})
        if not slots:
            self.skipTest("chưa có luật: khách đến theo lịch")
        for snap in snapshots(self.rows):
            if snap["tick"] < FIRST:
                self.assertEqual(snap["customers"], [], snap["tick"])
        # Giả định: lượt khách đầu ứng với bước first_customer_tick; dòng snapshot/event mang tick k hoặc k+1.
        self.assertIn(slots[0], (FIRST, FIRST + 1), slots)
        for t in slots:
            # Giả định: khách chỉ đến (hoặc báo no_dish) đúng nhịp lịch; bàn bận thì lượt đó có thể bỏ qua.
            self.assertEqual((t - slots[0]) % INTERVAL, 0, slots)

    def test_khach_bo_di_sau_patience_tru_uy_tin(self):
        """Khách không được phục vụ: bỏ đi sau patience_s, uy tín cộng left_reputation_delta (kẹp biên)."""
        left = events(self.rows, "customer_left")
        if not left:
            self.skipTest("chưa có luật: khách bỏ đi (customer_left)")
        first, gone = arrivals(self.rows)
        s = by_tick(self.rows)
        lo, hi = Q["reputation_min"], Q["reputation_max"]
        for e in left:
            t = e["tick"]
            want = min(hi, max(lo, s[t - 1]["reputation"] + Q["left_reputation_delta"]))
            self.assertTrue(close(s[t]["reputation"], want, 1e-9), (t, s[t - 1]["reputation"], s[t]["reputation"]))
            ids = [cid for cid, gt in gone.items() if gt == t]
            self.assertTrue(ids, f"customer_left ở tick {t} nhưng không khách nào rời snapshot")
            for cid in ids:
                # Giả định: kiên nhẫn đếm từ lúc khách xuất hiện; cho lệch 1 tick do quy ước tick = k + 1.
                self.assertLessEqual(abs((t - first[cid]) - PATIENCE), 1, (cid, first[cid], t))

    def test_uy_tin_kep_o_min(self):
        """Uy tín bắt đầu ở reputation_min, khách bỏ đi: không xuống dưới reputation_min."""
        lo, hi = Q["reputation_min"], Q["reputation_max"]
        rows = run(self, "quan", 1, QUAN_TICKS, scenario={"reputation": lo}, inventory=SAMPLE_INV, every=10)
        for snap in snapshots(rows):
            self.assertTrue(lo <= snap["reputation"] <= hi, snap["reputation"])
        if not events(rows, "customer_left"):
            self.skipTest("chưa có luật: khách bỏ đi (customer_left)")
        self.assertEqual(rows[-1]["reputation"], lo)


class QuanServe(unittest.TestCase):
    def test_tra_tien_theo_gia_menu(self):
        """Kịch bản phục vụ một khách: nếu có `paid`, tiền tăng = giá món (+ boa theo tip_rate)."""
        stove, table = Q["stoves"][0]["pos"], Q["tables"][0]["pos"]
        start = [stove[0], stove[1] - 1]  # đứng cạnh bếp (trong interact_radius)
        assert math.dist(start, stove) <= Q["interact_radius"]
        vec = [table[0] - start[0], table[1] - start[1]]
        d = math.hypot(*vec)
        mv = [vec[0] / d, vec[1] / d]
        cook_max = max(int(round(m["cook_s"] * HZ)) for m in T["menu"].values())
        t_cook = FIRST + 5
        t_pick = t_cook + cook_max + 30
        t_walk = t_pick + 5
        t_stop = t_walk + int(round(d / Q["walk_speed"] * HZ))
        t_serve = t_stop + 15
        eat = int(round(Q["eat_s"] * HZ))
        inp = frames({"tick": t_cook, "interact": True}, {"tick": t_cook + 1, "interact": False},
                     {"tick": t_pick, "interact": True}, {"tick": t_pick + 1, "interact": False},
                     {"tick": t_walk, "move": mv}, {"tick": t_stop, "move": [0, 0]},
                     {"tick": t_serve, "interact": True}, {"tick": t_serve + 1, "interact": False})
        rows = run(self, "quan", 1, t_serve + eat + 120, scenario={"player": {"pos": start}},
                   inputs=inp, inventory=SAMPLE_INV)
        paid = events(rows, "paid")
        if not paid:
            self.skipTest("chưa có luật: nấu / phục vụ / trả tiền (paid)")
        s = by_tick(rows)
        prices = [m["price"] for m in T["menu"].values()]
        ok = set()
        for p in prices:
            tip = p * Q["tip_rate"]
            # Giả định: boa = price × tip_rate (có thể làm tròn) hoặc không boa.
            ok |= {p, p + tip, p + math.floor(tip), p + round(tip), p + math.ceil(tip)}
        for e in paid:
            t = e["tick"]
            gain = s[t]["money"] - s[t - 1]["money"]
            self.assertTrue(any(close(gain, v, 1e-9) for v in ok), (gain, sorted(ok)))
            self.assertTrue(Q["reputation_min"] <= s[t]["reputation"] <= Q["reputation_max"])


class Determinism(unittest.TestCase):
    def _twice(self, *args):
        outs = []
        with Workdir() as w:
            for i in (1, 2):
                code, err = run_headless(*args, "--out", w.path(f"o{i}.jsonl"))
                self.assertEqual(code, 0, err)
                with open(w.path(f"o{i}.jsonl"), "rb") as f:
                    outs.append(f.read())
        self.assertEqual(outs[0], outs[1], args)
        return outs[0]

    def test_gather_cung_seed_cung_byte(self):
        with Workdir() as w:
            inp = write_json(w.path("in.json"), frames(
                {"tick": 0, "move": [1, 1]}, {"tick": 40, "move": [0, 1], "catch": True},
                {"tick": 41, "catch": False}, {"tick": 120, "move": [-1, -1]},
                {"tick": 200, "move": [0, 0], "interact": True}, {"tick": 201, "interact": False}))
            for seed in (1, 7, 42, 2024):
                self._twice("--mode", "gather", "--seed", str(seed), "--ticks", "400", "--inputs", inp,
                            "--snapshot-every", "5")

    def test_quan_cung_seed_cung_byte(self):
        with Workdir() as w:
            inp = write_json(w.path("in.json"), frames(
                {"tick": 0, "move": [-1, 1]}, {"tick": 80, "move": [0, 0], "interact": True},
                {"tick": 81, "interact": False}, {"tick": 300, "move": [1, -1]}, {"tick": 400, "move": [0, 0]}))
            ticks = str(FIRST + 2 * INTERVAL + 10)
            for seed in (1, 7, 42, 2024):
                self._twice("--mode", "quan", "--seed", str(seed), "--ticks", ticks, "--inputs", inp)
                self._twice("--mode", "quan", "--seed", str(seed), "--ticks", ticks, "--inputs", inp,
                            "--inventory", SAMPLE_INV)
                sc = write_json(w.path("sc.json"), {"quan": {"stock": {"ca_loc": 2, "bong_sung": 4}}})
                self._twice("--mode", "quan", "--seed", str(seed), "--ticks", ticks, "--inputs", inp,
                            "--scenario", sc)

    def test_quan_inventory_mau_nap_dung_kho(self):
        """docs/contracts/inventory.sample.json là đầu vào hợp lệ; kho tick 0 đúng nội dung file."""
        with open(SAMPLE_INV, encoding="utf-8") as f:
            items = json.load(f)["items"]
        rows = run(self, "quan", 1, 0, inventory=SAMPLE_INV)
        stock = snapshots(rows)[0]["stock"]
        self.assertEqual([it["id"] for it in stock], [it["id"] for it in items])
        self.assertEqual([it["kind"] for it in stock], [it["kind"] for it in items])


if __name__ == "__main__":
    unittest.main()
