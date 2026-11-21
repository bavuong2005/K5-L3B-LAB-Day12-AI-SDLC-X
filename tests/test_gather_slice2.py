"""Test tập trung cho Gather Lát 2 (TV2): hái rau, bắt cá, giỏ đầy, ưu tiên bến, tích hợp kho.

Chạy hộp đen qua `headless_cmd` trong game.contract.json để giữ tính độc lập với khung.
Kiểm chính xác schema sự kiện chính thức theo PRD-0 Test Contract v1.0:
  - gather: {"node_id", "kind", "amount"}
  - fish_caught: {"fish_id", "kind", "yield"}
  - hold_full (hái): {"action": "gather", "node_id", "required", "free"}
  - hold_full (bắt): {"action": "catch", "fish_id", "required", "free"}
"""

import json
import os
import subprocess
import unittest

from chonoi.contract import load_contract
from chonoi.ids import IdAllocator
from chonoi.rng import Streams
from chonoi.sim.gather import GatherSim
from helpers import ROOT, Workdir, events, frames, headless_cmd, read_jsonl, run_headless, snapshots, write_json


def _tuning_gather():
    with open("game.contract.json", encoding="utf-8") as f:
        return json.load(f)["tuning"]["gather"]


def hold_kinds(hold):
    """Contract 1.3: giỏ headless là cá thể {id, kind, fresh}. So thứ tự kind, số lượng vẫn theo luật P1."""
    if hold and isinstance(hold[0], dict):
        return [h["kind"] for h in hold]
    return list(hold)


def item_counts(items):
    """Kho đếm {kind: n} hoặc mảng cá thể → số lượng theo kind."""
    if isinstance(items, dict):
        return {k: v for k, v in items.items() if v}
    counts = {}
    for it in items:
        counts[it["kind"]] = counts.get(it["kind"], 0) + 1
    return counts


class GatherSlice2PlantTests(unittest.TestCase):
    def test_harvest_at_surface_sets_regrow_and_regrows(self):
        g = _tuning_gather()
        regrow_ticks = int(round(g["regrow_s"] * 60))
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {"gather": {
                "player": {"pos": [20, 0]},
                "nodes": [{"id": "N1", "kind": "bong_dien_dien", "pos": [21, 0]}],
                "random_fish": False,
            }})
            inp = write_json(w.path("in.json"), frames(
                {"tick": 0, "interact": True},
                {"tick": 1, "interact": False},
                {"tick": 2, "interact": True},  # nút đang mọc lại -> không hái được
            ))
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "5",
                                     "--scenario", sc, "--inputs", inp,
                                     "--snapshot-every", "1", "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("o.jsonl"))
            gather_evs = events(rows, "gather")
            self.assertEqual(len(gather_evs), 1)
            self.assertEqual(gather_evs[0]["tick"], 1)
            self.assertEqual(gather_evs[0]["data"], {
                "node_id": "N1",
                "kind": "bong_dien_dien",
                "amount": g["node_yield"],
            })
            snaps = {s["tick"]: s for s in snapshots(rows)}
            self.assertEqual(hold_kinds(snaps[1]["hold"]), ["bong_dien_dien"] * g["node_yield"])
            self.assertFalse(snaps[1]["nodes"][0]["ready"])
            self.assertEqual(snaps[1]["nodes"][0]["regrow_ticks"], regrow_ticks)
            # Nút chưa mọc lại nên lần interact ở tick 2 không thay đổi giỏ
            self.assertEqual(hold_kinds(snaps[3]["hold"]), ["bong_dien_dien"] * g["node_yield"])

        # Kiểm tra nút mọc lại sau regrow_ticks rồi hái lại được
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {"gather": {
                "player": {"pos": [20, 0]},
                "nodes": [{"id": "N1", "kind": "bong_sung", "pos": [20.5, 0], "regrow_ticks": 3}],
                "random_fish": False,
            }})
            inp = write_json(w.path("in.json"), frames(
                {"tick": 0, "interact": True},   # regrow_ticks còn 2 -> chưa ready
                {"tick": 1, "interact": False},
                {"tick": 2, "interact": True},   # bước này regrow_ticks về 0 -> node_regrown rồi hái được
            ))
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "4",
                                     "--scenario", sc, "--inputs", inp,
                                     "--snapshot-every", "1", "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("o.jsonl"))
            regrown = events(rows, "node_regrown")
            self.assertEqual(len(regrown), 1)
            self.assertEqual(regrown[0]["tick"], 3)
            self.assertEqual(regrown[0]["data"]["node_id"], "N1")
            gather_evs = events(rows, "gather")
            self.assertEqual(len(gather_evs), 1)
            self.assertEqual(gather_evs[0]["tick"], 3)
            self.assertEqual(hold_kinds(snapshots(rows)[-1]["hold"]), ["bong_sung"] * g["node_yield"])

    def test_harvest_blocked_underwater_and_out_of_radius(self):
        g = _tuning_gather()
        with Workdir() as w:
            # Dưới nước nhưng trong bán kính phẳng
            sc = write_json(w.path("sc.json"), {"gather": {
                "player": {"pos": [20, g["surface_depth"] + 0.5]},
                "nodes": [{"id": "N1", "kind": "bong_dien_dien", "pos": [20, 0]}],
                "random_fish": False,
            }})
            inp = write_json(w.path("in.json"), frames({"tick": 0, "interact": True}))
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "2",
                                     "--scenario", sc, "--inputs", inp, "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("o.jsonl"))
            self.assertEqual(events(rows, "gather"), [])
            self.assertEqual(snapshots(rows)[-1]["hold"], [])

            # Mặt nước nhưng ngoài interact_radius
            sc2 = write_json(w.path("sc2.json"), {"gather": {
                "player": {"pos": [20, 0]},
                "nodes": [{"id": "N1", "kind": "bong_dien_dien", "pos": [20 + g["interact_radius"] + 0.5, 0]}],
                "random_fish": False,
            }})
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "2",
                                     "--scenario", sc2, "--inputs", inp, "--out", w.path("o2.jsonl"))
            self.assertEqual(code, 0, err)
            rows2 = read_jsonl(w.path("o2.jsonl"))
            self.assertEqual(events(rows2, "gather"), [])
            self.assertEqual(snapshots(rows2)[-1]["hold"], [])

    def test_harvest_deterministic_distance_and_id_tiebreak(self):
        with Workdir() as w:
            # Hai nút cách đều 1.0 đơn vị; N10 đứng trước N2 trong scenario nhưng N2 phải được chọn trước
            sc = write_json(w.path("sc.json"), {"gather": {
                "player": {"pos": [30, 0]},
                "nodes": [
                    {"id": "N10", "kind": "bong_sung", "pos": [31, 0]},
                    {"id": "N2", "kind": "bong_dien_dien", "pos": [29, 0]},
                ],
                "random_fish": False,
            }})
            inp = write_json(w.path("in.json"), frames({"tick": 0, "interact": True}))
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "2",
                                     "--scenario", sc, "--inputs", inp, "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            gather_evs = events(read_jsonl(w.path("o.jsonl")), "gather")
            self.assertEqual(len(gather_evs), 1)
            self.assertEqual(gather_evs[0]["data"]["node_id"], "N2")

            # Nút gần hơn luôn thắng dù id lớn hơn
            sc2 = write_json(w.path("sc2.json"), {"gather": {
                "player": {"pos": [30, 0]},
                "nodes": [
                    {"id": "N1", "kind": "bong_dien_dien", "pos": [31.5, 0]},
                    {"id": "N9", "kind": "bong_sung", "pos": [29.5, 0]},
                ],
                "random_fish": False,
            }})
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "2",
                                     "--scenario", sc2, "--inputs", inp, "--out", w.path("o2.jsonl"))
            self.assertEqual(code, 0, err)
            gather_evs2 = events(read_jsonl(w.path("o2.jsonl")), "gather")
            self.assertEqual(gather_evs2[0]["data"]["node_id"], "N9")


class GatherSlice2FishTests(unittest.TestCase):
    def test_catch_underwater_yield_removal_and_cooldown(self):
        g = _tuning_gather()
        cd_ticks = int(round(g["catch_cooldown_s"] * 60))
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {"gather": {
                "player": {"pos": [30, 10]},
                "fish": [
                    {"id": "F1", "kind": "ca_linh", "pos": [30.5, 10]},
                    {"id": "F2", "kind": "ca_loc", "pos": [31.0, 10]},
                ],
                "nodes": [{"id": "N1", "kind": "bong_sung", "pos": [50, 0]}],
            }})
            inp = write_json(w.path("in.json"), frames(
                {"tick": 0, "catch": True},            # bắt F1 (gần hơn), đặt cooldown = cd_ticks
                {"tick": 1, "catch": False},
                {"tick": 2, "catch": True},            # đang hồi chiêu -> không bắt được F2
                {"tick": 3, "catch": False},
                {"tick": cd_ticks, "catch": True},     # vừa hết hồi chiêu -> bắt được F2
            ))
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", str(cd_ticks + 2),
                                     "--scenario", sc, "--inputs", inp,
                                     "--snapshot-every", "1", "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("o.jsonl"))
            caught = events(rows, "fish_caught")
            self.assertEqual(len(caught), 2)
            self.assertEqual(caught[0]["tick"], 1)
            self.assertEqual(caught[0]["data"], {
                "fish_id": "F1",
                "kind": "ca_linh",
                "yield": g["fish_yield"]["ca_linh"],
            })
            self.assertEqual(caught[1]["tick"], cd_ticks + 1)
            self.assertEqual(caught[1]["data"], {
                "fish_id": "F2",
                "kind": "ca_loc",
                "yield": g["fish_yield"]["ca_loc"],
            })

            snaps = {s["tick"]: s for s in snapshots(rows)}
            self.assertEqual(snaps[1]["player"]["catch_cd_ticks"], cd_ticks)
            self.assertEqual(hold_kinds(snaps[1]["hold"]), ["ca_linh"] * g["fish_yield"]["ca_linh"])
            self.assertEqual([f["id"] for f in snaps[1]["fish"]], ["F2"])
            # Ở tick 3 (sau lần bấm hụt vì cooldown ở tick 2), F2 vẫn còn
            self.assertEqual([f["id"] for f in snaps[3]["fish"]], ["F2"])
            # Sau khi hết cooldown ở tick cd_ticks + 1, F2 đã được bắt
            self.assertEqual(snaps[cd_ticks + 1]["fish"], [])
            expected_hold = ["ca_linh"] * g["fish_yield"]["ca_linh"] + ["ca_loc"] * g["fish_yield"]["ca_loc"]
            self.assertEqual(hold_kinds(snaps[cd_ticks + 1]["hold"]), expected_hold)

    def test_catch_blocked_at_surface_and_out_of_radius(self):
        g = _tuning_gather()
        with Workdir() as w:
            # Đang ở mặt nước dù cá nằm trong catch_radius
            sc = write_json(w.path("sc.json"), {"gather": {
                "player": {"pos": [30, g["surface_depth"]]},
                "fish": [{"id": "F1", "kind": "ca_loc", "pos": [30, g["surface_depth"] + 0.5]}],
            }})
            inp = write_json(w.path("in.json"), frames({"tick": 0, "catch": True}))
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "2",
                                     "--scenario", sc, "--inputs", inp, "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("o.jsonl"))
            self.assertEqual(events(rows, "fish_caught"), [])
            self.assertEqual(len(snapshots(rows)[-1]["fish"]), 1)

            # Dưới nước nhưng ngoài catch_radius
            sc2 = write_json(w.path("sc2.json"), {"gather": {
                "player": {"pos": [30, 10]},
                "fish": [{"id": "F1", "kind": "ca_loc", "pos": [30 + g["catch_radius"] + 0.5, 10]}],
            }})
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "2",
                                     "--scenario", sc2, "--inputs", inp, "--out", w.path("o2.jsonl"))
            self.assertEqual(code, 0, err)
            rows2 = read_jsonl(w.path("o2.jsonl"))
            self.assertEqual(events(rows2, "fish_caught"), [])
            self.assertEqual(len(snapshots(rows2)[-1]["fish"]), 1)

    def test_catch_deterministic_distance_and_id_tiebreak(self):
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {"gather": {
                "player": {"pos": [30, 10]},
                "fish": [
                    {"id": "F10", "kind": "ca_loc", "pos": [31, 10]},
                    {"id": "F2", "kind": "ca_linh", "pos": [29, 10]},
                ],
            }})
            inp = write_json(w.path("in.json"), frames({"tick": 0, "catch": True}))
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "2",
                                     "--scenario", sc, "--inputs", inp, "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            caught = events(read_jsonl(w.path("o.jsonl")), "fish_caught")
            self.assertEqual(len(caught), 1)
            self.assertEqual(caught[0]["data"]["fish_id"], "F2")


class GatherSlice2CapacityDockAndInventoryTests(unittest.TestCase):
    def test_hold_capacity_never_exceeded(self):
        g = _tuning_gather()
        cap = g["hold_capacity"]
        with Workdir() as w:
            # Giỏ đã đầy: hái nút phải báo hold_full, không tăng giỏ, nút vẫn ready
            sc = write_json(w.path("sc.json"), {"gather": {
                "player": {"pos": [20, 0]},
                "hold": ["ca_loc"] * cap,
                "nodes": [{"id": "N1", "kind": "bong_sung", "pos": [20.5, 0]}],
                "random_fish": False,
            }})
            inp = write_json(w.path("in.json"), frames({"tick": 0, "interact": True}))
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "2",
                                     "--scenario", sc, "--inputs", inp, "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("o.jsonl"))
            self.assertEqual(events(rows, "gather"), [])
            self.assertEqual(len(events(rows, "hold_full")), 1)
            last = snapshots(rows)[-1]
            self.assertEqual(last["hold_count"], cap)
            self.assertTrue(last["nodes"][0]["ready"])

            # Giỏ đã đầy: bắt cá phải báo hold_full, không tăng giỏ, cá vẫn còn
            sc2 = write_json(w.path("sc2.json"), {"gather": {
                "player": {"pos": [30, 10]},
                "hold": ["ca_loc"] * cap,
                "fish": [{"id": "F1", "kind": "ca_loc", "pos": [30.5, 10]}],
            }})
            inp2 = write_json(w.path("in2.json"), frames({"tick": 0, "catch": True}))
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "2",
                                     "--scenario", sc2, "--inputs", inp2, "--out", w.path("o2.jsonl"))
            self.assertEqual(code, 0, err)
            rows2 = read_jsonl(w.path("o2.jsonl"))
            self.assertEqual(events(rows2, "fish_caught"), [])
            self.assertEqual(len(events(rows2, "hold_full")), 1)
            last2 = snapshots(rows2)[-1]
            self.assertEqual(last2["hold_count"], cap)
            self.assertEqual(len(last2["fish"]), 1)

            # Giỏ thiếu chỗ cho fish_yield của ca_linh: tuyệt đối không vượt hold_capacity
            if g["fish_yield"]["ca_linh"] > 1:
                sc3 = write_json(w.path("sc3.json"), {"gather": {
                    "player": {"pos": [30, 10]},
                    "hold": ["ca_loc"] * (cap - 1),
                    "fish": [{"id": "F1", "kind": "ca_linh", "pos": [30.5, 10]}],
                }})
                code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "2",
                                         "--scenario", sc3, "--inputs", inp2, "--out", w.path("o3.jsonl"))
                self.assertEqual(code, 0, err)
                rows3 = read_jsonl(w.path("o3.jsonl"))
                self.assertLessEqual(snapshots(rows3)[-1]["hold_count"], cap)
                self.assertGreaterEqual(len(events(rows3, "hold_full")), 1)

    def test_dock_priority_over_harvest_and_writes_inventory_once(self):
        g = _tuning_gather()
        dock = g["dock_pos"]
        with Workdir() as w:
            # Đặt nút sẵn sàng ngay tại bến -> bấm interact phải ưu tiên cập bến (docked), không hái
            sc = write_json(w.path("sc.json"), {"gather": {
                "player": {"pos": list(dock)},
                "hold": ["ca_loc"],
                "nodes": [{"id": "N1", "kind": "bong_dien_dien", "pos": [dock[0] + 0.5, 0]}],
                "random_fish": False,
            }})
            inp = write_json(w.path("in.json"), frames({"tick": 0, "interact": True}))
            inv = w.path("inv.json")
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "10",
                                     "--scenario", sc, "--inputs", inp,
                                     "--inventory-out", inv, "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("o.jsonl"))
            self.assertEqual(events(rows, "gather"), [])
            end_evs = events(rows, "gather_end")
            self.assertEqual(len(end_evs), 1)
            self.assertEqual(end_evs[0]["data"]["reason"], "docked")
            with open(inv, encoding="utf-8") as f:
                saved = json.load(f)
            self.assertEqual(item_counts(saved["items"]), {"ca_loc": 1})

    def test_harvest_catch_dock_handoff_to_quan_and_deterministic_bytes(self):
        g = _tuning_gather()
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {"gather": {
                "player": {"pos": [6, 0]},
                "nodes": [{"id": "N1", "kind": "bong_dien_dien", "pos": [6, 0]}],
                "fish": [{"id": "F1", "kind": "ca_linh", "pos": [6, 2]}],
            }})
            # Hái N1 ở tick 0, lặn xuống d~2 (mất ~30-40 tick), bắt F1 ở tick 45, bơi về bến [2,0], cập bến ở tick 200
            inp = write_json(w.path("in.json"), frames(
                {"tick": 0, "interact": True, "move": [0, 1]},
                {"tick": 1, "interact": False},
                {"tick": 40, "move": [0, 0], "catch": True},
                {"tick": 41, "catch": False, "move": [-1, -0.5]},
                {"tick": 200, "move": [0, 0], "interact": True},
            ))
            inv1, inv2 = w.path("inv1.json"), w.path("inv2.json")
            out1, out2 = w.path("g1.jsonl"), w.path("g2.jsonl")
            for out, inv in ((out1, inv1), (out2, inv2)):
                code, err = run_headless("--mode", "gather", "--seed", "7", "--ticks", "250",
                                         "--scenario", sc, "--inputs", inp,
                                         "--inventory-out", inv, "--out", out)
                self.assertEqual(code, 0, err)
            # Tất định từng byte cả JSONL và file kho
            with open(out1, "rb") as a, open(out2, "rb") as b:
                self.assertEqual(a.read(), b.read())
            with open(inv1, "rb") as a, open(inv2, "rb") as b:
                self.assertEqual(a.read(), b.read())

            expected_items = {
                "bong_dien_dien": g["node_yield"],
                "ca_linh": g["fish_yield"]["ca_linh"],
            }
            with open(inv1, encoding="utf-8") as f:
                saved = json.load(f)
            self.assertEqual(item_counts(saved["items"]), expected_items)

            # Bàn giao sang chế độ quan: cùng các cá thể vừa ghi
            code, err = run_headless("--mode", "quan", "--seed", "7", "--ticks", "0",
                                     "--inventory", inv1, "--out", w.path("q.jsonl"))
            self.assertEqual(code, 0, err)
            self.assertEqual(item_counts(snapshots(read_jsonl(w.path("q.jsonl")))[0]["stock"]), expected_items)


class GatherSlice1And2IntegrationTests(unittest.TestCase):
    def test_tv1_hold_api_backward_compat_and_atomic_batch(self):
        tuning = load_contract()["tuning"]
        cap = tuning["gather"]["hold_capacity"]
        sim = GatherSim(tuning, {"hold": ["ca_loc"] * (cap - 2)}, Streams(1), IdAllocator())
        evs = []

        # Từ chối count <= 0, không sửa hold và không phát sự kiện
        self.assertFalse(sim._try_add_hold_batch("ca_linh", evs, 0,
                                                 action="catch", target_key="fish_id", target_id="F1"))
        self.assertFalse(sim._try_add_hold_batch("ca_linh", evs, -2,
                                                 action="catch", target_key="fish_id", target_id="F1"))
        self.assertEqual(len(sim.hold), cap - 2)
        self.assertEqual(evs, [])

        # Từ chối nguyên tử khi thiếu chỗ cho cả đàn (còn 2 chỗ, cần 3 cho ca_linh) -> đúng schema PRD-0
        self.assertFalse(sim._try_add_hold_batch("ca_linh", evs, 3,
                                                 action="catch", target_key="fish_id", target_id="F1"))
        self.assertEqual(len(sim.hold), cap - 2)
        self.assertEqual(evs, [("hold_full", {"action": "catch", "fish_id": "F1", "required": 3, "free": 2})])

        # Tương thích ngược API 2 tham số của TV1 (không sửa hàm TV1): try_add_hold(kind, events)
        evs.clear()
        self.assertTrue(sim.try_add_hold("bong_dien_dien", evs))
        self.assertTrue(sim.try_add_hold("bong_sung", evs))
        self.assertEqual(len(sim.hold), cap)
        self.assertEqual(sim.hold[-2:], ["bong_dien_dien", "bong_sung"])  # LIFO: mới nhất ở cuối
        self.assertEqual(evs, [])

        # Hái nút khi giỏ đầy (free = 0) qua _try_add_hold_batch -> đúng schema PRD-0 (không rơi vào {"kind": ...})
        self.assertFalse(sim._try_add_hold_batch("bong_sung", evs, 1,
                                                 action="gather", target_key="node_id", target_id="N1"))
        self.assertEqual(len(sim.hold), cap)
        self.assertEqual(evs, [("hold_full", {"action": "gather", "node_id": "N1", "required": 1, "free": 0})])

    def test_hold_full_contract_payload_and_atomic_fish_rejection(self):
        g = _tuning_gather()
        cap = g["hold_capacity"]
        with Workdir() as w:
            # Hái khi giỏ đầy -> hold_full có đúng payload PRD-0 {"action": "gather", "node_id", "required", "free"}
            sc_node = write_json(w.path("sc_node.json"), {"gather": {
                "player": {"pos": [20, 0]},
                "hold": ["ca_loc"] * cap,
                "nodes": [{"id": "N1", "kind": "bong_sung", "pos": [20.5, 0]}],
                "random_fish": False,
            }})
            inp_i = write_json(w.path("in_i.json"), frames({"tick": 0, "interact": True}))
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "2",
                                     "--scenario", sc_node, "--inputs", inp_i, "--out", w.path("o_node.jsonl"))
            self.assertEqual(code, 0, err)
            hf_node = events(read_jsonl(w.path("o_node.jsonl")), "hold_full")
            self.assertEqual(len(hf_node), 1)
            self.assertEqual(hf_node[0]["data"], {
                "action": "gather",
                "node_id": "N1",
                "required": g["node_yield"],
                "free": 0,
            })

            # Bắt ca_linh (yield 3) khi còn 2 ô -> từ chối toàn phần, đúng payload PRD-0, không bật cooldown
            sc_fish = write_json(w.path("sc_fish.json"), {"gather": {
                "player": {"pos": [30, 10]},
                "hold": ["ca_loc"] * (cap - 2),
                "fish": [{"id": "F1", "kind": "ca_linh", "pos": [30.5, 10]}],
            }})
            inp_c = write_json(w.path("in_c.json"), frames({"tick": 0, "catch": True}))
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "2",
                                     "--scenario", sc_fish, "--inputs", inp_c,
                                     "--snapshot-every", "1", "--out", w.path("o_fish.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("o_fish.jsonl"))
            self.assertEqual(events(rows, "fish_caught"), [])
            hf_fish = events(rows, "hold_full")
            self.assertEqual(len(hf_fish), 1)
            self.assertEqual(hf_fish[0]["data"], {
                "action": "catch",
                "fish_id": "F1",
                "required": g["fish_yield"]["ca_linh"],
                "free": 2,
            })
            snap1 = snapshots(rows)[1]
            self.assertEqual(snap1["hold_count"], cap - 2)
            self.assertEqual([f["id"] for f in snap1["fish"]], ["F1"])
            self.assertEqual(snap1["player"]["catch_cd_ticks"], 0)

            # Bắt ca_loc (yield 1) khi giỏ đầy (free = 0) -> đúng payload PRD-0 (không trả {"kind": ...})
            sc_fish_full = write_json(w.path("sc_fish_full.json"), {"gather": {
                "player": {"pos": [30, 10]},
                "hold": ["ca_loc"] * cap,
                "fish": [{"id": "F2", "kind": "ca_loc", "pos": [30.5, 10]}],
            }})
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "2",
                                     "--scenario", sc_fish_full, "--inputs", inp_c,
                                     "--out", w.path("o_fish_full.jsonl"))
            self.assertEqual(code, 0, err)
            hf_fish_full = events(read_jsonl(w.path("o_fish_full.jsonl")), "hold_full")
            self.assertEqual(len(hf_fish_full), 1)
            self.assertEqual(hf_fish_full[0]["data"], {
                "action": "catch",
                "fish_id": "F2",
                "required": g["fish_yield"]["ca_loc"],
                "free": 0,
            })

    def test_faint_after_gathering_clears_hold_writes_empty_inventory_and_is_deterministic(self):
        with Workdir() as w:
            # Hái rau trên mặt nước, lặn bắt cá, rồi hết oxy ngạt tới ngất -> mất toàn bộ giỏ, kho {}
            sc = write_json(w.path("sc.json"), {"gather": {
                "player": {"pos": [6, 0], "hp": 1, "oxygen_ticks": 15},
                "nodes": [{"id": "N1", "kind": "bong_dien_dien", "pos": [6, 0]}],
                # v1.1: cá khai trong scenario vẫn bơi. Tắt để cá đứng yên đúng chỗ bắt ở tick 25.
                "random_fish": False,
                "fish": [{"id": "F1", "kind": "ca_loc", "pos": [6, 1.5]}],
            }})
            inp = write_json(w.path("in.json"), frames(
                {"tick": 0, "interact": True, "move": [0, 1]},
                {"tick": 1, "interact": False},
                {"tick": 25, "move": [0, 0], "catch": True},
                {"tick": 26, "catch": False},
            ))
            inv1, inv2 = w.path("inv1.json"), w.path("inv2.json")
            out1, out2 = w.path("o1.jsonl"), w.path("o2.jsonl")
            for out, inv in ((out1, inv1), (out2, inv2)):
                code, err = run_headless("--mode", "gather", "--seed", "11", "--ticks", "220",
                                         "--scenario", sc, "--inputs", inp,
                                         "--inventory-out", inv, "--snapshot-every", "1", "--out", out)
                self.assertEqual(code, 0, err)

            with open(out1, "rb") as a, open(out2, "rb") as b:
                self.assertEqual(a.read(), b.read())
            with open(inv1, "rb") as a, open(inv2, "rb") as b:
                self.assertEqual(a.read(), b.read())

            rows = read_jsonl(out1)
            self.assertEqual(len(events(rows, "gather")), 1)
            self.assertEqual(len(events(rows, "fish_caught")), 1)
            self.assertEqual(len(events(rows, "choke")), 1)
            self.assertEqual(len(events(rows, "faint")), 1)
            end_evs = events(rows, "gather_end")
            self.assertEqual(len(end_evs), 1)
            self.assertEqual(end_evs[0]["data"], {"reason": "fainted", "inventory": {"items": []}})
            self.assertEqual(rows[-1]["reason"], "fainted")
            self.assertEqual(snapshots(rows)[-1]["hold"], [])
            with open(inv1, encoding="utf-8") as f:
                self.assertEqual(json.load(f), {"items": []})

            # Quán nạp kho rỗng sau khi ngất (mảng cá thể rỗng)
            code, err = run_headless("--mode", "quan", "--seed", "11", "--ticks", "0",
                                     "--inventory", inv1, "--out", w.path("q.jsonl"))
            self.assertEqual(code, 0, err)
            self.assertEqual(snapshots(read_jsonl(w.path("q.jsonl")))[0]["stock"], [])

    def test_same_tick_faint_blocks_dock_and_catch(self):
        g = _tuning_gather()
        dock = g["dock_pos"]
        with Workdir() as w:
            # Cùng tick vừa ngất vừa bấm interact trong vùng bến -> faint thắng, không docked, kho {}
            sc_dock = write_json(w.path("sc_dock.json"), {"gather": {
                "player": {"pos": [dock[0], 2.0], "hp": 1, "oxygen_ticks": 0, "zero_oxy_ticks": 59},
                "hold": ["ca_loc", "bong_sung"],
                "nodes": [{"id": "N1", "kind": "bong_dien_dien", "pos": [dock[0], 0]}],
                "random_fish": False,
            }})
            inp_dock = write_json(w.path("in_dock.json"), frames({"tick": 0, "interact": True}))
            inv_dock = w.path("inv_dock.json")
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "5",
                                     "--scenario", sc_dock, "--inputs", inp_dock,
                                     "--inventory-out", inv_dock, "--out", w.path("o_dock.jsonl"))
            self.assertEqual(code, 0, err)
            rows_dock = read_jsonl(w.path("o_dock.jsonl"))
            self.assertEqual([e["name"] for e in events(rows_dock)], ["choke", "faint", "gather_end"])
            self.assertEqual(events(rows_dock, "gather_end")[0]["data"], {"reason": "fainted", "inventory": {"items": []}})
            self.assertEqual(snapshots(rows_dock)[-1]["hold"], [])
            with open(inv_dock, encoding="utf-8") as f:
                self.assertEqual(json.load(f), {"items": []})

            # Cùng tick vừa ngất vừa bấm catch cạnh cá -> faint thắng, không fish_caught, cá còn nguyên
            sc_catch = write_json(w.path("sc_catch.json"), {"gather": {
                "player": {"pos": [30, 10], "hp": 1, "oxygen_ticks": 0, "zero_oxy_ticks": 59},
                "hold": ["bong_sung"],
                "fish": [{"id": "F1", "kind": "ca_loc", "pos": [30.5, 10]}],
            }})
            inp_catch = write_json(w.path("in_catch.json"), frames({"tick": 0, "catch": True}))
            inv_catch = w.path("inv_catch.json")
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "5",
                                     "--scenario", sc_catch, "--inputs", inp_catch,
                                     "--inventory-out", inv_catch, "--out", w.path("o_catch.jsonl"))
            self.assertEqual(code, 0, err)
            rows_catch = read_jsonl(w.path("o_catch.jsonl"))
            self.assertEqual([e["name"] for e in events(rows_catch)], ["choke", "faint", "gather_end"])
            self.assertEqual(events(rows_catch, "fish_caught"), [])
            last_snap = snapshots(rows_catch)[-1]
            self.assertEqual(last_snap["hold"], [])
            self.assertEqual([f["id"] for f in last_snap["fish"]], ["F1"])
            with open(inv_catch, encoding="utf-8") as f:
                self.assertEqual(json.load(f), {"items": []})

    def test_day_mode_gather_events_and_quan_handoff(self):
        """Kiểm tra tương thích luồng `--mode day` v1.1 với sự kiện PRD-0 v1.0 và bàn giao sang Quán."""
        fixture = os.path.join(ROOT, "tests", "fixtures", "contract-v1.1-day.json")
        if not os.path.exists(fixture):
            self.skipTest("không có contract fixture v1.1")
        env = dict(os.environ, CHONOI_CONTRACT=fixture)
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {
                "gather": {
                    "player": {"pos": [6, 0]},
                    "nodes": [{"id": "N1", "kind": "bong_sung", "pos": [6, 0]}],
                    "fish": [{"id": "F1", "kind": "ca_loc", "pos": [6, 2]}],
                },
                "quan": {"time_left_ticks": 1},
            })
            inp = write_json(w.path("in.json"), frames(
                {"tick": 0, "interact": True, "move": [0, 1]},
                {"tick": 1, "interact": False},
                {"tick": 40, "move": [0, 0], "catch": True},
                {"tick": 41, "catch": False, "move": [-1, -0.5]},
                {"tick": 200, "move": [0, 0], "interact": True},
            ))
            out = w.path("day.jsonl")
            p = subprocess.run([*headless_cmd(), "--mode", "day", "--seed", "7", "--ticks", "250",
                                "--scenario", sc, "--inputs", inp, "--out", out],
                               cwd=ROOT, capture_output=True, text=True, env=env)
            self.assertEqual(p.returncode, 0, p.stderr)
            rows = read_jsonl(out)
            g_evs = events(rows, "gather")
            self.assertEqual(len(g_evs), 1)
            self.assertEqual(g_evs[0]["data"], {"node_id": "N1", "kind": "bong_sung", "amount": 1})
            f_evs = events(rows, "fish_caught")
            self.assertEqual(len(f_evs), 1)
            self.assertEqual(f_evs[0]["data"], {"fish_id": "F1", "kind": "ca_loc", "yield": 1})
            ge = events(rows, "gather_end")[0]
            self.assertEqual(ge["data"], {"reason": "docked", "inventory": {"items": {"bong_sung": 1, "ca_loc": 1}}})
            quan_snap = [s for s in snapshots(rows) if s["tick"] == ge["tick"]][0]
            self.assertEqual(quan_snap["phase"], "quan")
            self.assertEqual(quan_snap["stock"], {"bong_sung": 1, "ca_loc": 1})


if __name__ == "__main__":
    unittest.main()
