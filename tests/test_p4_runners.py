"""TV5 — Phase 4 (TICKET-04, contract v1.3): kiểm `bench_cmd` và `soak_cmd` ở biên CLI.

Gọi đúng lệnh khai trong game.contract.json (như runner của lớp), kiểm cấu trúc JSON,
công thức avg/1% low, mã 2 khi đối số sai, và soak tất định ở trường gameplay.
Chạy: PYTHONPATH=tests:. python3 -m unittest tests.test_p4_runners -v
"""

import json
import math
import os
import shlex
import subprocess
import unittest

from chonoi.bench import measure

from helpers import ROOT, Workdir

BENCH_KEYS = {"avg_fps", "p1_low_fps", "frames", "measured_s", "load_ms"}
SOAK_KEYS = {"days", "days_completed", "crashes", "results", "duration_s"}


def contract():
    with open(os.path.join(ROOT, "game.contract.json"), encoding="utf-8") as f:
        return json.load(f)


def run_cmd(key, *args):
    p = subprocess.run([*shlex.split(contract()[key]), *args], cwd=ROOT, capture_output=True, text=True)
    return p.returncode, p.stderr


class ContractV13(unittest.TestCase):
    def test_contract_1_3_khai_bench_va_soak(self):
        c = contract()
        self.assertEqual(c["contract_version"], "1.3")
        self.assertTrue(c["bench_cmd"].strip())
        self.assertTrue(c["soak_cmd"].strip())


class Bench(unittest.TestCase):
    def test_measure_du_5_truong_va_dung_cong_thuc(self):
        r = measure(42, 0.3, warmup_s=0)
        self.assertEqual(set(r), BENCH_KEYS)
        self.assertGreater(r["frames"], 0)
        self.assertAlmostEqual(r["avg_fps"], r["frames"] / r["measured_s"], places=6)
        self.assertLessEqual(r["p1_low_fps"], r["avg_fps"] + 1e-9)  # 1% chậm nhất không nhanh hơn TB
        self.assertGreaterEqual(r["load_ms"], 0)
        self.assertLessEqual(r["measured_s"], 0.3 + 0.1)

    def test_cli_ghi_bench_json(self):
        with Workdir() as w:
            out = w.path("bench.json")
            code, err = run_cmd("bench_cmd", "--seed", "42", "--duration", "0.2", "--out", out)
            self.assertEqual(code, 0, err)
            with open(out, encoding="utf-8") as f:
                self.assertEqual(set(json.load(f)), BENCH_KEYS)

    def test_cli_doi_so_sai_ma_2(self):
        with Workdir() as w:
            for args in (["--seed", "42", "--duration", "0", "--out", w.path("a.json")],
                         ["--seed", "x", "--duration", "1", "--out", w.path("b.json")],
                         ["--seed", "42", "--out", w.path("c.json")]):
                with self.subTest(args):
                    self.assertEqual(run_cmd("bench_cmd", *args)[0], 2)


class Soak(unittest.TestCase):
    def _soak(self, w, name, days="1", seed="7"):
        out = w.path(name)
        code, err = run_cmd("soak_cmd", "--seed", seed, "--days", days, "--out", out)
        self.assertEqual(code, 0, err)
        with open(out, encoding="utf-8") as f:
            return json.load(f)

    def test_soak_1_ngay_cau_truc_va_dat(self):
        with Workdir() as w:
            r = self._soak(w, "soak.json")
        self.assertEqual(set(r), SOAK_KEYS)
        self.assertEqual((r["days"], r["days_completed"], r["crashes"]), (1, 1, 0))
        self.assertEqual([x["day"] for x in r["results"]], [1])
        mult = contract()["tuning"]["score"]["reputation_multiplier"]
        for x in r["results"]:
            self.assertEqual(set(x), {"day", "earned", "reputation", "score"})
            self.assertEqual(x["score"], x["earned"] + mult * math.floor(x["reputation"]))

    def test_soak_tat_dinh_bo_duration(self):
        with Workdir() as w:
            a = self._soak(w, "a.json", days="2")
            b = self._soak(w, "b.json", days="2")
        a.pop("duration_s")
        b.pop("duration_s")
        self.assertEqual(a, b)
        self.assertEqual(a["days_completed"], 2)

    def test_soak_doi_so_sai_ma_2(self):
        with Workdir() as w:
            for days in ("0", "-1", "abc"):
                with self.subTest(days):
                    self.assertEqual(run_cmd("soak_cmd", "--seed", "7", "--days", days,
                                             "--out", w.path("s.json"))[0], 2)


if __name__ == "__main__":
    unittest.main()
