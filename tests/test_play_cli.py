"""Terminal mode (chonoi/play.py): renderers, line mode, và chạy curses thật trong pty.

Chạy: PYTHONPATH=tests:. python3 -m unittest tests.test_play_cli -v
Ghi capture màn hình pty: PYTHONPATH=tests:. python3 -m tests.test_play_cli docs/proof/phase-4/play-cli.txt
"""

import errno
import fcntl
import io
import os
import re
import select
import signal
import struct
import subprocess
import sys
import termios
import time
import unittest

from chonoi import play

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _game(**kw):
    return play.Game(kw.pop("mode", "day"), kw.pop("days", 1), kw.pop("seed", 1), **kw)


class Args:
    ascii = False
    demo = False
    ticks = None
    every = 300


def _quan_stock_scenario():
    import json, tempfile
    stock = [{"id": f"I{i}", "kind": k, "fresh": 100} for i, k in enumerate(["ca_loc"] * 3 + ["bong_sung"] * 6, 1)]
    f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump({"quan": {"stock": stock}}, f)
    f.close()
    return f.name


def _quan_game():
    path = _quan_stock_scenario()
    try:
        return _game(mode="quan", scenario_path=path)
    finally:
        os.unlink(path)


def _text(game, w=100, h=35, ascii_mode=False):
    return play.render(game, w, h, ascii_mode).to_text()


class RenderTest(unittest.TestCase):
    def test_intro_has_story_plan_and_player_name(self):
        t = _text(_game())
        self.assertIn("NGÀY 1/1", t)
        self.assertIn("Trường con", t)
        self.assertNotIn("Út Sen", t)
        self.assertIn("Cần mang về", t)

    def test_gather_frame_hud(self):
        g = _game()
        g.key("enter")
        g.advance(120)
        t = _text(g)
        for s in ("O2 [", "HP ", "Giỏ 0/12", "BÂY GIỜ LÀM", "@", "Cá Sấu", "bến"):
            self.assertIn(s, t)
        self.assertIn("30m", t)  # thước đo độ sâu

    def test_ascii_mode_has_no_box_chars(self):
        g = _game()
        g.key("enter")
        g.advance(10)
        t = _text(g, ascii_mode=True)
        self.assertNotIn("♥", t)
        self.assertNotIn("█", t)
        self.assertIn("HP vvv", t)

    def test_too_small_terminal(self):
        self.assertIn("quá nhỏ", _text(_game(), 60, 20))

    def test_quan_frame_and_hint_is_accurate(self):
        g = _quan_game()
        self.assertEqual(g.phase, "quan")
        g.key("enter")
        # chưa có khách
        self.assertIn("Chưa có khách", _text(g))
        first = g.tuning["quan"]["first_customer_tick"]
        g.advance(first + 1)
        snap = g.snap()
        self.assertTrue(snap["customers"])
        h = play.quan_hint(snap, g.tuning)
        self.assertIn("nấu", h["text"])
        self.assertIn("bếp", h["text"])
        t = _text(g)
        for s in ("[T1]", "[B1]", "[B2]", "ĐƠN KHÁCH", "Ghe Quán"):
            self.assertIn(s, t)

    def test_quan_hint_follows_real_serving_loop(self):
        """Bot chỉ theo gợi ý phải bán được món (tức gợi ý khớp luật thật)."""
        g = _quan_game()
        g.key("enter")
        for _ in range(3600):
            play.bot_tick(g)
        self.assertGreater(g.session.snapshot()["money"], 0)

    def test_shop_and_summary_screens(self):
        g = _game()
        for _ in range(60000):
            play.bot_tick(g)
            if g.stage == "summary":
                break
        self.assertEqual(g.stage, "summary")
        t = _text(g)
        self.assertIn("TỔNG KẾT", t)
        self.assertIn("ĐIỂM", t)
        g.key("r")
        self.assertEqual(g.stage, "intro")
        self.assertEqual(g.session.tick, 0)

    def test_result_and_shop_stage_sequence(self):
        g = _game()
        seen = []
        for _ in range(60000):
            play.bot_tick(g)
            if not seen or seen[-1] != (g.stage, g.phase):
                seen.append((g.stage, g.phase))
            if g.stage == "summary":
                break
        self.assertIn(("result", "shop"), seen)
        self.assertIn(("intro", "quan"), seen)
        self.assertIn(("play", "shop"), seen)

    def test_shop_buy_by_number(self):
        g = _game()
        g.key("enter")
        # ép đủ tiền bằng scenario day.money
        import json, tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump({"day": {"money": 1000, "earned": 1000}}, f)
        try:
            g2 = _game(scenario_path=f.name)
        finally:
            os.unlink(f.name)
        for _ in range(60000):
            play.bot_tick(g2) if g2.phase != "shop" or g2.stage != "play" else None
            if g2.phase == "shop" and g2.stage == "play":
                break
            if g2.stage == "result":
                g2.key("enter")
        self.assertEqual((g2.phase, g2.stage), ("shop", "play"))
        self.assertIn("[1]", _text(g2))
        g2.key("1")
        g2.tick(move=(0.0, 0.0))
        self.assertEqual(sum(g2.session.snapshot()["upgrades"].values()), 1)

    def test_r_ignored_unless_finished_and_quit_confirm(self):
        g = _game()
        g.key("enter")
        g.advance(5)
        g.key("r")
        self.assertEqual(g.session.tick, 5)
        g.key("q")
        self.assertTrue(g.confirm_quit)
        self.assertIn("Thoát game", _text(g))
        g.key("n")
        self.assertFalse(g.want_quit)
        g.key("q")
        g.key("y")
        self.assertTrue(g.want_quit)

    def test_pause_and_help(self):
        g = _game()
        g.key("enter")
        g.advance(3)
        g.key("p")
        self.assertTrue(g.paused)
        self.assertIn("TẠM DỪNG", _text(g))
        t0 = g.snap()["sim_tick"]
        g.advance(30)
        self.assertEqual(g.session.snapshot()["sim_tick"], t0)
        g.key("esc")
        g.advance(3)
        self.assertFalse(g.paused)
        g.key("h")
        self.assertIn("TRỢ GIÚP", _text(g))

    def test_move_keys_expire(self):
        g = _game()
        g.key("enter")
        g.key("d", now=100.0)
        g.tick(now=100.1)
        g.advance(1, now=100.1)
        self.assertGreater(g.session.snapshot()["player"]["vel"][0], 0)
        g.tick(now=101.0)
        self.assertEqual(g._release_moves(101.0), (0.0, 0.0))

    def test_unknown_snapshot_fields_ignored(self):
        g = _game()
        g.key("enter")
        snap = dict(g.snap(), brand_new_field={"x": 1})
        g.last_snap = snap
        play.render(g, 100, 35)  # không ném lỗi

    def test_story_parse_and_fallback(self):
        st = play.load_story()
        self.assertTrue(st["intro"])
        self.assertTrue(any("Trường con" in l for l in st["intro"]) or os.path.exists(play.STORY_PATH) is False)
        self.assertTrue(play.load_story("/nonexistent/story.js")["intro"])


class LineModeTest(unittest.TestCase):
    def run_lines(self, lines, *flags):
        r = subprocess.run([sys.executable, "-m", "chonoi.play", "--mode", "day", "--text", *flags],
                           input=lines, capture_output=True, text=True, encoding="utf-8", cwd=ROOT, timeout=60)
        return r

    def test_commands_and_frames(self):
        r = self.run_lines("enter\nd 60\nwait 30\ns 60\ne\nspace\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.count("\n=== "), 6)
        self.assertIn("Lặn xuống", r.stdout)
        self.assertIn("--- kết thúc: tick=", r.stdout)

    def test_ticks_budget(self):
        r = self.run_lines("enter\nwait 500\nwait 500\n", "--ticks", "100")
        self.assertEqual(r.returncode, 0)
        self.assertIn("tick=100 ", r.stdout)

    def test_demo_text_plays_whole_day(self):
        r = subprocess.run([sys.executable, "-m", "chonoi.play", "--mode", "day", "--text", "--demo", "--ticks", "40000",
                            "--every", "100000"], capture_output=True, text=True, encoding="utf-8", cwd=ROOT,
                           stdin=subprocess.DEVNULL, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("TỔNG KẾT", r.stdout)

    def test_bad_args_exit_2(self):
        for argv in (["--days", "9"], ["--mode", "quan", "--days", "2"], ["--scenario", "/no/such.json"]):
            r = subprocess.run([sys.executable, "-m", "chonoi.play", "--text", *argv], capture_output=True, text=True,
                               cwd=ROOT, stdin=subprocess.DEVNULL, timeout=30)
            self.assertEqual(r.returncode, 2, argv)

    def test_non_tty_falls_back_to_text(self):
        r = subprocess.run([sys.executable, "-m", "chonoi.play", "--mode", "day"], capture_output=True, text=True,
                           encoding="utf-8", cwd=ROOT, input="q\n", timeout=30)
        self.assertEqual(r.returncode, 0)
        self.assertIn("=== khung đầu", r.stdout)

    def test_does_not_touch_headless_jsonl(self):
        import hashlib, tempfile
        outs = []
        for _ in range(2):
            with tempfile.TemporaryDirectory() as d:
                p = os.path.join(d, "o.jsonl")
                subprocess.run([sys.executable, "-m", "chonoi.headless", "--mode", "day", "--seed", "1", "--ticks", "300",
                                "--out", p], cwd=ROOT, check=True)
                with open(p, "rb") as fh:
                    outs.append(hashlib.sha1(fh.read()).hexdigest())
        self.assertEqual(outs[0], outs[1])


# ---------------------------------------------------------------------------- pty + mini terminal emulator
class Screen:
    """Emulator tối thiểu cho đầu ra curses (CUP, EL, ED, ECH, REP, CUU/CUD/CUF/CUB, CHA/VPA, SGR bỏ qua)."""

    def __init__(self, w, h):
        self.w, self.h = w, h
        self.g = [[" "] * w for _ in range(h)]
        self.x = self.y = 0
        self.buf = ""

    def feed(self, data):
        self.buf += data
        s, i = self.buf, 0
        while i < len(s):
            c = s[i]
            if c == "\x1b":
                m = re.match(r"\x1b\[([?0-9;]*)([@-~])", s[i:])
                if m:
                    self.csi(m.group(1), m.group(2))
                    i += m.end()
                    continue
                m = re.match(r"\x1b[()][0-9A-Za-z]|\x1b[=>78MDEHc]|\x1b\][^\x07]*\x07", s[i:])
                if m:
                    i += m.end()
                    continue
                break  # chưa đủ byte
            if c == "\r":
                self.x = 0
            elif c == "\n":
                self.y = min(self.h - 1, self.y + 1)
            elif c == "\b":
                self.x = max(0, self.x - 1)
            elif c == "\t":
                self.x = min(self.w - 1, (self.x // 8 + 1) * 8)
            elif c >= " ":
                self.put(c)
            i += 1
        self.buf = s[i:]

    def put(self, c):
        if self.x >= self.w:
            self.x = 0
            self.y = min(self.h - 1, self.y + 1)
        self.g[self.y][self.x] = c
        self.last = c
        self.x += 1

    def csi(self, p, f):
        nums = [int(n) if n.isdigit() else 0 for n in p.lstrip("?").split(";")] if p else []
        n1 = nums[0] if nums and nums[0] else 1
        if p.startswith("?"):
            return
        if f in "Hf":
            self.y = min(self.h - 1, (nums[0] or 1) - 1) if nums else 0
            self.x = min(self.w - 1, ((nums[1] if len(nums) > 1 else 1) or 1) - 1)
        elif f == "A":
            self.y = max(0, self.y - n1)
        elif f == "B":
            self.y = min(self.h - 1, self.y + n1)
        elif f == "C":
            self.x = min(self.w - 1, self.x + n1)
        elif f == "D":
            self.x = max(0, self.x - n1)
        elif f == "G":
            self.x = min(self.w - 1, n1 - 1)
        elif f == "d":
            self.y = min(self.h - 1, n1 - 1)
        elif f == "K":
            mode = nums[0] if nums else 0
            a, b = {0: (self.x, self.w), 1: (0, self.x + 1), 2: (0, self.w)}[mode]
            for k in range(a, b):
                self.g[self.y][k] = " "
        elif f == "J":
            mode = nums[0] if nums else 0
            if mode in (2, 3):
                self.g = [[" "] * self.w for _ in range(self.h)]
            elif mode == 0:
                for k in range(self.x, self.w):
                    self.g[self.y][k] = " "
                for yy in range(self.y + 1, self.h):
                    self.g[yy] = [" "] * self.w
        elif f == "X":
            for k in range(self.x, min(self.w, self.x + n1)):
                self.g[self.y][k] = " "
        elif f == "b":
            for _ in range(n1):
                self.put(getattr(self, "last", " "))
        elif f == "P":
            row = self.g[self.y]
            del row[self.x:self.x + n1]
            row.extend([" "] * (self.w - len(row)))
        elif f == "@":
            row = self.g[self.y]
            row[self.x:self.x] = [" "] * n1
            del row[self.w:]

    def text(self):
        return "\n".join("".join(r).rstrip() for r in self.g)


class PtyRun:
    def __init__(self, argv, w=100, h=35, term="xterm-256color"):
        self.screen = Screen(w, h)
        env = dict(os.environ, TERM=term, LANG="en_US.UTF-8", LC_ALL="en_US.UTF-8", PYTHONPATH=ROOT)
        pid, fd = _forkpty()
        if pid == 0:
            os.chdir(ROOT)
            os.execvpe(sys.executable, [sys.executable, "-m", "chonoi.play", *argv], env)
        self.pid, self.fd = pid, fd
        fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", h, w, 0, 0))
        self.status = None
        self.raw = b""

    def pump(self, secs):
        end = time.time() + secs
        while time.time() < end:
            r, _, _ = select.select([self.fd], [], [], 0.05)
            if r:
                try:
                    d = os.read(self.fd, 65536)
                except OSError:
                    break
                if not d:
                    break
                self.raw += d
                self.screen.feed(d.decode("utf-8", "replace"))
        return self.screen.text()

    def send(self, data):
        os.write(self.fd, data.encode() if isinstance(data, str) else data)

    def wait_for(self, text, timeout=8.0):
        end = time.time() + timeout
        while time.time() < end:
            if text in self.pump(0.15):
                return True
        return False

    def finish(self, timeout=8.0):
        end = time.time() + timeout
        while time.time() < end:
            self.pump(0.1)
            pid, st = os.waitpid(self.pid, os.WNOHANG)
            if pid:
                self.status = os.waitstatus_to_exitcode(st)
                return self.status
        os.kill(self.pid, signal.SIGKILL)
        os.waitpid(self.pid, 0)
        return None


def _forkpty():
    import pty
    return pty.fork()


class PtyTest(unittest.TestCase):
    def test_play_session_in_pty(self):
        run = PtyRun(["--mode", "day", "--seed", "1"])
        self.assertTrue(run.wait_for("NGÀY 1/1"), run.screen.text())
        run.send("\r")
        self.assertTrue(run.wait_for("O2 ["), run.screen.text())
        run.send("s")
        run.pump(0.6)
        run.send("h")
        self.assertTrue(run.wait_for("TRỢ GIÚP"))
        run.send(" ")
        run.send("p")
        self.assertTrue(run.wait_for("TẠM DỪNG"))
        run.send("p")
        run.pump(0.3)
        run.send("q")
        self.assertTrue(run.wait_for("Thoát game"))
        run.send("y")
        self.assertEqual(run.finish(), 0)

    def test_demo_in_pty_exits_zero(self):
        run = PtyRun(["--mode", "day", "--demo", "--demo-seconds", "3"])
        self.assertTrue(run.wait_for("Giỏ"), run.screen.text())
        self.assertEqual(run.finish(timeout=15), 0)


def record(path):
    """Ghi capture pty (các màn chính) vào `path`."""
    parts = []

    def snap(run, title):
        parts.append(f"##### {title}\n{run.screen.text()}\n")
    run = PtyRun(["--mode", "day", "--seed", "1"])
    run.wait_for("NGÀY 1/1")
    run.pump(0.3)
    snap(run, "Màn mở đầu Ngày 1 (TERM=xterm-256color, 100x35)")
    run.send("\r")
    run.wait_for("O2 [")
    run.send("s")
    run.pump(1.2)
    snap(run, "Buổi sáng: đang lặn (đã nhấn S)")
    run.send("h")
    run.wait_for("TRỢ GIÚP")
    run.pump(0.3)
    snap(run, "Trợ giúp (H)")
    run.send(" ")
    run.send("p")
    run.wait_for("TẠM DỪNG")
    run.pump(0.3)
    snap(run, "Tạm dừng (P)")
    run.send("p")
    run.pump(0.2)
    run.send("q")
    run.wait_for("Thoát game")
    run.pump(0.3)
    snap(run, "Xác nhận thoát (Q)")
    run.send("y")
    code = run.finish()
    parts.append(f"##### Thoát bằng Q -> Y: exit code = {code}\n")
    demo = PtyRun(["--mode", "day", "--demo", "--demo-seconds", "14", "--speed", "30"])
    demo.wait_for("Giỏ")
    for label, key in (("Demo bot: buổi sáng", "Giỏ"), ("Demo bot: buổi tối (quán)", "ĐƠN KHÁCH")):
        if demo.wait_for(key, 20):
            demo.pump(0.5)
            snap(demo, label)
    dc = demo.finish(timeout=25)
    parts.append(f"##### --demo thoát: exit code = {dc}\n")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))
    return code, dc


if __name__ == "__main__":
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        print(record(sys.argv[1]))
    else:
        unittest.main()
