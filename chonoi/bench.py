"""Benchmark có render (TICKET-04). Út Sen đứng yên ở bến, cảnh gather 1280×720.

python3 -m chonoi.bench --seed 42 --duration 30 --out bench.json [--mode auto|browser|sim]

Hai chế độ (nhãn in ra stderr, JSON luôn đúng 5 trường):
  browser  ĐO THẬT: mở máy chủ `chonoi.live` (cảnh gather: độ tươi, cá, Cá Sấu Năm Chèo,
           Út Sen đứng yên ở bến [2,0]) rồi lái ứng dụng web thật (`chonoi/web/index.html`,
           PixiJS + canvas 2D) trong Chrome/Chromium headless 1280×720 (DPR 1) qua Chrome
           DevTools Protocol, đo thời gian giữa các lần `requestAnimationFrame`. Làm nóng
           3 s rồi đo `--duration` giây. Tắt giới hạn vsync/khung hình để thấy chi phí vẽ
           thật; số FPS phụ thuộc phần cứng/GPU của máy chạy (headless có thể dùng
           render phần mềm). Không đo thời gian GPU hiển thị lên màn hình thật.
  sim      KHÔNG PHẢI render: chỉ bước mô phỏng `GatherSim` + tô một bộ đệm byte trên CPU.
           FPS cao hơn thực tế nhiều bậc; dùng làm dự phòng khi máy không có Chrome.
  auto     (mặc định) browser nếu tìm thấy Chrome/Chromium (hoặc $CHROME_BIN), không thì sim.
Mốc avg ≥ 60, 1% low ≥ 30, load ≤ 10 s chỉ để báo cáo. `load_ms` ở chế độ browser = từ lúc
bắt đầu dựng máy chủ + mở trình duyệt đến khung hình gather đầu tiên có dữ liệu.
"""

import argparse
import base64
import json
import math
import os
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.request

from .contract import DEFAULT_PATH, load_contract
from .errors import BadInput
from .ids import IdAllocator
from .inputs import InputState
from .rng import Streams
from .sim.gather import GatherSim

WIDTH, HEIGHT = 1280, 720
WARMUP_S = 3.0
_IDLE = InputState((0.0, 0.0), frozenset(), frozenset())


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        sys.stderr.write(f"lỗi: {message}\n")
        sys.exit(2)


def _plot(buf, x, d, bounds, value):
    x0, x1 = bounds["x"]
    d0, d1 = bounds["d"]
    px = int((float(x) - x0) / (x1 - x0) * (WIDTH - 1))
    py = int((float(d) - d0) / (d1 - d0) * (HEIGHT - 1))
    for dy in range(-1, 2):
        yy = py + dy
        if yy < 0 or yy >= HEIGHT:
            continue
        row = yy * WIDTH
        for dx in range(-1, 2):
            xx = px + dx
            if 0 <= xx < WIDTH:
                buf[row + xx] = value


def _draw(buf, blank, sim):
    buf[:] = blank
    bounds = sim.t["bounds"]
    fresh = sim.tuning_fresh if sim.tuning_fresh else None
    if fresh:
        span = int(WIDTH * float(fresh["initial"]) / 100)
        buf[:span] = b"\x40" * span
    _plot(buf, sim.pos[0], sim.pos[1], bounds, 255)
    for fish in sim.fish:
        _plot(buf, fish["pos"][0], fish["pos"][1], bounds, 180)
    for monster in sim.monsters:
        _plot(buf, monster["pos"][0], monster["pos"][1], bounds, 220)


def measure_sim(seed, duration_s, warmup_s=WARMUP_S, contract_path=None) -> dict:
    started = time.perf_counter()
    contract = load_contract(contract_path or DEFAULT_PATH)
    tuning = contract["tuning"]
    sim = GatherSim(tuning, {}, Streams(seed), IdAllocator(),
                    contract_version=contract.get("contract_version"))
    sim.tuning_fresh = tuning.get("freshness")
    blank = bytes(WIDTH * HEIGHT)
    buf = bytearray(blank)
    _draw(buf, blank, sim)
    load_ms = int(round((time.perf_counter() - started) * 1000))

    def frames_for(seconds):
        times = []
        end = time.perf_counter() + seconds
        while time.perf_counter() < end:
            t0 = time.perf_counter()
            sim.step(_IDLE)
            _draw(buf, blank, sim)
            times.append(time.perf_counter() - t0)
        return times

    if warmup_s > 0:
        frames_for(warmup_s)
    samples = frames_for(duration_s)
    return _report(samples, load_ms)


def _report(samples, load_ms) -> dict:
    frames = len(samples)
    measured_s = sum(samples)
    if frames == 0 or measured_s <= 0:
        raise BadInput("không đo được khung hình")
    slow_n = max(1, math.ceil(0.01 * frames))
    slowest = sorted(samples, reverse=True)[:slow_n]
    return {
        "avg_fps": frames / measured_s,
        "p1_low_fps": slow_n / sum(slowest),
        "frames": frames,
        "measured_s": measured_s,
        "load_ms": load_ms,
    }


# ---------------------------------------------------------------- chế độ browser
BENCH_SCENARIO = {"gather": {
    "player": {"pos": [2, 0], "vel": [0, 0], "heading_deg": 0},
    "hold": ["ca_loc", "bong_dien_dien", "ca_linh"],
    "nodes": [
        {"id": "N1", "kind": "bong_dien_dien", "pos": [12, 0]},
        {"id": "N2", "kind": "bong_dien_dien", "pos": [28, 0]},
        {"id": "N3", "kind": "bong_sung", "pos": [44, 0]},
        {"id": "N4", "kind": "bong_sung", "pos": [60, 0]},
    ],
    "fish": [
        {"id": "F1", "kind": "ca_linh", "pos": [15, 5], "heading_deg": 0},
        {"id": "F2", "kind": "ca_loc", "pos": [30, 10], "heading_deg": 0},
        {"id": "F3", "kind": "ca_linh", "pos": [45, 10], "heading_deg": 0},
        {"id": "F4", "kind": "ca_loc", "pos": [60, 16], "heading_deg": 0},
        {"id": "F5", "kind": "ca_linh", "pos": [75, 5], "heading_deg": 0},
        {"id": "F6", "kind": "ca_loc", "pos": [90, 16], "heading_deg": 0},
    ],
    "monsters": [{
        "id": "M1", "kind": "ca_sau", "pos": [60, 24], "waypoints": [[60, 24], [64, 24]],
        "target_idx": 1, "state": "patrol", "state_ticks_left": 0, "recoil_dir": None,
    }],
}}

CHROME_CANDIDATES = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
)
CHROME_NAMES = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome", "microsoft-edge")

# Ghi mốc thời gian mỗi lần requestAnimationFrame (cùng vòng lặp vẽ của trang chạy song song).
_PROBE_JS = (
    "window.__ts=[];(function f(t){window.__ts.push(t);requestAnimationFrame(f)})(performance.now());true"
)


def find_chrome():
    env = os.environ.get("CHROME_BIN")
    if env and os.path.exists(env):
        return env
    for name in CHROME_NAMES:
        found = shutil.which(name)
        if found:
            return found
    for path in CHROME_CANDIDATES:
        if os.path.exists(path):
            return path
    return None


class _WS:
    """WebSocket client tối thiểu (stdlib) cho Chrome DevTools Protocol."""

    def __init__(self, url):
        rest = url[len("ws://"):]
        hostport, _, path = rest.partition("/")
        host, _, port = hostport.partition(":")
        self.sock = socket.create_connection((host, int(port)), timeout=60)
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall((f"GET /{path} HTTP/1.1\r\nHost: {hostport}\r\nUpgrade: websocket\r\n"
                           f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
                           "Sec-WebSocket-Version: 13\r\n\r\n").encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise OSError("handshake DevTools thất bại")
            buf += chunk
        if b" 101 " not in buf.split(b"\r\n")[0]:
            raise OSError("handshake DevTools bị từ chối")
        self._rest = buf.split(b"\r\n\r\n", 1)[1]
        self._id = 0

    def _read(self, n):
        while len(self._rest) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise OSError("DevTools đóng kết nối")
            self._rest += chunk
        out, self._rest = self._rest[:n], self._rest[n:]
        return out

    def _send(self, text):
        data = text.encode()
        n = len(data)
        head = b"\x81" + (bytes([0x80 | n]) if n < 126 else b"\xfe" + struct.pack(">H", n)
                          if n < 65536 else b"\xff" + struct.pack(">Q", n))
        mask = os.urandom(4)
        self.sock.sendall(head + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def _recv(self):
        msg = b""
        while True:
            b0, b1 = self._read(2)
            n = b1 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._read(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._read(8))[0]
            payload = self._read(n)
            op = b0 & 0x0F
            if op == 8:
                raise OSError("DevTools đóng kết nối")
            if op in (9, 10):
                continue
            msg += payload
            if b0 & 0x80:
                return msg.decode()

    def call(self, method, **params):
        self._id += 1
        self._send(json.dumps({"id": self._id, "method": method, "params": params}))
        while True:
            m = json.loads(self._recv())
            if m.get("id") == self._id:
                if "error" in m:
                    raise OSError(f"{method}: {m['error']}")
                return m.get("result", {})

    def eval(self, expr):
        r = self.call("Runtime.evaluate", expression=expr, returnByValue=True)
        if "exceptionDetails" in r:
            raise OSError(f"JS lỗi: {r['exceptionDetails'].get('text')}")
        return r["result"].get("value")

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


def _browser_samples(chrome, url, duration_s, warmup_s, t_start):
    prof = tempfile.mkdtemp(prefix="chonoi-bench-")
    proc = subprocess.Popen(
        [chrome, "--headless=new", "--remote-debugging-port=0", f"--user-data-dir={prof}",
         f"--window-size={WIDTH},{HEIGHT}", "--no-first-run", "--no-default-browser-check",
         "--disable-gpu-vsync", "--disable-frame-rate-limit", "--mute-audio",
         "--autoplay-policy=no-user-gesture-required", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ws = None
    try:
        port_file = os.path.join(prof, "DevToolsActivePort")
        deadline = time.time() + 30
        while not os.path.exists(port_file):
            if proc.poll() is not None or time.time() > deadline:
                raise OSError("Chrome headless không khởi động được")
            time.sleep(0.1)
        time.sleep(0.2)
        port = open(port_file).read().split()[0]
        req = urllib.request.Request(f"http://127.0.0.1:{port}/json/new?about:blank", method="PUT")
        target = json.load(urllib.request.urlopen(req, timeout=10))
        ws = _WS(target["webSocketDebuggerUrl"])
        ws.call("Page.enable")
        ws.call("Emulation.setDeviceMetricsOverride", width=WIDTH, height=HEIGHT,
                deviceScaleFactor=1, mobile=False)
        ws.call("Page.navigate", url=url)
        deadline = time.time() + 30
        while ws.eval("document.readyState") != "complete":
            if time.time() > deadline:
                raise OSError("trang không tải xong")
            time.sleep(0.05)
        ws.eval("startFromMenu()")  # bấm "Chơi" của menu thật
        ws.eval(_PROBE_JS)
        deadline = time.time() + 30
        # đến khi trang vào màn chơi và đã có snapshot gather (khung vẽ cảnh đầu tiên)
        while not ws.eval("uiScreen==='play' && !!snap && snap.mode==='gather' && window.__ts.length>2"):
            if time.time() > deadline:
                raise OSError("trang không vào được cảnh gather")
            time.sleep(0.05)
        load_ms = int(round((time.perf_counter() - t_start) * 1000))
        size = ws.eval("[innerWidth, innerHeight, devicePixelRatio, cv.width, cv.height]")
        if size[:3] != [WIDTH, HEIGHT, 1] or size[3:] != [WIDTH, HEIGHT]:
            raise OSError(f"cửa sổ đo không phải {WIDTH}x{HEIGHT}: {size}")
        time.sleep(warmup_s)
        ws.eval("window.__mark=window.__ts.length;true")
        time.sleep(duration_s)
        ts = ws.eval("window.__ts.slice(window.__mark)")
        if ws.eval("snap && snap.finished") is True:
            raise OSError("phiên gather kết thúc sớm trong lúc đo")
        samples = [(b - a) / 1000.0 for a, b in zip(ts, ts[1:]) if b > a]
        return samples, load_ms
    finally:
        if ws:
            ws.close()
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        shutil.rmtree(prof, ignore_errors=True)


def measure_browser(seed, duration_s, warmup_s=WARMUP_S, contract_path=None, chrome=None) -> dict:
    from .live import LiveGame, LiveServer
    from .scenario import load_scenario

    chrome = chrome or find_chrome()
    if not chrome:
        raise BadInput("không tìm thấy Chrome/Chromium (đặt CHROME_BIN hoặc dùng --mode sim)")
    t_start = time.perf_counter()
    contract = load_contract(contract_path or DEFAULT_PATH)
    tuning = contract["tuning"]
    fd, path = tempfile.mkstemp(suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(BENCH_SCENARIO, f)
        scenario = load_scenario(path, "gather", tuning, contract["contract_version"])
    finally:
        os.unlink(path)
    game = LiveGame("gather", tuning, scenario, seed, contract=contract)
    server = LiveServer(game, "127.0.0.1", 0)
    game.start()
    server.start()
    try:
        samples, load_ms = _browser_samples(chrome, server.url, duration_s, warmup_s, t_start)
    except OSError as e:
        raise BadInput(f"benchmark trình duyệt lỗi: {e}")
    finally:
        server.stop()
        game.stop()
    return _report(samples, load_ms)


def measure(seed, duration_s, warmup_s=WARMUP_S, contract_path=None, mode="auto") -> dict:
    if mode == "auto":
        mode = "browser" if find_chrome() else "sim"
        if mode == "sim":
            sys.stderr.write("cảnh báo: không có Chrome/Chromium, chạy chế độ sim (KHÔNG phải render)\n")
    sys.stderr.write(f"chế độ đo: {mode}" + (" (render thật bằng trình duyệt)\n" if mode == "browser"
                     else " (chỉ mô phỏng + bộ đệm CPU, KHÔNG phải render)\n"))
    if mode == "browser":
        return measure_browser(seed, duration_s, warmup_s, contract_path)
    return measure_sim(seed, duration_s, warmup_s, contract_path)


def main(argv=None) -> int:
    p = _Parser(prog="chonoi.bench")
    p.add_argument("--seed", required=True, type=int)
    p.add_argument("--duration", required=True, type=float)
    p.add_argument("--out", required=True)
    p.add_argument("--mode", choices=["auto", "browser", "sim"], default="auto",
                   help="browser = render thật qua Chrome headless; sim = chỉ mô phỏng (không render)")
    a = p.parse_args(argv)
    try:
        if a.duration <= 0:
            raise BadInput("--duration phải > 0")
        report = measure(a.seed, a.duration, mode=a.mode)
    except BadInput as e:
        sys.stderr.write(f"đầu vào sai: {e}\n")
        return 2
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(report, f, ensure_ascii=False)
        f.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
