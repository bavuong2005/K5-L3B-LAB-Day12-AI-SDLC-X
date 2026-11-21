"""Đọc game.contract.json và kiểm dải hợp lệ của tuning P1 (PRD mục 13.2, Test Contract)."""

import json
import os

from .errors import BadInput

DEFAULT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game.contract.json")


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _between(name, v, lo, hi):
    if not _num(v) or not (lo <= v <= hi):
        raise BadInput(f"tuning.{name} phải trong [{lo}, {hi}], đang là {v!r}")


def load_contract(path=DEFAULT_PATH) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            c = json.load(f)
    except (OSError, ValueError) as e:
        raise BadInput(f"không đọc được {path}: {e}")
    validate_tuning(c.get("tuning"), burn_enabled="burn" in c.get("extensions", []))
    return c


def _int_between(name, v, lo, hi):
    if isinstance(v, bool) or not isinstance(v, int) or not (lo <= v <= hi):
        raise BadInput(f"tuning.{name} phải là số nguyên trong [{lo}, {hi}], đang là {v!r}")


def _pos_in(name, pos, bounds, keys):
    if (not isinstance(pos, list) or len(pos) != 2 or not all(_num(c) for c in pos)):
        raise BadInput(f"tuning.{name} phải là [số, số]")
    for c, k in zip(pos, keys):
        lo, hi = bounds[k]
        if not (lo <= c <= hi):
            raise BadInput(f"tuning.{name} nằm ngoài vùng {k} ∈ [{lo}, {hi}]")


def _bounds(name, b, keys):
    if not isinstance(b, dict) or set(b) != set(keys):
        raise BadInput(f"tuning.{name}.bounds phải có đúng khóa {list(keys)}")
    for k in keys:
        v = b[k]
        if not (isinstance(v, list) and len(v) == 2 and all(_num(c) for c in v) and v[0] == 0 and v[1] > 0):
            raise BadInput(f"tuning.{name}.bounds.{k} phải là [0, số dương]")


def _validate_gather(g):
    """Dải hợp lệ P1 theo PRD mục 13.2."""
    _between("gather.duration_s", g.get("duration_s"), 60, 600)
    _bounds("gather", g.get("bounds"), ("x", "d"))
    b = g["bounds"]
    _between("gather.dock_radius", g.get("dock_radius"), 0.5, 5)
    _between("gather.interact_radius", g.get("interact_radius"), 0.5, 5)
    _between("gather.catch_radius", g.get("catch_radius"), 0.5, 5)
    _between("gather.swim_speed", g.get("swim_speed"), 1, 10)
    _between("gather.catch_cooldown_s", g.get("catch_cooldown_s"), 0, 10)
    _between("gather.oxygen_max_s", g.get("oxygen_max_s"), 10, 120)
    _int_between("gather.ramp_max_ticks", g.get("ramp_max_ticks"), 0, 6)
    _int_between("gather.hold_capacity", g.get("hold_capacity"), 4, 30)
    _int_between("gather.hp_max", g.get("hp_max"), 1, 99)
    _int_between("gather.oxygen_refill_per_tick", g.get("oxygen_refill_per_tick"), 1, 10_000)
    _int_between("gather.choke_interval_ticks", g.get("choke_interval_ticks"), 1, 10_000)
    _int_between("gather.node_yield", g.get("node_yield"), 1, 12)
    _between("gather.regrow_s", g.get("regrow_s"), 0.1, 600)
    _between("gather.surface_depth", g.get("surface_depth"), 0, 5)
    _pos_in("gather.dock_pos", g.get("dock_pos"), b, ("x", "d"))
    _pos_in("gather.start_pos", g.get("start_pos"), b, ("x", "d"))
    if not _num(g.get("start_heading_deg")):
        raise BadInput("tuning.gather.start_heading_deg phải là số")
    fy = g.get("fish_yield")
    if not isinstance(fy, dict) or not {"ca_linh", "ca_loc"} <= set(fy):
        raise BadInput("tuning.gather.fish_yield phải có ca_linh và ca_loc")
    for k, v in fy.items():
        _int_between(f"gather.fish_yield.{k}", v, 1, g["hold_capacity"])
    nodes = g.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise BadInput("tuning.gather.nodes phải là mảng không rỗng")
    seen, kinds = set(), set()
    for n in nodes:
        if not isinstance(n, dict) or not isinstance(n.get("id"), str) or n["id"] in seen:
            raise BadInput("tuning.gather.nodes: mỗi nút cần id duy nhất")
        seen.add(n["id"])
        if n.get("kind") not in ("bong_dien_dien", "bong_sung", "keo_neo"):
            raise BadInput(f"tuning.gather.nodes.{n['id']}: kind phải là bong_dien_dien, bong_sung hoặc keo_neo")
        kinds.add(n["kind"])
        _pos_in(f"gather.nodes.{n['id']}.pos", n.get("pos"), b, ("x", "d"))
        if n["pos"][1] != 0:
            raise BadInput(f"tuning.gather.nodes.{n['id']}: nút hái nằm ở mặt nước (d = 0)")
    if not {"bong_dien_dien", "bong_sung"} <= kinds:
        raise BadInput("tuning.gather.nodes phải có ít nhất một nút bong_dien_dien và một nút bong_sung")
    fish = g.get("fish_initial")
    if isinstance(fish, int) and not isinstance(fish, bool):
        _validate_fish_v11(g, fish, fy)
    elif not isinstance(fish, list) or len(fish) != 6:
        raise BadInput("tuning.gather.fish_initial phải là số đàn (v1.1) hoặc danh sách đúng 6 đàn (v1.0)")
    else:
        seen = set()
        for f in fish:
            if not isinstance(f, dict) or not isinstance(f.get("id"), str) or f["id"] in seen:
                raise BadInput("tuning.gather.fish_initial: mỗi đàn cần id duy nhất")
            seen.add(f["id"])
            if f.get("kind") not in fy:
                raise BadInput(f"tuning.gather.fish_initial.{f['id']}: kind phải thuộc fish_yield")
            _pos_in(f"gather.fish_initial.{f['id']}.pos", f.get("pos"), b, ("x", "d"))
            if f["pos"][1] <= g["surface_depth"]:
                raise BadInput(f"tuning.gather.fish_initial.{f['id']}: đàn cá phải ở dưới nước")


def _validate_fish_v11(g, count, fy):
    """TICKET-02 §4.1: fish_initial là số, đủ khóa cá bơi/sinh và 3 loài."""
    if "ca_keo" not in fy:
        raise BadInput("tuning.gather.fish_yield v1.1 phải có ca_keo")
    _int_between("gather.fish_initial", count, 1, 12)
    _between("gather.fish_speed", g.get("fish_speed"), 0.1, 10)
    _int_between("gather.fish_turn_ticks", g.get("fish_turn_ticks"), 1, 10_000)
    _int_between("gather.fish_max", g.get("fish_max"), count, 30)
    _int_between("gather.fish_spawn_ticks", g.get("fish_spawn_ticks"), 1, 10_000)
    _between("gather.fish_spawn_clearance", g.get("fish_spawn_clearance"), 0, 30)
    xspan = g.get("fish_x")
    if not (isinstance(xspan, list) and len(xspan) == 2 and xspan[0] < xspan[1]):
        raise BadInput("tuning.gather.fish_x phải là [min, max]")
    xs = g.get("fish_spawn_x")
    if not isinstance(xs, list) or not xs:
        raise BadInput("tuning.gather.fish_spawn_x phải là mảng x")
    for name in ("fish_depths", "fish_spawn_depths", "fish_weights"):
        block = g.get(name)
        if not isinstance(block, dict) or set(block) != {"ca_linh", "ca_loc", "ca_keo"}:
            raise BadInput(f"tuning.gather.{name} phải có đủ ca_linh, ca_loc, ca_keo")
    monsters = g.get("monsters")
    if not isinstance(monsters, dict) or "spawns" not in monsters:
        raise BadInput("tuning.gather.monsters phải có spawns (v1.1)")


def _validate_day_and_shop(t, menu):
    """TICKET-02 §2 và §4.1: day_plan khớp công thức, shop có oxygen/hp."""
    plans = t.get("day_plan")
    if not isinstance(plans, list) or len(plans) != 5:
        raise BadInput("tuning.day_plan phải là mảng 5 ngày")
    from .sim.day import plan_ingredients
    seen = set()
    for i, p in enumerate(plans):
        if not isinstance(p, dict) or "day" not in p or "dishes" not in p:
            raise BadInput(f"tuning.day_plan[{i}] cần day và dishes")
        day = p["day"]
        if day in seen or not isinstance(day, int) or not 1 <= day <= 5:
            raise BadInput(f"tuning.day_plan[{i}].day phải là số 1–5, không trùng")
        seen.add(day)
        got = plan_ingredients(menu, p["dishes"])
        if p.get("ingredients") != got:
            raise BadInput(f"tuning.day_plan ngày {day}: ingredients phải bằng Σ công thức × suất ({got})")
    shop = t.get("shop")
    if not isinstance(shop, dict) or not isinstance(shop.get("upgrades"), dict):
        raise BadInput("tuning.shop phải có upgrades")
    _int_between("shop.max_ticks", shop.get("max_ticks"), 1, 10_000)
    for uid, key in (("oxygen", "oxygen_max_s"), ("hp", "hp_max")):
        levels = shop["upgrades"].get(uid)
        if not isinstance(levels, list) or not levels:
            raise BadInput(f"tuning.shop.upgrades.{uid} phải là mảng cấp")
        for lv in levels:
            if not isinstance(lv, dict) or "level" not in lv or "price" not in lv or key not in lv:
                raise BadInput(f"tuning.shop.upgrades.{uid}: mỗi cấp cần level, price, {key}")


def _validate_freshness(t):
    """TICKET-03: freshness trong tuning. decay × 240 / tick_hz phải là số nguyên."""
    fr = t.get("freshness")
    if not isinstance(fr, dict):
        raise BadInput("tuning.freshness phải là object")
    _between("freshness.initial", fr.get("initial"), 0, 100)
    _between("freshness.gather_decay_per_s", fr.get("gather_decay_per_s"), 0, 100)
    _between("freshness.quan_decay_per_s", fr.get("quan_decay_per_s"), 0, 100)
    _between("freshness.spoiled_below", fr.get("spoiled_below"), 0, 100)
    hz = t.get("tick_hz", 60)
    if isinstance(hz, bool) or not isinstance(hz, int) or hz <= 0:
        raise BadInput("tuning.tick_hz phải là số nguyên dương")
    for key in ("gather_decay_per_s", "quan_decay_per_s"):
        units = fr[key] * 240 / hz
        if abs(units - round(units)) > 1e-6:
            raise BadInput(f"tuning.freshness.{key} × 240 / tick_hz phải là số nguyên")


def validate_tuning(t, *, burn_enabled=False):
    if not isinstance(t, dict):
        raise BadInput("thiếu khối tuning")
    g, q, menu = t.get("gather"), t.get("quan"), t.get("menu")
    if not isinstance(g, dict) or not isinstance(q, dict) or not isinstance(menu, dict):
        raise BadInput("tuning phải có gather, quan, menu")
    _validate_gather(g)
    # Quán: dải hợp lệ P1 (PRD mục 13.2)
    _between("quan.duration_s", q.get("duration_s"), 60, 600)
    _bounds("quan", q.get("bounds"), ("x", "z"))
    _between("quan.patience_s", q.get("patience_s"), 20, 180)
    _between("quan.walk_speed", q.get("walk_speed"), 1, 10)
    _between("quan.interact_radius", q.get("interact_radius"), 0.5, 5)
    _int_between("quan.ramp_max_ticks", q.get("ramp_max_ticks", 6), 0, 6)
    _between("quan.eat_s", q.get("eat_s"), 0.1, 600)
    _between("quan.customer_interval_s", q.get("customer_interval_s"), 0.1, 600)
    _int_between("quan.first_customer_tick", q.get("first_customer_tick"), 1, int(q["duration_s"] * 60) - 1)
    if not (_num(q.get("tip_rate")) and q["tip_rate"] > 0 and _num(q.get("left_reputation_delta"))
            and q["left_reputation_delta"] < 0):
        raise BadInput("tip_rate phải > 0 và left_reputation_delta phải < 0")
    ratio = q.get("tip_min_patience_ratio")
    if not (_num(ratio) and 0 < ratio <= 1):
        raise BadInput("quan.tip_min_patience_ratio phải thuộc (0, 1]")
    if not (_num(q.get("tip_reputation")) and q["tip_reputation"] > 0):
        raise BadInput("quan.tip_reputation phải > 0")
    if burn_enabled:
        _between("quan.burn_s", q.get("burn_s"), 20, 20)
    elif q.get("burn_s") is not None:
        raise BadInput("burn_s phải là null ở lõi (cháy món là mở rộng)")
    if isinstance(g.get("fish_initial"), int):
        _validate_day_and_shop(t, menu)
    if "freshness" in t:
        _validate_freshness(t)
    # TODO(nhóm): bổ sung kiểm các khóa còn lại nếu muốn chặt hơn (bếp/bàn, uy tín, ...).
    for dish_id, d in menu.items():
        price, cook = d.get("price"), d.get("cook_s")
        if isinstance(price, bool) or not isinstance(price, int) or price <= 0 or not _num(cook) or cook <= 0:
            raise BadInput(f"menu.{dish_id}: price (nguyên) và cook_s phải > 0")
