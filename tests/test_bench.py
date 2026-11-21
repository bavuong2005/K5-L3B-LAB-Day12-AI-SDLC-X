"""Test bench_cmd (TICKET-04): đúng 5 trường, mã thoát, chế độ sim và browser (nếu có Chrome)."""

import json
import os
import subprocess
import sys
import unittest

from chonoi import bench
from helpers import ROOT, Workdir

FIELDS = {"avg_fps", "p1_low_fps", "frames", "measured_s", "load_ms"}


def _run(*args):
    return subprocess.run([sys.executable, "-m", "chonoi.bench", *args], cwd=ROOT,
                          capture_output=True, text=True)


class BenchTests(unittest.TestCase):
    def _check(self, mode, extra=()):
        with Workdir() as w:
            out = w.path("bench.json")
            p = _run("--seed", "42", "--duration", "1", "--out", out, "--mode", mode, *extra)
            self.assertEqual(p.returncode, 0, p.stderr)
            data = json.load(open(out, encoding="utf-8"))
        self.assertEqual(set(data), FIELDS)
        self.assertGreater(data["frames"], 0)
        self.assertGreater(data["avg_fps"], 0)
        self.assertGreater(data["measured_s"], 0)
        self.assertLessEqual(data["p1_low_fps"], data["avg_fps"] + 1e-6)
        return p.stderr

    def test_sim_mode_five_fields_and_honest_label(self):
        err = self._check("sim")
        self.assertIn("KHÔNG phải render", err)

    @unittest.skipUnless(bench.find_chrome(), "không có Chrome/Chromium")
    def test_browser_mode_five_fields(self):
        err = self._check("browser")
        self.assertIn("render thật", err)

    def test_bad_input_exit_2(self):
        with Workdir() as w:
            self.assertEqual(_run("--seed", "1", "--duration", "0", "--out", w.path("b.json")).returncode, 2)
            self.assertEqual(_run("--seed", "x", "--duration", "1", "--out", w.path("b.json")).returncode, 2)


if __name__ == "__main__":
    unittest.main()
