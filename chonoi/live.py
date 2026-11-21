"""Cửa sổ chơi trực tiếp bằng TRÌNH DUYỆT, chỉ dùng thư viện chuẩn Python.

    python3 -m chonoi.live --mode gather|quan|day [--days N] [--seed N] [--port 8000]

Máy chủ HTTP nhỏ (ThreadingHTTPServer) phục vụ `chonoi/web/index.html` và hai API:
    GET  /state  -> snapshot JSON hiện tại (cùng trường như dòng snapshot của headless) + `meta` + `events`
    POST /input  -> {"move": [a, b], "interact": bool, "catch": bool}   (trạng thái phím đang giữ)
                    v1.1: + "pause", "shop_done" (bool, cạnh lên), "buy": "oxygen"|"hp" (lệnh một lần)
    POST /restart -> chơi lại từ đầu (cùng seed, cùng scenario)

Mô phỏng chạy 60 tick/s trong một luồng nền, dùng CÙNG lớp sim như headless (qua `runner.Session`).
Client chỉ ĐỌC snapshot và tự bỏ qua trường chưa có, nên luật do nhóm viết thêm trường nào cũng không vỡ.
Ngẫu nhiên vẫn đi qua `Streams` (seed); chỉ nhịp chạy theo đồng hồ thật, không đi vào luật.

v1.1 (TV6, T248): `--mode day [--days N]`; `meta` = tuning của PHA hiện tại + `phase`, `menu`, `day_plan`
(của Ngày), `shop` (catalog nâng cấp), `upgrades`, `active_upgrades`, `day`, `days_completed`; snapshot thêm
`paused` (bool) — để UI (chonoi/web) dựng DayIntro/EveningIntro/Shop/pause chỉ từ /state.
"""

import argparse
import json
import os
import sys
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .contract import DEFAULT_PATH, load_contract
from .errors import BadInput
from .inputs import BUTTONS_V10, LiveInputs, buttons_for
from .inventory import menu_kinds, read_inventory
from .runner import Session
from .scenario import load_scenario
from .sim.day import missing_day_keys

WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
TICK_S = 1.0 / 60.0
MAX_BODY = 4096
RECENT_EVENTS = 40


class LiveGame:
    """Một lượt chơi + luồng nền bước 60 tick/s. Mọi truy cập trạng thái đi qua khóa."""

    def __init__(self, mode, tuning, scenario, seed, inventory=None, inventory_out=None, days=1, contract=None):
        version = (contract or {}).get("contract_version", "1.0")
        self._args = (mode, tuning, scenario, seed, inventory, days, version)
        self.buttons, self.strings = buttons_for(contract) if contract is not None else (BUTTONS_V10, ())
        self.mode = mode
        self.tuning = tuning
        self.inventory_out = inventory_out
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None
        self._reset()

    def _reset(self):
        self.session = Session(*self._args)
        self.inputs = LiveInputs(self.buttons)
        self.events = self.session.initial_events()
        self._saved = False
        self.error = None

    # --- luồng nền ----------------------------------------------------------------
    def start(self):
        self._thread = threading.Thread(target=self._loop, name="chonoi-sim", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    def _loop(self):
        nxt = time.perf_counter()
        while not self._stop.is_set():
            nxt += TICK_S
            with self._lock:
                try:
                    self._tick_once()
                except Exception:  # luật của nhóm lỗi: báo ra terminal + client, dừng bước (restart để chơi lại)
                    self.error = traceback.format_exc()
                    sys.stderr.write(self.error)
                    self.session.sim.done = True
                    self.session.sim.reason = "error"
            delay = nxt - time.perf_counter()
            if delay > 0:
                self._stop.wait(delay)
            elif delay < -0.25:  # chạy chậm quá thì bỏ bù, tránh chạy dồn
                nxt = time.perf_counter()

    def _tick_once(self):
        s = self.session
        if s.done:
            return
        for row in s.step(self.inputs.advance()):
            self.events.append(row)
        del self.events[:-RECENT_EVENTS]
        if s.done and not self._saved:
            self._saved = True
            if self.inventory_out:
                try:
                    s.write_inventory_if_done(self.inventory_out)
                except OSError as e:
                    sys.stderr.write(f"lỗi ghi kho: {e}\n")

    # --- API cho handler -----------------------------------------------------------
    def state_json(self) -> bytes:
        with self._lock:
            snap = self.session.snapshot()
            snap["paused"] = self.session.paused
            snap["meta"] = self._meta(snap)
            snap["events"] = list(self.events)
            snap["finished"] = self.session.done
            snap["reason"] = self.session.sim.reason if self.session.done else None
            snap["error"] = self.error
            return json.dumps(snap, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    def _meta(self, snap) -> dict:
        """Tuning của pha hiện tại (gather/quan) + dữ liệu cho UI. Gather/quan độc lập giữ như v1.0."""
        if self.mode != "day":
            return self.tuning[self.mode]
        phase = snap["phase"]
        meta = dict(self.tuning.get(phase, {})) if phase in ("gather", "quan") else {}
        sim = self.session.sim
        meta.update({"phase": phase, "menu": self.tuning["menu"], "day_plan": snap.get("day_plan"),
                     "shop": self.tuning["shop"], "upgrades": snap.get("upgrades"),
                     "active_upgrades": snap.get("active_upgrades"), "day": snap.get("day"),
                     "days": sim.days, "days_completed": sim.days_completed})
        return meta

    def set_input(self, body: dict):
        move = body.get("move")
        if move is not None:
            ok = (isinstance(move, list) and len(move) == 2 and
                  all(isinstance(c, (int, float)) and not isinstance(c, bool) and abs(c) <= 1 for c in move))
            if not ok:
                raise ValueError("move phải là [a, b] trong [-1, 1]")
        buttons = {}
        for b in self.buttons:
            if b in body:
                if not isinstance(body[b], bool):
                    raise ValueError(f"{b} phải là boolean")
                buttons[b] = body[b]
        buy = None
        if "buy" in self.strings and "buy" in body:
            buy = body["buy"]
            if not (isinstance(buy, str) and buy):
                raise ValueError("buy phải là chuỗi khác rỗng")
        with self._lock:
            self.inputs.set(move, buy=buy, **buttons)

    def restart(self):
        with self._lock:
            self._reset()


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    game: LiveGame = None  # gán trên lớp con trong make_server

    def log_message(self, fmt, *args):  # yên lặng
        pass

    def _send(self, code, body: bytes, ctype="application/json; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/state":
            self._send(200, self.game.state_json())
        elif path in ("/", "/index.html"):
            try:
                with open(os.path.join(WEB_DIR, "index.html"), "rb") as f:
                    self._send(200, f.read(), "text/html; charset=utf-8")
            except OSError:
                self._send(404, b'{"error":"thieu index.html"}')
        else:
            # file tĩnh trong chonoi/web/ (vd. pixi.min.js); chặn thoát khỏi thư mục web
            rel = path.lstrip("/")
            file_path = os.path.abspath(os.path.join(WEB_DIR, rel))
            if file_path.startswith(os.path.abspath(WEB_DIR) + os.sep) and os.path.isfile(file_path):
                ctype = {".js": "application/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
                         ".png": "image/png"}.get(os.path.splitext(file_path)[1], "application/octet-stream")
                try:
                    with open(file_path, "rb") as f:
                        self._send(200, f.read(), ctype)
                    return
                except OSError:
                    pass
            self._send(404, b'{"error":"khong co"}')

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = -1
        if n < 0 or n > MAX_BODY:
            self._send(400, b'{"error":"body sai"}')
            return
        raw = self.rfile.read(n) if n else b""
        try:
            if path == "/input":
                body = json.loads(raw.decode("utf-8") or "{}")
                if not isinstance(body, dict):
                    raise ValueError("body phải là object")
                self.game.set_input(body)
            elif path == "/restart":
                self.game.restart()
            else:
                self._send(404, b'{"error":"khong co"}')
                return
        except (ValueError, UnicodeDecodeError) as e:
            self._send(400, json.dumps({"error": str(e)}).encode("utf-8"))
            return
        self._send(200, b'{"ok":true}')


class LiveServer:
    """Máy chủ + mô phỏng. port=0 -> cổng ngẫu nhiên (đọc `.port`)."""

    def __init__(self, game: LiveGame, host="127.0.0.1", port=8000):
        handler = type("Handler", (_Handler,), {"game": game})
        self.game = game
        self.httpd = ThreadingHTTPServer((host, port), handler)
        self.httpd.daemon_threads = True
        self.host = host
        self.port = self.httpd.server_address[1]
        self._thread = None

    @property
    def url(self):
        return f"http://{self.host}:{self.port}/"

    def start(self):
        self.game.start()
        self._thread = threading.Thread(target=self.httpd.serve_forever, name="chonoi-http", daemon=True)
        self._thread.start()

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        if self._thread:
            self._thread.join(timeout=2)
        self.game.stop()


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="chonoi.live", description="Chơi trực tiếp trên trình duyệt (starter).")
    p.add_argument("--mode", required=True, choices=["gather", "quan", "day"])
    p.add_argument("--days", type=int, default=None, help="chỉ với day: số Ngày 1–5 (mặc định 1)")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--port", type=int, default=8000, help="0 = cổng ngẫu nhiên")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--scenario")
    p.add_argument("--inventory", help="chỉ với quan: nạp kho từ file")
    p.add_argument("--inventory-out", dest="inventory_out", help="chỉ với gather: ghi kho khi kết thúc buổi")
    a = p.parse_args(argv)
    try:
        if a.inventory and a.mode != "quan":
            raise BadInput("--inventory chỉ dùng với quan")
        if a.inventory_out and a.mode != "gather":
            raise BadInput("--inventory-out chỉ dùng với gather")
        if a.days is not None and a.mode != "day":
            raise BadInput("--days chỉ dùng với --mode day")
        days = 1 if a.days is None else a.days
        if not (1 <= days <= 5):
            raise BadInput("--days phải là số nguyên từ 1 đến 5")
        if a.mode == "day" and (a.inventory or a.inventory_out):
            raise BadInput("--inventory/--inventory-out không dùng với day")
        contract = load_contract(os.environ.get("CHONOI_CONTRACT") or DEFAULT_PATH)
        tuning = contract["tuning"]
        if a.mode == "day" and missing_day_keys(tuning):
            raise BadInput(f"--mode day: contract chưa có khóa {', '.join(missing_day_keys(tuning))} (chờ TV1)")
        scenario = load_scenario(a.scenario, a.mode, tuning, contract["contract_version"])
        inventory = read_inventory(a.inventory, version=contract["contract_version"]) if a.inventory else None
        if inventory is not None and "stock" in scenario:
            raise BadInput("vừa có quan.stock vừa có --inventory")
        game = LiveGame(a.mode, tuning, scenario, a.seed, inventory, a.inventory_out, days=days, contract=contract)
        server = LiveServer(game, a.host, a.port)
    except BadInput as e:
        sys.stderr.write(f"đầu vào sai: {e}\n")
        return 2
    except OSError as e:
        sys.stderr.write(f"không mở được cổng {a.port}: {e}\n")
        return 1
    server.start()
    print(f"Mở trình duyệt tại {server.url}  (chế độ {a.mode}, seed {a.seed}). Ctrl+C để dừng.", flush=True)
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
