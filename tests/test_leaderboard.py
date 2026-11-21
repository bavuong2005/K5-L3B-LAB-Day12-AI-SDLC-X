"""Mở rộng `leaderboard` (T460/T462): top 10 cục bộ, ghi 1 mục/lượt 5 Ngày chuẩn, xuất JSON, cờ sai -> mã 2."""

import json
import os
import subprocess
import unittest

from chonoi import leaderboard
from chonoi.errors import BadInput

from helpers import ROOT, Workdir, headless_cmd, read_jsonl, write_json


def head(*args):
    p = subprocess.run([*headless_cmd(), *args], cwd=ROOT, capture_output=True, text=True)
    return p.returncode, p.stderr


def entries(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)["entries"]


class StoreUnit(unittest.TestCase):
    def test_sort_desc_ties_keep_insertion_order_after_reopen(self):
        with Workdir() as w:
            s = w.path("s.json")
            for name, score in (("a", 100), ("b", 300), ("c", 100), ("d", 300)):
                leaderboard.add(s, name, score, 5, 1)
            self.assertEqual([e["name"] for e in entries(s)], ["b", "d", "a", "c"])
            leaderboard.add(s, "e", 100, 5, 1)  # mở lại: mục hòa mới đứng sau mục cũ
            self.assertEqual([e["name"] for e in entries(s)], ["b", "d", "a", "c", "e"])

    def test_top_10_only_and_unicode_name(self):
        with Workdir() as w:
            s = w.path("s.json")
            for i in range(12):
                leaderboard.add(s, f"Út Sen {i}", i, 5, i)
            e = entries(s)
            self.assertEqual(len(e), 10)
            self.assertEqual([x["score"] for x in e], list(range(11, 1, -1)))
            self.assertEqual(set(e[0]), {"name", "score", "days_completed", "seed"})
            self.assertEqual(e[0]["name"], "Út Sen 11")

    def test_empty_name_and_bad_store_rejected(self):
        with Workdir() as w:
            with self.assertRaises(BadInput):
                leaderboard.add(w.path("s.json"), "  ", 1, 5, 1)
            write_json(w.path("bad.json"), {"entries": "x"})
            with self.assertRaises(BadInput):
                leaderboard.load(w.path("bad.json"))

    def test_export_sorted_four_fields(self):
        with Workdir() as w:
            s = w.path("s.json")
            leaderboard.add(s, "a", 1, 5, 1)
            leaderboard.add(s, "b", 9, 5, 2)
            leaderboard.export(s, w.path("o.json"))
            self.assertEqual(entries(w.path("o.json")),
                             [{"name": "b", "score": 9, "days_completed": 5, "seed": 2},
                              {"name": "a", "score": 1, "days_completed": 5, "seed": 1}])


class HeadlessFlags(unittest.TestCase):
    def test_five_days_writes_exactly_one_entry(self):
        with Workdir() as w:
            args = ("--mode", "day", "--days", "5", "--seed", "3", "--ticks", "200000",
                    "--out", w.path("o.jsonl"), "--leaderboard", w.path("lb.json"), "--player-name", "Út Sen")
            self.assertEqual(head(*args)[0], 0)
            end = read_jsonl(w.path("o.jsonl"))[-1]
            self.assertEqual(end["reason"], "days_complete")
            e = entries(w.path("lb.json"))
            self.assertEqual(e, [{"name": "Út Sen", "score": end["score"], "days_completed": 5, "seed": 3}])

    def test_incomplete_run_or_other_days_writes_nothing(self):
        with Workdir() as w:
            base = ("--mode", "day", "--seed", "3", "--out", w.path("o.jsonl"),
                    "--leaderboard", w.path("lb.json"), "--player-name", "A")
            self.assertEqual(head(*base, "--days", "5", "--ticks", "100")[0], 0)  # tick_limit
            self.assertEqual(head(*base, "--days", "1", "--ticks", "50000")[0], 0)  # không đủ 5 Ngày
            self.assertFalse(os.path.exists(w.path("lb.json")))

    def test_flag_errors_exit_2(self):
        with Workdir() as w:
            o = w.path("o.jsonl")
            for extra in (("--mode", "day", "--leaderboard", w.path("l.json")),
                          ("--mode", "day", "--player-name", "A"),
                          ("--mode", "gather", "--leaderboard", w.path("l.json"), "--player-name", "A"),
                          ("--mode", "day", "--leaderboard", w.path("l.json"), "--player-name", " ")):
                self.assertEqual(head("--seed", "1", "--ticks", "5", "--out", o, *extra)[0], 2, extra)
            self.assertFalse(os.path.exists(o))

    def test_export_command_and_default_unchanged_without_flags(self):
        with Workdir() as w:
            leaderboard.add(w.path("s.json"), "a", 5, 5, 1)
            for mod in ("chonoi.headless", "chonoi.live"):
                out = w.path(mod + ".json")
                p = subprocess.run(["python3", "-m", mod, "--export-leaderboard", out,
                                    "--leaderboard", w.path("s.json")], cwd=ROOT, capture_output=True, text=True)
                self.assertEqual(p.returncode, 0, p.stderr)
                self.assertEqual(entries(out)[0]["name"], "a")
            self.assertEqual(head("--mode", "day", "--seed", "1", "--ticks", "10", "--out", w.path("n.jsonl"))[0], 0)
            self.assertFalse(os.path.exists(os.path.join(ROOT, "leaderboard.json")))


if __name__ == "__main__":
    unittest.main()
