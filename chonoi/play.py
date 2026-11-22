"""Chơi game ngay trong TERMINAL (vỏ thứ ba, cạnh headless và live). Chỉ thư viện chuẩn.

    python3 -m chonoi.play --mode day [--seed N] [--days 1-5] [--scenario F]
        [--demo] [--text] [--ticks N] [--ascii] [--sticky] [--speed X]

Dùng CHÙNG `runner.Session` như headless/live: file này chỉ ĐỌC snapshot/event, không có luật chơi
(các dòng "BÂY GIỜ LÀM" chỉ diễn giải luật hiện có từ snapshot + tuning), bỏ qua trường chưa biết.
Mặc định của headless/live/JSONL không bị đổi. Có curses + TTY -> giao diện thời gian thực (60 tick/s, ~30 fps);
không có (hoặc `--text`) -> chế độ dòng lệnh đọc stdin (`w 30`, `e`, `space`, `wait 60`, ...).
Nhân vật chính: Trường con.
"""

import argparse
import math
import os
import re
import sys
import time

from .contract import DEFAULT_PATH, load_contract
from .errors import BadInput
from .inputs import BUTTONS_V10, LiveInputs, buttons_for
from .runner import Session
from .scenario import load_scenario
from .sim.day import missing_day_keys

TICK_HZ = 60
FPS = 30
MOVE_HOLD_S = 0.22          # terminal không có "nhả phím": mỗi lần bấm giữ hướng ngần này giây
PLAYER_NAME = "Trường con"

KIND_VI = {"ca_linh": "cá linh", "ca_loc": "cá lóc", "ca_keo": "cá kèo", "bong_dien_dien": "bông điên điển",
           "bong_sung": "bông súng", "keo_neo": "keo nèo"}
KIND_ABBR = {"ca_linh": "LI", "ca_loc": "LO", "ca_keo": "KE", "bong_dien_dien": "DD", "bong_sung": "BS",
             "keo_neo": "KN"}
DISH_VI = {"ca_loc_nuong_trui": "Cá lóc nướng trui", "goi_bong_sung": "Gỏi bông súng",
           "lau_ca_linh_dien_dien": "Lẩu cá linh bông điên điển", "canh_chua_ca_loc": "Canh chua cá lóc",
           "ca_keo_nuong": "Cá kèo nướng", "lau_mam": "Lẩu mắm"}
DISH_SHORT = {"ca_loc_nuong_trui": "Lóc nướng", "goi_bong_sung": "Gỏi BS", "lau_ca_linh_dien_dien": "Lẩu linh",
              "canh_chua_ca_loc": "Canh chua", "ca_keo_nuong": "Kèo nướng", "lau_mam": "Lẩu mắm"}
UPGRADE_VI = {"oxygen": "Bình oxy (oxy tối đa)", "hp": "Áo phao (Máu tối đa)"}
FIELD_VI = {"oxygen_max_s": "oxy tối đa {}s", "hp_max": "Máu tối đa {}"}
REASON_VI = {"docked": "cập bến", "time": "hết giờ", "fainted": "ngất", "days_complete": "hoàn thành các Ngày",
             "patience": "hết kiên nhẫn", "closing": "đóng cửa"}

GLYPH_U = {"heart": "♥", "heart0": "♡", "full": "█", "empty": "░", "face": "☺", "dock": "⌂", "node": "❀",
           "node0": "o", "wave": "~", "dot": "·", "h": "─", "v": "│", "tl": "┌", "tr": "┐", "bl": "└",
           "br": "┘", "fishr": "><>", "fishl": "<><", "arrow": "▶", "star": "★"}
GLYPH_A = {"heart": "v", "heart0": ".", "full": "#", "empty": "-", "face": ":)", "dock": "D", "node": "*",
           "node0": "o", "wave": "~", "dot": ".", "h": "-", "v": "|", "tl": "+", "tr": "+", "bl": "+",
           "br": "+", "fishr": "><>", "fishl": "<><", "arrow": ">", "star": "*"}


def dish_name(d):
    return DISH_VI.get(d, str(d).replace("_", " "))


def kind_name(k):
    return KIND_VI.get(k, str(k).replace("_", " "))


# ---------------------------------------------------------------------------- truyện (story.js, nếu có)
STORY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web", "story.js")
_FALLBACK_INTRO = [
    "Trường con chèo ghe ra chợ nổi trên sông.",
    "Sáng lặn bắt cá, hái bông súng; tối mở quán trên ghe, nấu cho khách.",
    "Dưới sâu có Cá Sấu Năm Chèo — giữ hơi thở và nhớ về bến!",
]


def load_story(path=STORY_PATH):
    """Đọc ChoNoiStory từ story.js bằng regex; hỏng/thiếu -> dùng chữ riêng. Trả {'intro': [...], 'pre': {n: [...]}}."""
    out = {"intro": list(_FALLBACK_INTRO), "pre": {}}
    try:
        with open(path, encoding="utf-8") as f:
            src = f.read()
        names = {}
        for who, nm in re.findall(r"(\w+):\s*\{\s*name:\s*'([^']+)'", src):
            names[who] = nm
        letter = {"S": "sen", "B": "batu", "C": "chuba", "H": "haibap", "K": "casau"}

        def lines(block):
            res = []
            for l, t in re.findall(r"\b([SBCHK])\('((?:[^'\\]|\\.)*)'\)", block):
                res.append(f"{names.get(letter[l], l)}: {t.replace(chr(92) + chr(39), chr(39))}")
            return res
        m = re.search(r"intro:\s*\[(.*?)\n\s*\],", src, re.S)
        if m and lines(m.group(1)):
            out["intro"] = lines(m.group(1))
        for n in range(1, 6):
            m = re.search(rf"\n\s*{n}:\s*\{{\s*pre:\s*\[(.*?)\]", src, re.S)
            if m:
                out["pre"][n] = lines(m.group(1))
    except (OSError, ValueError, re.error, KeyError):
        pass
    return out


# ---------------------------------------------------------------------------- canvas
class Canvas:
    """Lưới ký tự + thuộc tính ngữ nghĩa (tên). Cùng một canvas ra curses hoặc text."""

    def __init__(self, w, h):
        self.w, self.h = w, h
        self.ch = [[" "] * w for _ in range(h)]
        self.at = [[""] * w for _ in range(h)]

    def put(self, y, x, text, attr=""):
        if not (0 <= y < self.h):
            return
        for i, c in enumerate(str(text)):
            xx = x + i
            if 0 <= xx < self.w:
                self.ch[y][xx] = c
                self.at[y][xx] = attr

    def fill(self, y, x, w, h, c=" ", attr=""):
        for yy in range(y, y + h):
            self.put(yy, x, c * w, attr)

    def box(self, y, x, w, h, g, attr=""):
        self.put(y, x, g["tl"] + g["h"] * (w - 2) + g["tr"], attr)
        self.put(y + h - 1, x, g["bl"] + g["h"] * (w - 2) + g["br"], attr)
        for yy in range(y + 1, y + h - 1):
            self.put(yy, x, g["v"], attr)
            self.put(yy, x + w - 1, g["v"], attr)

    def overlay(self, lines, g, title="", attr="hint"):
        """Hộp chữ ở giữa; lines: list str hoặc (str, attr)."""
        rows = [(l, "") if isinstance(l, str) else l for l in lines]
        bw = min(self.w - 2, max([len(t) for t, _ in rows] + [len(title) + 4]) + 4)
        bh = min(self.h - 2, len(rows) + 2)
        x, y = (self.w - bw) // 2, (self.h - bh) // 2
        self.fill(y, x, bw, bh)
        self.box(y, x, bw, bh, g, attr)
        if title:
            self.put(y, x + 2, f" {title} ", "title")
        for i, (t, a) in enumerate(rows[:bh - 2]):
            self.put(y + 1 + i, x + 2, t[:bw - 4], a)

    def text_lines(self):
        return ["".join(r).rstrip() for r in self.ch]

    def to_text(self):
        return "\n".join(self.text_lines())

    def runs(self, y):
        """[(x, text, attr)] gom theo thuộc tính."""
        out, row, at = [], self.ch[y], self.at[y]
        i = 0
        while i < self.w:
            j = i
            while j < self.w and at[j] == at[i]:
                j += 1
            out.append((i, "".join(row[i:j]), at[i]))
            i = j
        return out


# ---------------------------------------------------------------------------- tiện ích đọc snapshot
def hold_items(snap):
    """[(kind, fresh|None)] — hold có thể là mảng chuỗi (v1.0) hoặc cá thể {id,kind,fresh} (v1.2)."""
    out = []
    for it in snap.get("hold") or []:
        if isinstance(it, dict):
            out.append((it.get("kind"), it.get("fresh")))
        else:
            out.append((it, None))
    return out


def counts_of(items, spoiled_below=None):
    c = {}
    for k, f in items:
        c[k] = c.get(k, 0) + 1
    return c


def stock_items(snap):
    s = snap.get("stock")
    out = []
    if isinstance(s, list):
        out = [(it.get("kind"), it.get("fresh")) for it in s if isinstance(it, dict)]
    elif isinstance(s, dict):
        for k in sorted(s):
            out += [(k, None)] * int(s[k])
    return out


def is_spoiled(fresh, below):
    return fresh is not None and below is not None and fresh < below


def bar(frac, n, g):
    frac = max(0.0, min(1.0, frac))
    k = int(round(frac * n))
    return g["full"] * k + g["empty"] * (n - k)


def fmt_time(ticks):
    s = max(0, int(math.ceil(ticks / TICK_HZ)))
    return f"{s // 60:02d}:{s % 60:02d}"


def compass(dx, dy):
    """Hướng bằng chữ từ vector (x sang phải, y xuống)."""
    parts = []
    if dy < -0.7:
        parts.append("lên")
    elif dy > 0.7:
        parts.append("xuống")
    if dx < -0.7:
        parts.append("trái")
    elif dx > 0.7:
        parts.append("phải")
    return "-".join(parts) or "ngay tại đây"


# ---------------------------------------------------------------------------- gợi ý "BÂY GIỜ LÀM"
def gather_hint(snap, tuning):
    """Diễn giải luật gather (không áp luật): trả dict(text, target=(x,d)|None, act=None|'interact'|'catch')."""
    g = tuning["gather"]
    p = snap["player"]
    pos = p["pos"]
    speed = g["swim_speed"]
    depth = pos[1]
    surf = g["surface_depth"]
    under = depth > surf
    dock = g["dock_pos"]
    hold = hold_items(snap)
    have = counts_of(hold)
    free = snap.get("hold_capacity", g["hold_capacity"]) - len(hold)
    plan = ((snap.get("day_plan") or {}).get("ingredients")) or {}
    need = {k: max(0, n - have.get(k, 0)) for k, n in plan.items()}
    met = bool(plan) and all(v == 0 for v in need.values())
    dist_dock = math.dist(pos, dock)
    back_ticks = dist_dock / speed * TICK_HZ
    t_left = snap["time_left_ticks"]
    in_dock = dist_dock <= g["dock_radius"]

    def go(target, text):
        dx, dy = target[0] - pos[0], target[1] - pos[1]
        return {"text": f"{text} ({compass(dx, dy)}, cách {math.hypot(dx, dy):.0f}m)", "target": tuple(target),
                "act": None}

    def to_dock(why):
        if in_dock and not under:
            return {"text": f"{why} — bấm E để cập bến, mở quán.", "target": tuple(dock), "act": "interact"}
        return go(dock, f"{why}: bơi về bến (mặt nước)")
    if t_left <= back_ticks * 1.3 + 300:
        return to_dock("Sắp hết giờ")
    if free <= 0:
        return to_dock("Giỏ đầy")
    if met:
        return to_dock("Đủ nguyên liệu hôm nay")
    asc = depth / speed * TICK_HZ
    if under and p["oxygen_ticks"] < asc * 1.4 + 90:
        return go((pos[0], 0.0), "SẮP HẾT OXY! Lên mặt nước")
    mcfg = ((g.get("monsters") or {}).get("species") or {}).get("ca_sau", {})
    danger = float(mcfg.get("detect_radius", 10))
    mons = [m["pos"] for m in snap.get("monsters") or []]
    wants = (lambda k: need.get(k, 0) > 0) if plan else (lambda k: True)
    cands = []
    for n in snap.get("nodes") or []:
        if n.get("ready") and wants(n["kind"]) and g["node_yield"] <= free:
            cands.append((abs(n["pos"][0] - pos[0]) + 2 * n["pos"][1], "node", n))
    for f in snap.get("fish") or []:
        y = g["fish_yield"].get(f["kind"], 1)
        if wants(f["kind"]) and y <= free and not any(math.dist(f["pos"], m) < danger * 0.9 for m in mons):
            cands.append((math.dist(pos, f["pos"]) + f["pos"][1] * 0.7, "fish", f))
    if not cands:
        return to_dock("Không còn gì hái/bắt được")
    cands.sort(key=lambda c: (c[0], c[2]["id"]))
    _, typ, e = cands[0]
    if typ == "node":
        tgt = (e["pos"][0], 0.0)
        if not under and math.dist(pos, e["pos"]) <= g["interact_radius"] * 0.9:
            return {"text": f"Bấm E để hái {kind_name(e['kind'])} ({e['id']}).", "target": tuple(e["pos"]),
                    "act": "interact"}
        return go(tgt, f"Bơi trên mặt nước tới {kind_name(e['kind'])} {e['id']}")
    if (not under or depth < 2) and p["oxygen_ticks"] < p.get("oxygen_max_ticks", 0) * 0.9:
        return {"text": "Nổi chờ hồi oxy trước khi lặn sâu.", "target": None, "act": None}
    if under and p["catch_cd_ticks"] == 0 and math.dist(pos, e["pos"]) <= g["catch_radius"] * 0.9:
        return {"text": f"Bấm SPACE để bắt đàn {kind_name(e['kind'])}!", "target": tuple(e["pos"]),
                "act": "catch"}
    return go(e["pos"], f"Lặn tới đàn {kind_name(e['kind'])} {e['id']} rồi bấm SPACE")


def quan_hint(snap, tuning):
    """Cách phục vụ (đọc từ sim/quan.py): E gần BẾP sẵn sàng = lấy món (tay trống); E gần bếp nghỉ = nấu đơn
    chờ nấu cũ nhất (order_tick rồi id bàn); E gần BÀN có khách đã nấu = giao món đúng đơn."""
    q = tuning["quan"]
    p = snap["player"]["pos"]
    r = q["interact_radius"]
    tables = {t["id"]: t for t in snap.get("tables") or []}
    stoves = list(snap.get("stoves") or [])
    custs = list(snap.get("customers") or [])
    hand = snap.get("hand")

    def idnum(s):
        m = re.search(r"\d+", str(s))
        return int(m.group()) if m else 0

    def go(pos, text, act):
        d = math.dist(p, pos)
        dx, dy = pos[0] - p[0], pos[1] - p[1]
        if d <= r * 0.9:
            return {"text": text.format(where="Đang đứng đủ gần") + " — bấm E.", "target": tuple(pos), "act": "interact"}
        return {"text": text.format(where=f"Đi {compass(dx, dy)} (cách {d:.0f}m)"), "target": tuple(pos), "act": None}
    if isinstance(hand, dict):
        c = next((c for c in custs if c["id"] == hand.get("order_id")), None)
        if c is not None and c["table_id"] in tables:
            return go(tables[c["table_id"]]["pos"], "{where} tới bàn %s, giao %s" % (c["table_id"], dish_name(hand.get("dish_id"))), 0)
    if hand is None:
        ready = [s for s in stoves if s.get("state") == "ready"]
        if ready:
            s = min(ready, key=lambda s: math.dist(p, s["pos"]))
            return go(s["pos"], "{where} tới bếp %s: lấy món chín (%s)" % (s["id"], dish_name((s.get("dish") or {}).get("dish_id"))), 0)
    orders = sorted((c for c in custs if c.get("order_status") == "reserved"),
                    key=lambda c: (c.get("order_tick", 0), idnum(c["table_id"])))
    idle = [s for s in stoves if s.get("state") == "idle"]
    if orders and idle:
        s = min(idle, key=lambda s: math.dist(p, s["pos"]))
        c = orders[0]
        return go(s["pos"], "{where} tới bếp %s: nấu %s cho bàn %s" % (s["id"], dish_name(c["dish_id"]), c["table_id"]), 0)
    cooking = [s for s in stoves if s.get("state") == "cooking"]
    if cooking:
        s = min(cooking, key=lambda s: s["cook_ticks_left"])
        return {"text": f"Chờ bếp {s['id']} nấu xong (còn {math.ceil(s['cook_ticks_left'] / TICK_HZ)}s); đứng gần bếp sẵn sàng lấy món.",
                "target": tuple(s["pos"]), "act": None}
    if any(c.get("order_status") == "unfulfillable" for c in custs):
        return {"text": "Có bàn hết nguyên liệu để nấu — không làm gì được, khách sẽ tự bỏ đi.", "target": None, "act": None}
    if custs:
        return {"text": "Khách đang ăn / chờ — đợi khách thanh toán.", "target": None, "act": None}
    return {"text": "Chưa có khách. Đứng giữa quán chờ khách tới.", "target": None, "act": None}


# ---------------------------------------------------------------------------- trạng thái chơi
STAGES = ("intro", "play", "result", "summary")


class Game:
    """Một lượt chơi trong terminal: Session + máy trạng thái màn hình (intro/play/result/summary)."""

    def __init__(self, mode="day", days=1, seed=1, scenario_path=None, contract_path=None, story=None):
        contract = load_contract(contract_path or os.environ.get("CHONOI_CONTRACT") or DEFAULT_PATH)
        self.tuning = contract["tuning"]
        if mode == "day":
            miss = missing_day_keys(self.tuning)
            if miss:
                raise BadInput(f"--mode day: contract chưa có khóa {', '.join(miss)}")
        self.contract = contract
        self.version = contract["contract_version"]
        self.mode, self.days, self.seed = mode, days, seed
        self.scenario = load_scenario(scenario_path, mode, self.tuning, self.version)
        self.buttons, _ = buttons_for(contract)
        self.story = story if story is not None else load_story()
        self.spoiled_below = (self.tuning.get("freshness") or {}).get("spoiled_below")
        self.sticky = False
        self.restart()

    def restart(self):
        self.session = Session(self.mode, self.tuning, self.scenario, self.seed, None, self.days, self.version)
        self.inputs = LiveInputs(self.buttons)
        self.log = []
        self.result = None
        self.dish_counts = {}
        self.stage = "intro"
        self.help = False
        self.confirm_quit = False
        self.ui_paused = False
        self.want_quit = False
        self.move_keys = {}      # hướng -> thời điểm hết hạn
        self.sticky_move = (0.0, 0.0)
        self.oneshots = []
        self.frame = 0
        self.last_snap = None
        self._rep0 = None
        for r in self.session.initial_events():
            self._note(r)
        self.snap()

    # --- snapshot (đệm 1 tick) ---
    def snap(self):
        if self.last_snap is None or self.last_snap.get("tick") != self.session.tick or \
                self.last_snap.get("_stage") != self.stage:
            s = self.session.snapshot()
            s["_stage"] = self.stage
            self.last_snap = s
        return self.last_snap

    @property
    def phase(self):
        return self.session.sim.phase

    @property
    def paused(self):
        return self.session.paused or self.ui_paused

    # --- nhật ký / theo dõi (chỉ đọc event) ---
    def _note(self, row):
        name, d = row["name"], row.get("data") or {}
        ph = row.get("phase")
        if name == "phase_start" and ph == "quan":
            self._rep0 = self.session.sim.reputation
            self.result = {"served": 0, "left": 0, "money": 0, "tip": 0, "rep": self._rep0, "rep_delta": 0.0}
        r = self.result
        if r is not None and ph == "quan":
            if name == "paid":
                r["served"] += 1
                r["money"] += d.get("base_price", 0)
                r["tip"] += d.get("tip", 0)
                if d.get("dish_id"):
                    self.dish_counts[d["dish_id"]] = self.dish_counts.get(d["dish_id"], 0) + 1
            elif name == "customer_left":
                r["left"] += 1
            if name in ("paid", "customer_left", "quan_end"):
                r["rep"] = d.get("reputation", r["rep"])
            r["rep_delta"] = round(r["rep"] - (self._rep0 or 0), 2)
        text = self.describe(row)
        if text:
            self.log.append((row["tick"], text))
            del self.log[:-30]

    @staticmethod
    def describe(row):
        n, d = row["name"], row.get("data") or {}
        K = lambda k: kind_name(k)
        table = {
            "day_start": lambda: None, "day_plan": lambda: None, "node_regrown": lambda: None,
            "phase_start": lambda: {"gather": "Buổi sáng bắt đầu.", "quan": "Mở quán!", "shop": "Vào Shop."}.get(row.get("phase")),
            "dive": lambda: "Lặn xuống.", "surface": lambda: "Nổi lên mặt nước (hồi oxy).",
            "oxygen_empty": lambda: "HẾT OXY! Lên mặt nước ngay!",
            "choke": lambda: f"Ngạt thở! Máu còn {d.get('hp')}.",
            "faint": lambda: "NGẤT! Mất hết giỏ.",
            "fish_caught": lambda: f"Bắt được {K(d.get('kind'))} +{d.get('yield')}.",
            "gather": lambda: f"Hái {K(d.get('kind'))} +{d.get('amount')}.",
            "hold_full": lambda: "Giỏ không đủ chỗ!",
            "monster_hit": lambda: f"CÁ SẤU CẮN! Máu còn {d.get('hp')}, rơi {len(d.get('lost') or [])} món.",
            "gather_end": lambda: f"Kết thúc buổi sáng ({REASON_VI.get((d or {}).get('reason'), d.get('reason'))}).",
            "spoiled": lambda: f"{K(d.get('kind'))} bị ươn ({d.get('location', 'giỏ')}).",
            "customer_arrived": lambda: f"Khách bàn {d.get('table_id')} gọi {dish_name(d.get('dish_id'))}.",
            "cook_started": lambda: f"Bếp {d.get('stove_id')} nấu {dish_name(d.get('dish_id'))}.",
            "dish_ready": lambda: f"Bếp {d.get('stove_id')}: món chín, lấy đi!",
            "dish_picked": lambda: f"Bưng {dish_name(d.get('dish_id'))}.",
            "served": lambda: f"Giao món tới bàn {d.get('table_id')}.",
            "paid": lambda: f"Bàn {d.get('table_id')} trả {d.get('base_price', 0) + d.get('tip', 0)}k (boa {d.get('tip', 0)}).",
            "customer_left": lambda: f"Khách bàn {d.get('table_id')} bỏ đi ({REASON_VI.get(d.get('reason'), d.get('reason'))}).",
            "dish_burnt": lambda: "Món cháy mất!",
            "no_dish": lambda: "Hết nguyên liệu cho món khách gọi.",
            "quan_end": lambda: "Quán đóng cửa.",
            "bought": lambda: f"Đã mua {UPGRADE_VI.get(d.get('upgrade'), d.get('upgrade'))} cấp {d.get('level')}.",
            "buy_failed": lambda: f"Không mua được ({ {'funds': 'thiếu tiền', 'max_level': 'đã tối đa'}.get(d.get('reason'), d.get('reason')) }).",
            "shop_end": lambda: "Rời Shop.",
            "paused": lambda: "Tạm dừng.", "resumed": lambda: "Tiếp tục.",
        }
        f = table.get(n)
        if f is None:
            return n.replace("_", " ")
        try:
            return f()
        except Exception:
            return n

    # --- bước tick ---
    def _release_moves(self, now):
        if self.sticky:
            return self.sticky_move
        x = y = 0.0
        for dname, exp in list(self.move_keys.items()):
            if exp < now:
                del self.move_keys[dname]
                continue
            dx, dy = DIRS[dname]
            x, y = x + dx, y + dy
        return (max(-1.0, min(1.0, x)), max(-1.0, min(1.0, y)))

    def set_move(self, mv):
        """Ghi đè hướng (bot / chế độ text)."""
        self.move_keys = {}
        self.sticky_move = mv
        self.inputs.set(move=list(mv))

    def tick(self, now=None, move=None):
        """Một tick sim nếu màn đang chơi. Trả True nếu có chạy."""
        if self.stage != "play" or self.help or self.confirm_quit:
            return False
        if self.session.done:
            return False
        if self.ui_paused:
            return False
        if move is None:
            move = self._release_moves(now if now is not None else time.perf_counter())
        if not self.session.paused:
            self.inputs.set(move=list(move))
        shot = self.oneshots
        self.oneshots = []
        buy = None
        for b in shot:
            if b[0] == "buy":
                buy = b[1]
            else:
                self.inputs.set(**{b[0]: True})
        if buy:
            self.inputs.set(buy=buy)
        before = (self.phase, getattr(self.session.sim, "day", 0))
        rows = self.session.step(self.inputs.advance())
        for b in shot:
            if b[0] != "buy":
                self.inputs.set(**{b[0]: False})
        for r in rows:
            self._note(r)
        self.snap()
        if self.session.done:
            self.stage = "summary"
        elif self.session.phase_changed and (self.phase, getattr(self.session.sim, "day", 0)) != before:
            self.stage = "result" if self.phase == "shop" else "intro"
            self.move_keys = {}
            self.sticky_move = (0.0, 0.0)
            self.inputs.set(move=[0.0, 0.0])
        return True

    def advance(self, n, now=None):
        for _ in range(n):
            if not self.tick(now):
                break

    # --- phím / lệnh (đã chuẩn hóa tên) ---
    def key(self, k, now=None):
        now = time.perf_counter() if now is None else now
        if self.confirm_quit:
            if k in ("y", "enter"):
                self.want_quit = True
            elif k in ("n", "esc", "q"):
                self.confirm_quit = False
            return
        if self.help:
            self.help = False
            return
        if k == "q":
            if self.stage == "summary":
                self.want_quit = True
            else:
                self.confirm_quit = True
            return
        if k == "h":
            self.help = True
            return
        if self.stage in ("intro", "result"):
            if k in ("enter", "space"):
                self.stage = "play"
            return
        if self.stage == "summary":
            if k == "r":
                self.restart()
            return
        # --- đang chơi ---
        if k in ("p", "esc"):
            if "pause" in self.buttons:
                self.oneshots.append(("pause", True))
                if self.session.paused:
                    self.tick(now)   # cạnh pause phải đi qua một bước để thoát pause
                else:
                    self.tick(now)
            else:
                self.ui_paused = not self.ui_paused
            return
        if self.phase == "shop":
            if k in ("enter", "space"):
                self.oneshots.append(("shop_done", True))
            elif k.isdigit():
                ups = sorted(((self.tuning.get("shop") or {}).get("upgrades") or {}))
                i = int(k) - 1
                if 0 <= i < len(ups):
                    self.oneshots.append(("buy", ups[i]))
            return
        if k in DIRS:
            if self.sticky:
                self.sticky_move = DIRS[k]
            else:
                self.move_keys[k] = now + MOVE_HOLD_S
        elif k == "x":
            self.sticky_move = (0.0, 0.0)
            self.move_keys = {}
        elif k == "e":
            self.oneshots.append(("interact", True))
        elif k == "space" and self.phase == "gather":
            self.oneshots.append(("catch", True))


DIRS = {"w": (0.0, -1.0), "s": (0.0, 1.0), "a": (-1.0, 0.0), "d": (1.0, 0.0)}
KEYMAP_NAMES = {"up": "w", "down": "s", "left": "a", "right": "d"}


# ---------------------------------------------------------------------------- vẽ
def _title_phase(game, snap):
    sim = game.session.sim
    day = f"Ngày {snap.get('day', 1)}/{game.days} · " if game.mode == "day" else ""
    ph = {"gather": "Buổi sáng — Lặn & Hái", "quan": "Buổi tối — Mở Quán", "shop": "Shop cuối Ngày"}.get(snap["phase"], "")
    return f"{day}{ph}"


def _hud_top(c, game, snap, g):
    c.put(0, 0, " " * c.w, "title")
    c.put(0, 1, "QUÁN ĂN CHỢ NỔI", "title")
    c.put(0, 20, "· " + _title_phase(game, snap), "title")
    right = f"Tiền {snap['money']}k  Uy tín {snap['reputation']:.1f}{g['star']}  Điểm {snap['score']}"
    c.put(0, max(0, c.w - len(right) - 1), right, "title")


def _hint_line(c, y, hint):
    c.put(y, 1, "BÂY GIỜ LÀM:", "hint")
    c.put(y, 14, (hint or {}).get("text", ""), "hintt")


def _log_and_footer(c, game, log_rows, footer):
    top = c.h - 1 - log_rows
    c.put(top - 1, 0, "─" * c.w if c.w else "", "dim")
    shown = game.log[-log_rows:]
    for i, (t, text) in enumerate(shown):
        c.put(top + i, 1, f"[{fmt_time(t)}] {text}"[:c.w - 2], "log")
    c.put(c.h - 1, 0, footer[:c.w], "dim")
    return top - 1


def render_gather(c, game, snap, g):
    t = game.tuning["gather"]
    p = snap["player"]
    _hud_top(c, game, snap, g)
    oxy_frac = p["oxygen_ticks"] / max(1, p["oxygen_max_ticks"])
    low = oxy_frac < 0.25
    row1 = f" Giờ {fmt_time(snap['time_left_ticks'])}   O2 "
    c.put(1, 0, row1)
    c.put(1, len(row1), "[" + bar(oxy_frac, 20, g) + "]", "bad" if low else "good")
    x = len(row1) + 22
    secs = f" {p['oxygen_ticks'] / TICK_HZ:4.1f}s"
    c.put(1, x, secs, "bad" if low else "")
    x += len(secs) + 2
    c.put(1, x, "HP ")
    c.put(1, x + 3, g["heart"] * max(0, p["hp"]) + g["heart0"] * max(0, p["hp_max"] - p["hp"]), "bad")
    x += 4 + p["hp_max"] + 1
    alerts = []
    if p.get("invuln_ticks", 0) > 0:
        alerts.append("(vừa bị cắn - tạm bất tử)")
    if oxy_frac == 0 and not p.get("at_surface"):
        alerts.append("NGẠT!")
    for m in snap.get("monsters") or []:
        if m.get("state") == "chase":
            alerts.append("CÁ SẤU ĐANG ĐUỔI!")
            break
    c.put(1, x, " ".join(alerts), "bad")
    # giỏ
    hold = hold_items(snap)
    cap = snap.get("hold_capacity", 0)
    c.put(2, 0, f" Giỏ {len(hold)}/{cap} ")
    xx = 12 + len(str(len(hold))) + len(str(cap))
    below = game.spoiled_below
    for i in range(cap):
        if i < len(hold):
            k, f = hold[i]
            sp = is_spoiled(f, below)
            mark = "!" if sp else ("+" if f is not None else " ")
            c.put(2, xx + i * 4, f"{KIND_ABBR.get(k, '??')}{mark}", "bad" if sp else "good")
        else:
            c.put(2, xx + i * 4, " . ", "dim")
    nm = (snap.get("day_plan") or {}).get("ingredients") or {}
    have = counts_of(hold)
    if nm:
        txt = "Cần: " + ", ".join(f"{kind_name(k)} {have.get(k, 0)}/{n}" for k, n in nm.items())
        c.put(3, 1, txt[:c.w - 2], "dim")
    hint = gather_hint(snap, game.tuning)
    _hint_line(c, 4, hint)
    # bản đồ nhìn ngang
    log_rows = 5 if c.h >= 30 else 3
    bottom = _log_and_footer(c, game, log_rows, " WASD/←↑↓→ bơi · E hái/cập bến · SPACE bắt cá · P tạm dừng · H trợ giúp · Q thoát")
    my0, mh = 5, bottom - 5
    if mh < 6:
        return
    gut = 5
    mw = c.w - gut - 1
    bx, bd = t["bounds"]["x"], t["bounds"]["d"]

    def cx(x_):
        return gut + int(round((x_ - bx[0]) / (bx[1] - bx[0]) * (mw - 1)))

    def ry(d_):
        return my0 + int(round((d_ - bd[0]) / (bd[1] - bd[0]) * (mh - 2)))
    c.put(my0, gut, g["wave"] * mw, "water")
    for dm in range(5, int(bd[1]) + 1, 5):
        r = ry(dm)
        c.put(r, 0, f"{dm:>3}m", "dim")
        c.put(r, gut, (g["dot"] + "   ") * (mw // 4), "dim")
    c.put(my0, 0, "  0m", "dim")
    c.put(my0 + mh - 1, gut, "=" * mw, "dim")
    dock = t["dock_pos"]
    c.put(my0, cx(dock[0]) - 1, g["dock"] + "bến", "dock")
    for n in snap.get("nodes") or []:
        if n.get("ready"):
            c.put(my0, cx(n["pos"][0]), g["node"], "node")
        else:
            c.put(my0, cx(n["pos"][0]), g["node0"], "dim")
    tgt = hint.get("target")
    fish_attr = {"ca_linh": "f_linh", "ca_loc": "f_loc", "ca_keo": "f_keo"}
    for f in snap.get("fish") or []:
        face_r = math.cos(math.radians(f.get("heading_deg", 0))) >= 0
        r = max(my0 + 1, ry(f["pos"][1]))
        c.put(r, cx(f["pos"][0]) - 1, g["fishr"] if face_r else g["fishl"], fish_attr.get(f["kind"], "f_linh"))
    for m in snap.get("monsters") or []:
        r = max(my0 + 1, ry(m["pos"][1]))
        chase = m.get("state") == "chase"
        c.put(r, cx(m["pos"][0]) - 3, "~~CÁ SẤU>" if chase else "~Cá Sấu~", "bad" if chase else "monster")
    px, py = cx(p["pos"][0]), ry(p["pos"][1])
    if tgt is not None:
        tx, ty = cx(tgt[0]), ry(tgt[1])
        if hint.get("act"):
            c.put(ty, tx - 3, "[", "hint")
            c.put(ty, tx + 2, "]", "hint")
        else:
            c.put(ty, tx, "X", "hint")
    blink = p.get("invuln_ticks", 0) > 0 and (snap["tick"] // 6) % 2 == 0
    if not blink:
        c.put(py, px, "@", "player")
    if p["catch_cd_ticks"] > 0:
        c.put(py, px + 2, "·", "dim")


def _stock_summary(snap, below):
    items = stock_items(snap)
    cnt, bad = {}, {}
    for k, f in items:
        cnt[k] = cnt.get(k, 0) + 1
        if is_spoiled(f, below):
            bad[k] = bad.get(k, 0) + 1
    if not cnt:
        return "Kho: (trống)"
    return "Kho: " + ", ".join(f"{kind_name(k)} {n}" + (f" ({bad[k]} ươn)" if k in bad else "") for k, n in sorted(cnt.items()))


def render_quan(c, game, snap, g):
    t = game.tuning["quan"]
    _hud_top(c, game, snap, g)
    c.put(1, 0, f" Giờ {fmt_time(snap['time_left_ticks'])}   {_stock_summary(snap, game.spoiled_below)}"[:c.w])
    hand = snap.get("hand")
    c.put(2, 1, "Tay: ", "")
    c.put(2, 6, dish_name(hand["dish_id"]) + f" (cho đơn {hand['order_id']})" if isinstance(hand, dict) else "(trống)",
          "good" if isinstance(hand, dict) else "dim")
    plan = (snap.get("day_plan") or {}).get("dishes") or {}
    if plan:
        c.put(3, 1, "Thực đơn hôm nay: " + ", ".join(dish_short(d) for d in plan), "dim")
    hint = quan_hint(snap, game.tuning)
    _hint_line(c, 4, hint)
    log_rows = 5 if c.h >= 30 else 3
    bottom = _log_and_footer(c, game, log_rows, " WASD/←↑↓→ đi · E tương tác (bếp/bàn) · P tạm dừng · H trợ giúp · Q thoát")
    my0, mh = 5, bottom - 5
    bx, bz = t["bounds"]["x"], t["bounds"]["z"]
    wu, hu = bx[1] - bx[0], bz[1] - bz[0]
    if mh < hu // 2 + 3:
        return
    sx = max(2, min(4, (c.w - 4) // (wu + 1)))
    sy = max(1, min(2, (mh - 2) // (hu + 1)))
    ox, oy = 2, my0 + 1
    bw, bh = wu * sx + 4, hu * sy + 3
    c.box(my0, 1, bw, min(bh, mh), g, "dim")
    c.put(my0, 4, " Ghe Quán ", "dim")

    def pt(pos):
        return ox + 1 + int(round((pos[0] - bx[0]) * sx)), oy + int(round((pos[1] - bz[0]) * sy))
    p = snap["player"]["pos"]
    r = t["interact_radius"]
    near = None
    ents = [("s", s) for s in snap.get("stoves") or []] + [("t", tb) for tb in snap.get("tables") or []]
    if ents:
        d_, _, near = min(((math.dist(p, e["pos"]), i, e) for i, (_, e) in enumerate(ents)), key=lambda z: (z[0], z[1]))
        if d_ > r:
            near = None
    tgt = hint.get("target")
    custs = {cu["table_id"]: cu for cu in snap.get("customers") or []}
    for s in snap.get("stoves") or []:
        x, y = pt(s["pos"])
        hot = s is near or s.get("id") == (near or {}).get("id")
        c.put(y, x - 2, f"[{s['id']}]", "rev" if hot else "stove")
        st = s.get("state")
        if st == "cooking":
            c.put(y + 1, x - 2, f"nấu {math.ceil(s['cook_ticks_left'] / TICK_HZ)}s", "warn")
        elif st == "ready":
            left = ""
            if t.get("burn_s"):
                left = f" {max(0, math.ceil(t['burn_s'] - s.get('ready_ticks', 0) / TICK_HZ))}s"
            blink = (snap["tick"] // 12) % 2 == 0
            c.put(y + 1, x - 2, ("CHÍN!" if blink else "chín!") + left, "good")
        else:
            c.put(y + 1, x - 2, "nghỉ", "dim")
        if st in ("cooking", "ready") and s.get("dish"):
            c.put(y + 2, x - 2, DISH_SHORT.get(s["dish"].get("dish_id"), "?")[:8], "dim")
    for tb in snap.get("tables") or []:
        x, y = pt(tb["pos"])
        hot = tb["id"] == (near or {}).get("id")
        c.put(y, x - 2, f"[{tb['id']}]", "rev" if hot else "table")
        cu = custs.get(tb["id"])
        if cu:
            c.put(y + 1, x - 2, f"{g['face']}{DISH_SHORT.get(cu['dish_id'], '?')}"[:11], "")
            st = cu.get("state")
            if st == "eating":
                ear = cu.get("eat_ticks_left", 0) / max(1, t["eat_s"] * TICK_HZ)
                c.put(y + 2, x - 2, "ăn " + bar(ear, 6, g), "good")
            else:
                frac = cu["patience_ticks_left"] / max(1, t["patience_s"] * TICK_HZ)
                a = "good" if frac > 0.5 else ("warn" if frac > 0.25 else "bad")
                c.put(y + 2, x - 2, bar(frac, 8, g), a)
                lab = {"reserved": "chờ nấu", "assigned": "chờ món", "unfulfillable": "hết NL!"}.get(cu.get("order_status"), "")
                c.put(y + 3, x - 2, lab, a)
    if tgt is not None:
        x, y = pt(tgt)
        c.put(y - 1, x - 1, "▼▼" if g is GLYPH_U else "vv", "hint")
    px, py = pt(p)
    c.put(py, px, "@", "player")
    if isinstance(hand, dict):
        c.put(py, px + 1, "(" + DISH_SHORT.get(hand["dish_id"], "?") + ")", "good")
    # cột đơn bên phải
    sx0 = bw + 3
    if c.w - sx0 >= 26:
        c.put(my0, sx0, "ĐƠN KHÁCH", "title")
        y = my0 + 1
        for cu in sorted(snap.get("customers") or [], key=lambda z: (z.get("order_tick", 0), z["table_id"])):
            frac = cu["patience_ticks_left"] / max(1, t["patience_s"] * TICK_HZ)
            lab = {"reserved": "chờ nấu", "assigned": "đã nấu/chờ món", "served": "đang ăn",
                   "unfulfillable": "hết nguyên liệu"}.get(cu.get("order_status"), "")
            c.put(y, sx0, f"{cu['table_id']} {dish_short(cu['dish_id'])}"[:c.w - sx0 - 1])
            c.put(y + 1, sx0, f"  {lab} {bar(frac, 6, g) if cu.get('state') == 'waiting' else ''}"[:c.w - sx0 - 1],
                  "dim")
            y += 2
            if y >= bottom - 1:
                break
        if y == my0 + 1:
            c.put(y, sx0, "(chưa có khách)", "dim")


def dish_short(d):
    return DISH_SHORT.get(d, dish_name(d))


def wrap(text, w):
    out, cur = [], ""
    for word in str(text).split():
        if len(cur) + len(word) + 1 > w:
            out.append(cur)
            cur = word
        else:
            cur = (cur + " " + word).strip()
    if cur:
        out.append(cur)
    return out


def render_intro(c, game, snap, g):
    c.put(0, 0, " " * c.w, "title")
    c.put(0, 1, "QUÁN ĂN CHỢ NỔI", "title")
    lines = []
    day = snap.get("day", 1)
    plan = snap.get("day_plan") or {}
    if snap["phase"] == "gather":
        title = f"NGÀY {day}/{game.days} — BUỔI SÁNG" if game.mode == "day" else "BUỔI SÁNG — LẶN & HÁI"
        if day == 1 or game.mode != "day":
            story = game.story["intro"]
        else:
            story = []
        story = list(story) + list((game.story.get("pre") or {}).get(day, []))
        for s in story[:10]:
            lines += [(l, "") for l in wrap(s, 70)]
        lines.append(("", ""))
        if plan.get("dishes"):
            lines.append(("Hôm nay quán bán: " + ", ".join(f"{dish_name(d)} x{n}" for d, n in plan["dishes"].items()), "good"))
            lines.append(("Cần mang về: " + ", ".join(f"{kind_name(k)} {n}" for k, n in plan["ingredients"].items()), "good"))
        lines += [("", ""),
                  ("Bơi bằng WASD; E hái bông (ở mặt nước) / cập bến; SPACE bắt cá (dưới nước).", ""),
                  ("Canh oxy! Tránh Cá Sấu. Cá để lâu sẽ ươn. Về bến (E) để mở quán buổi tối.", "")]
    else:
        title = f"NGÀY {day}/{game.days} — BUỔI TỐI: MỞ QUÁN" if game.mode == "day" else "BUỔI TỐI — MỞ QUÁN"
        lines += [(_stock_summary(snap, game.spoiled_below), "good"), ("", "")]
        lines += [(l, "") for l in wrap("Trời tối, ghe thành quán. Trường con vừa là đầu bếp vừa là người bưng.", 70)]
        lines += [("", ""), ("Cách phục vụ (đúng 3 bước):", "hint"),
                  (" 1. Đứng gần BẾP trống, bấm E: nấu món của khách chờ lâu nhất.", ""),
                  (" 2. Món CHÍN: đứng gần bếp đó, bấm E để bưng (tay chỉ cầm 1 món).", ""),
                  (" 3. Tới đúng BÀN của món đó, bấm E để giao. Khách ăn rồi trả tiền (+boa nếu còn kiên nhẫn).", ""),
                  ("", ""), ("Món để cháy sau ít giây; khách hết kiên nhẫn sẽ bỏ đi và mất uy tín.", "dim")]
    lines += [("", ""), ("Nhấn ENTER hoặc SPACE để bắt đầu.   (H: trợ giúp, Q: thoát)", "hint")]
    c.overlay(lines, g, title, "hint")


def render_result(c, game, snap, g):
    r = game.result or {"served": 0, "left": 0, "money": 0, "tip": 0, "rep": snap["reputation"], "rep_delta": 0}
    lines = [(f"Khách đã phục vụ: {r['served']}", "good"), (f"Khách bỏ đi: {r['left']}", "bad" if r["left"] else ""),
             (f"Tiền bán món: {r['money']}k + boa {r['tip']}k", ""),
             (f"Uy tín: {r['rep']:.2f} ({r['rep_delta']:+.2f})", ""), ("", ""),
             (f"Tổng tiền hiện có: {snap['money']}k   Điểm: {snap['score']}", "hint"), ("", ""),
             ("ENTER/SPACE: vào Shop", "hint")]
    c.overlay(lines, g, f"KẾT QUẢ NGÀY {snap.get('day', 1)}", "hint")


def render_shop(c, game, snap, g):
    _hud_top(c, game, snap, g)
    c.put(2, 2, f"Tiền: {snap['money']}k", "good")
    c.put(2, 24, f"Còn {fmt_time(snap['time_left_ticks'])} (Shop tự đóng khi hết giờ)", "dim")
    y = 4
    cat = snap.get("shop") or {}
    for i, uid in enumerate(sorted(cat)):
        e = cat[uid]
        nxt = e.get("next")
        head = f"[{i + 1}] {UPGRADE_VI.get(uid, uid)} — cấp {e['level']}/{e['max_level']}"
        c.put(y, 2, head, "title")
        if nxt:
            eff = ", ".join(FIELD_VI.get(k, k + " {}").format(v) for k, v in nxt.items() if k not in ("level", "price"))
            ok = snap["money"] >= nxt["price"]
            c.put(y + 1, 6, f"Lên cấp {nxt['level']}: {nxt['price']}k → {eff}  " + ("(đủ tiền, bấm số)" if ok else "(thiếu tiền)"),
                  "good" if ok else "dim")
        else:
            c.put(y + 1, 6, "Đã tối đa", "dim")
        y += 3
    c.put(y + 1, 2, "ENTER/SPACE: xong, sang Ngày kế · P: tạm dừng · H: trợ giúp", "hint")
    stock = _stock_summary(snap, game.spoiled_below)
    c.put(y + 3, 2, stock + " (kho dư bỏ sau Shop)", "dim")
    bottom = _log_and_footer(c, game, 4 if c.h >= 26 else 2, " Số 1,2: mua nâng cấp · ENTER: tiếp tục · Q thoát")


def render_summary(c, game, snap, g):
    sim = game.session.sim
    top = max(sorted(game.dish_counts), key=lambda k: game.dish_counts[k]) if game.dish_counts else None
    reason = REASON_VI.get(sim.reason, sim.reason)
    lines = [(f"Kết thúc: {reason}", "hint"), ("", ""), (f"Số Ngày hoàn thành: {getattr(sim, 'days_completed', '-')}", ""),
             (f"Tiền: {snap['money']}k   Tổng kiếm: {snap['earned']}k", ""),
             (f"Uy tín: {snap['reputation']:.2f}", ""), (f"ĐIỂM: {snap['score']}", "good"),
             (f"Món bán chạy nhất: {dish_name(top) if top else '(chưa có)'}", ""), ("", ""),
             ("R: chơi lại · Q: thoát", "hint")]
    c.overlay(lines, g, "TỔNG KẾT", "hint")


HELP_LINES = [
    ("PHÍM", "title"),
    ("W A S D / mũi tên  đi / bơi", ""),
    ("E                  tương tác: hái, cập bến, nấu, lấy món, giao món", ""),
    ("SPACE              bắt cá (buổi sáng); tiếp tục ở các màn chờ", ""),
    ("P / ESC            tạm dừng - bấm lại để tiếp tục", ""),
    ("1, 2               mua nâng cấp (Shop)   ENTER: xong Shop", ""),
    ("R                  chơi lại (chỉ khi đã kết thúc)", ""),
    ("X                  dừng hẳn (khi dùng --sticky)", ""),
    ("H                  bật/tắt trợ giúp    Q  thoát (hỏi lại)", ""),
    ("", ""),
    ("KÝ HIỆU: @ bạn · ><> cá (linh cyan, lóc xanh, kèo vàng) · * nút rau · ~Cá Sấu~", ""),
    ("Giỏ: LI cá linh, LO cá lóc, KE cá kèo, DD điên điển, BS bông súng, KN keo nèo", ""),
    ("      '+' tươi, '!' ươn (không nấu được)", ""),
    ("Ghi chú: terminal không có phím nhả - mỗi lần bấm giữ hướng ~0.2s;", "dim"),
    ("giữ phím để đi liên tục hoặc chạy với --sticky.", "dim"),
    ("", ""), ("Bấm phím bất kỳ để đóng.", "hint"),
]


def render(game, w, h, ascii_mode=False):
    g = GLYPH_A if ascii_mode else GLYPH_U
    c = Canvas(w, h)
    if w < 80 or h < 24:
        c.put(0, 0, f"Terminal quá nhỏ ({w}x{h}); cần tối thiểu 80x24.")
        return c
    snap = game.snap()
    if game.stage == "intro":
        render_intro(c, game, snap, g)
    elif game.phase == "gather":
        render_gather(c, game, snap, g)
    elif game.phase == "quan":
        render_quan(c, game, snap, g)
    elif game.phase == "shop":
        render_shop(c, game, snap, g)
    if game.stage == "result":
        render_result(c, game, snap, g)
    elif game.stage == "summary":
        render_summary(c, game, snap, g)
    if game.stage == "play" and game.paused and not game.help and not game.confirm_quit:
        c.overlay(["", "  TẠM DỪNG  ", "", "  P / ESC: tiếp tục  "], g, "", "warn")
    if game.help:
        c.overlay(HELP_LINES, g, "TRỢ GIÚP", "hint")
    if game.confirm_quit:
        c.overlay(["", "Thoát game? (Y: có / N: không)", ""], g, "THOÁT", "warn")
    return c


# ---------------------------------------------------------------------------- bot autoplay
def bot_step(game):
    """Điều khiển thử: đọc gợi ý như người chơi. Trả (move, oneshots)."""
    snap = game.snap()
    ph = game.phase
    if ph == "shop":
        cat = snap.get("shop") or {}
        for i, uid in enumerate(sorted(cat)):
            nxt = cat[uid].get("next")
            if nxt and snap["money"] >= nxt["price"]:
                return (0.0, 0.0), [("buy", uid), ("shop_done", True)]
        return (0.0, 0.0), [("shop_done", True)]
    hint = gather_hint(snap, game.tuning) if ph == "gather" else quan_hint(snap, game.tuning)
    tgt, pos = hint.get("target"), snap["player"]["pos"]
    mv = (0.0, 0.0)
    act = hint.get("act")
    if tgt is not None and not act:
        dx, dy = tgt[0] - pos[0], tgt[1] - pos[1]
        d = math.hypot(dx, dy)
        if d > 0.15:
            mv = (dx / d, dy / d)
    elif tgt is not None and act and ph == "gather" and act == "catch":
        mv = (0.0, 0.0)
    shots = [(act, True)] if act else []
    return mv, shots


def bot_tick(game):
    """Một tick của bot (kể cả bấm tiếp tục ở màn chờ)."""
    if game.stage in ("intro", "result"):
        game.key("enter")
        return
    if game.stage == "summary":
        return
    mv, shots = bot_step(game)
    game.oneshots.extend(shots)
    game.tick(move=mv)


# ---------------------------------------------------------------------------- chế độ dòng lệnh (text)
def run_text(game, args, stdin=None, out=None):
    stdin = sys.stdin if stdin is None else stdin
    out = sys.stdout if out is None else out
    try:
        out.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    asc = args.ascii
    width, height = 100, 35

    def show(label):
        out.write(f"=== {label} | tick {game.session.tick} | {game.phase} | stage {game.stage} ===\n")
        out.write(render(game, width, height, asc).to_text() + "\n")
        out.flush()
    budget = args.ticks

    def left():
        return None if budget is None else budget - game.session.tick
    show("khung đầu")
    if args.demo:
        every = max(1, args.every)
        limit = budget if budget is not None else 3600
        while game.session.tick < limit and game.stage != "summary" and not game.want_quit:
            before = game.session.tick
            bot_tick(game)
            if game.session.tick and game.session.tick % every == 0 and game.session.tick != before:
                show("demo")
        show("demo kết thúc")
        return 0
    for line in stdin:
        parts = line.strip().lower().split()
        if not parts or parts[0].startswith("#"):
            continue
        cmd, n = parts[0], (int(parts[1]) if len(parts) > 1 and parts[1].lstrip("-").isdigit() else None)
        if left() is not None and left() <= 0:
            break
        note = None
        run_n = lambda k: min(k, left()) if left() is not None else k
        if cmd in DIRS or cmd in KEYMAP_NAMES:
            if game.stage == "play":
                dname = KEYMAP_NAMES.get(cmd, cmd)
                for _ in range(run_n(n if n is not None else 10)):
                    game.tick(move=DIRS[dname])
            else:
                note = "đang ở màn chờ — gõ 'enter'"
        elif cmd in ("e", "interact"):
            game.key("e")
            game.tick(move=(0.0, 0.0))
        elif cmd in ("space", "catch"):
            game.key("space")
            game.tick(move=(0.0, 0.0))
        elif cmd in ("wait", "tick"):
            for _ in range(run_n(n if n is not None else 1)):
                game.tick(move=(0.0, 0.0))
        elif cmd in ("enter", "next", "go"):
            game.key("enter")
            if game.phase == "shop" and game.stage == "play":
                game.tick(move=(0.0, 0.0))
        elif cmd == "done":
            game.key("enter")
            game.tick(move=(0.0, 0.0))
        elif cmd == "buy":
            game.key(parts[1] if len(parts) > 1 and parts[1].isdigit() else "9")
            if len(parts) > 1 and not parts[1].isdigit() and game.phase == "shop":
                game.oneshots.append(("buy", parts[1]))
            game.tick(move=(0.0, 0.0))
        elif cmd in ("p", "pause"):
            game.key("p")
        elif cmd in ("r", "restart"):
            if game.stage == "summary":
                game.restart()
            else:
                note = "R chỉ dùng khi đã kết thúc"
        elif cmd in ("h", "help"):
            game.key("h")
        elif cmd in ("q", "quit"):
            break
        elif cmd == "bot":
            for _ in range(run_n(n if n is not None else 60)):
                bot_tick(game)
        else:
            note = f"lệnh không hiểu: {cmd}"
        show(line.strip() + (f"  ({note})" if note else ""))
        if game.stage == "summary" and cmd not in ("r", "restart"):
            pass
    sim = game.session.sim
    out.write(f"--- kết thúc: tick={game.session.tick} pha={game.phase} tiền={game.session.snapshot()['money']} "
              f"xong={game.session.done}\n")
    return 0


# ---------------------------------------------------------------------------- curses
def run_curses(game, args):
    import curses
    import locale
    locale.setlocale(locale.LC_ALL, "")
    os.environ.setdefault("ESCDELAY", "25")
    ascii_mode = args.ascii or "utf" not in (locale.getpreferredencoding(False) or "").lower()

    def main(stdscr):
        try:
            curses.curs_set(0)
        except curses.error:
            pass
        stdscr.nodelay(True)
        stdscr.keypad(True)
        attrs = _init_attrs(curses)
        start = time.perf_counter()
        prev = start
        acc = 0.0
        demo_frames = 0
        while not game.want_quit:
            now = time.perf_counter()
            while True:
                k = stdscr.getch()
                if k == -1:
                    break
                name = _key_name(curses, k)
                if name and not args.demo:
                    game.key(name, now)
                elif name == "q":
                    game.want_quit = True
            acc += (now - prev) * args.speed
            prev = now
            n = min(int(acc * TICK_HZ), 20 * max(1, int(args.speed)))
            acc -= n / TICK_HZ
            if args.demo:
                for _ in range(n):
                    bot_tick(game)
                if game.stage in ("intro", "result"):
                    demo_frames += 1
                if now - start >= args.demo_seconds or game.stage == "summary" and now - start > 1.5:
                    game.want_quit = True
            else:
                for _ in range(n):
                    if not game.tick(now):
                        break
            h, w = stdscr.getmaxyx()
            cv = render(game, w, h, ascii_mode)
            stdscr.erase()
            for y in range(h):
                for x, txt, at in cv.runs(y):
                    if not txt.strip() and not at:
                        continue
                    if y == h - 1 and x + len(txt) >= w:
                        txt = txt[:max(0, w - x - 1)]
                    try:
                        stdscr.addstr(y, x, txt, attrs.get(at, 0))
                    except curses.error:
                        pass
            stdscr.refresh()
            sleep = (1.0 / FPS) - (time.perf_counter() - now)
            if sleep > 0:
                time.sleep(sleep)
    curses.wrapper(main)
    return 0


def _key_name(curses, k):
    if k == curses.KEY_UP:
        return "w"
    if k == curses.KEY_DOWN:
        return "s"
    if k == curses.KEY_LEFT:
        return "a"
    if k == curses.KEY_RIGHT:
        return "d"
    if k in (10, 13, curses.KEY_ENTER):
        return "enter"
    if k == 27:
        return "esc"
    if k == 32:
        return "space"
    if k == curses.KEY_RESIZE:
        return None
    if 0 <= k < 256:
        return chr(k).lower()
    return None


def _init_attrs(curses):
    m = {"": 0, "dim": curses.A_DIM, "rev": curses.A_REVERSE, "title": curses.A_BOLD | curses.A_REVERSE,
         "hint": curses.A_BOLD, "hintt": curses.A_BOLD, "good": curses.A_BOLD, "bad": curses.A_BOLD,
         "warn": curses.A_BOLD, "player": curses.A_BOLD, "log": 0}
    if not curses.has_colors():
        return m
    curses.start_color()
    try:
        curses.use_default_colors()
        bg = -1
    except curses.error:
        bg = curses.COLOR_BLACK
    spec = {"title": (curses.COLOR_BLACK, curses.COLOR_CYAN), "hint": (curses.COLOR_YELLOW, bg),
            "hintt": (curses.COLOR_WHITE, bg), "good": (curses.COLOR_GREEN, bg), "bad": (curses.COLOR_RED, bg),
            "warn": (curses.COLOR_YELLOW, bg), "water": (curses.COLOR_BLUE, bg), "node": (curses.COLOR_GREEN, bg),
            "dock": (curses.COLOR_YELLOW, bg), "f_linh": (curses.COLOR_CYAN, bg), "f_loc": (curses.COLOR_GREEN, bg),
            "f_keo": (curses.COLOR_YELLOW, bg), "monster": (curses.COLOR_MAGENTA, bg),
            "player": (curses.COLOR_WHITE, bg), "table": (curses.COLOR_CYAN, bg), "stove": (curses.COLOR_RED, bg),
            "log": (curses.COLOR_WHITE, bg)}
    for i, (name, (fg, b)) in enumerate(spec.items(), 1):
        try:
            curses.init_pair(i, fg, b)
            extra = curses.A_BOLD if name in ("hint", "player", "bad", "good", "title") else 0
            m[name] = curses.color_pair(i) | extra
        except curses.error:
            pass
    return m


# ---------------------------------------------------------------------------- CLI
class _Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        sys.stderr.write(f"lỗi: {message}\n")
        sys.exit(2)


def main(argv=None) -> int:
    p = _Parser(prog="chonoi.play", description="Chơi Quán Ăn Chợ Nổi trong terminal.")
    p.add_argument("--mode", default="day", choices=["gather", "quan", "day"])
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--days", type=int, default=None, help="chỉ với day: 1-5 (mặc định 1)")
    p.add_argument("--scenario")
    p.add_argument("--demo", action="store_true", help="bot tự chơi vài giây (smoke test)")
    p.add_argument("--demo-seconds", type=float, default=8.0)
    p.add_argument("--text", action="store_true", help="chế độ dòng lệnh: đọc lệnh từ stdin, in từng khung")
    p.add_argument("--ticks", type=int, default=None, help="chế độ text: tổng số tick tối đa")
    p.add_argument("--every", type=int, default=300, help="text --demo: in khung mỗi N tick")
    p.add_argument("--ascii", action="store_true", help="chỉ ký tự ASCII")
    p.add_argument("--sticky", action="store_true", help="hướng đi giữ tới khi bấm X / hướng khác")
    p.add_argument("--speed", type=float, default=None, help="nhân tốc độ thời gian (mặc định 1; demo 12)")
    a = p.parse_args(argv)
    try:
        if a.days is not None and a.mode != "day":
            raise BadInput("--days chỉ dùng với --mode day")
        days = 1 if a.days is None else a.days
        if not (1 <= days <= 5):
            raise BadInput("--days phải là số nguyên từ 1 đến 5")
        if a.ticks is not None and a.ticks < 0:
            raise BadInput("--ticks phải >= 0")
        game = Game(a.mode, days, a.seed, a.scenario)
    except BadInput as e:
        sys.stderr.write(f"đầu vào sai: {e}\n")
        return 2
    game.sticky = a.sticky
    if a.speed is None:
        a.speed = 12.0 if a.demo else 1.0
    if a.speed <= 0:
        sys.stderr.write("đầu vào sai: --speed phải > 0\n")
        return 2
    use_curses = not a.text and sys.stdin.isatty() and sys.stdout.isatty()
    if use_curses:
        try:
            import curses
            curses.setupterm()
        except Exception:
            use_curses = False
    if not use_curses:
        return run_text(game, a)
    return run_curses(game, a)


if __name__ == "__main__":
    sys.exit(main())
