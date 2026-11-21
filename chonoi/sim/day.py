"""Vòng Ngày `--mode day` (Test Contract v1.1, đề §2, §4.3–4.5). TV6, T243; v1.2 T330–T331.

Máy trạng thái pha: gather --gather_end--> quan --quan_end--> shop --shop_end--> (days_completed+1)
--> gather (Ngày kế) | kết thúc (reason `days_complete`).

- Đầu Ngày: `day_start {}` → `day_plan {dishes, ingredients}` → `phase_start {}` (pha gather).
- Sim con kết thúc: event kết thúc mang PHA CŨ; dựng pha mới và phát `phase_start` CÙNG tick
  (kể cả ngất: kho rỗng). Pha mới chạy gameplay từ bước sau. Runner ghi snapshot đổi pha với `phase_tick:0`.
- Kho bàn giao gather → quan trong bộ nhớ (`GatherSim.inventory_items()` — đếm v1.0/v1.1; cá thể v1.2 khi TV2 sẵn).
  Cùng tick chuyển pha: không gọi `child.step` → không hao thêm; quán chạy từ bước sau (T330).
- v1.2 (T331): id tăng xuyên Ngày; Ngày 1 giữ id mẫu `gather.hold`; Ngày kế cấp id mới (kind/fresh ban đầu);
  Shop `stock` cá thể không hao.
- Giữ qua Ngày: money, earned, uy tín, cấp. Mỗi Ngày dựng GatherSim/QuanSim mới từ mẫu scenario;
  oxy/Máu đầy theo `active_upgrades` (áp các trường của mục cấp lên bản sao `tuning.gather`), giỏ mới,
  kho dư bỏ sau Shop.
- Một `Streams` và một `IdAllocator` cho cả lượt chạy (GIẢ ĐỊNH, spec Clarifications).

Gọi GatherSim/QuanSim CHỈ qua giao diện hiện có (tuning, scenario, streams, ids[, inventory]). Nếu sim con
có tham số ngữ cảnh Ngày (T246 của TV2: `day`, `active_upgrades`; T230 của TV3: `plan_dishes`) thì truyền
qua `_kwargs_for`; chưa có thì dùng đường dự phòng bằng dữ liệu (bản sao tuning đã lọc).
"""

import copy
import inspect

from ..errors import BadInput
from .gather import GatherSim
from .quan import QuanSim
from .shop import ShopSim, upgrade_entry

UPGRADE_META_KEYS = ("level", "price")


def plan_ingredients(menu, dishes) -> dict:
    """ingredients = Σ công thức × số suất, theo thứ tự món rồi thứ tự công thức (khớp dòng mẫu đề §4.4)."""
    out = {}
    for dish_id, n in dishes.items():
        if dish_id not in menu:
            raise BadInput(f"day_plan: món không có trong menu: {dish_id}")
        for kind, q in menu[dish_id]["recipe"].items():
            out[kind] = out.get(kind, 0) + q * n
    return out


def missing_day_keys(tuning) -> list:
    """Khóa contract v1.1 mà mode day cần (của TV1, T210). Rỗng = đủ."""
    miss = []
    if not isinstance(tuning.get("day_plan"), list):
        miss.append("tuning.day_plan")
    shop = tuning.get("shop")
    if not isinstance(shop, dict):
        miss.append("tuning.shop")
    else:
        if "max_ticks" not in shop:
            miss.append("tuning.shop.max_ticks")
        if not isinstance(shop.get("upgrades"), dict):
            miss.append("tuning.shop.upgrades")
    return miss


def _kwargs_for(cls, **candidates) -> dict:
    params = inspect.signature(cls.__init__).parameters
    return {k: v for k, v in candidates.items() if k in params}


class DayState:
    def __init__(self, tuning, block):
        self.money = block.get("money", 0)
        self.earned = block.get("earned", 0)
        self.reputation = block.get("reputation", tuning["quan"]["reputation_initial"])
        self.upgrades = dict(block.get("upgrades", {}))
        self.active_upgrades = {}
        self.days_completed = 0


class DaySim:
    mode = "day"

    def __init__(self, tuning, scenario, streams, ids, days=1, version=None):
        miss = missing_day_keys(tuning)
        if miss:
            raise BadInput(f"contract chưa có khóa {', '.join(miss)} (chờ TV1)")
        self.tuning = tuning
        self.streams = streams
        self.ids = ids
        self.days = days
        self.version = version
        self.tpl_gather = scenario.get("gather", {})
        self.tpl_quan = scenario.get("quan", {})
        block = scenario.get("day", {})
        self.state = DayState(tuning, block)
        self.plan_override = {p["day"]: p for p in block.get("day_plan", [])}
        self.day = 0
        self.day_plan = None
        self.phase = None
        self.child = None
        self.done = False
        self.reason = None
        self.phase_changed = False
        self._pending = []
        self._start_day(1, self._pending)  # sự kiện tick 0, runner lấy qua initial_events()

    # --- giao diện cho runner ---------------------------------------------------
    def initial_events(self):
        out, self._pending = self._pending, []
        return out

    @property
    def time_left_ticks(self):
        return self.child.time_left_ticks

    @property
    def money(self):
        return self.state.money + (self.child.money if self.phase == "quan" else 0)

    @property
    def earned(self):
        return self.state.earned + (self.child.earned if self.phase == "quan" else 0)

    @property
    def reputation(self):
        return self.child.reputation if self.phase == "quan" else self.state.reputation

    @property
    def days_completed(self):
        return self.state.days_completed

    def snapshot(self) -> dict:
        s = {"day": self.day, "day_plan": copy.deepcopy(self.day_plan),
             "upgrades": dict(sorted(self.state.upgrades.items())),
             "active_upgrades": dict(sorted(self.state.active_upgrades.items())),
             "days_completed": self.state.days_completed}
        s.update(self.child.snapshot())
        return s

    def step(self, inp):
        """Một bước gameplay; trả [(name, data, phase, day)]."""
        self.phase_changed = False
        out = [(n, d, self.phase, self.day) for n, d in self.child.step(inp)]
        if self.child.done:
            self._advance(out)
        return out

    # --- đổi pha ----------------------------------------------------------------
    def _emit(self, out, name, data=None):
        out.append((name, {} if data is None else data, self.phase, self.day))

    def _plan_for(self, n):
        src = self.plan_override.get(n)
        if src is None:
            # D1–D5 lặp lại từ Ngày 6 (TICKET-04 soak). Ngày 1–5 vẫn trúng đúng mục.
            cycle = ((n - 1) % 5) + 1
            src = next((p for p in self.tuning["day_plan"] if p.get("day") == cycle), None)
        if src is None:
            raise BadInput(f"day_plan không có mục cho Ngày {n}")
        dishes = dict(src["dishes"])
        return {"dishes": dishes, "ingredients": plan_ingredients(self.tuning["menu"], dishes)}

    def _start_day(self, n, out):
        self.day = n
        self.state.active_upgrades = dict(self.state.upgrades)  # chỉ khi dựng Ngày mới
        self.day_plan = self._plan_for(n)
        self.phase = "gather"
        self._emit(out, "day_start")
        self._emit(out, "day_plan", copy.deepcopy(self.day_plan))
        self.child = self._build_gather()
        self._emit(out, "phase_start")
        self.phase_changed = True

    def _gather_tuning(self):
        """Bản sao tuning cho Ngày: áp cấp hiệu lực (vd. oxygen_max_s, hp_max) lên tuning.gather."""
        t = dict(self.tuning)
        g = copy.deepcopy(self.tuning["gather"])
        for uid in sorted(self.state.active_upgrades):
            e = upgrade_entry(self.tuning["shop"], uid, self.state.active_upgrades[uid])
            if e:
                for k, v in e.items():
                    if k not in UPGRADE_META_KEYS:
                        g[k] = v
        t["gather"] = g
        return t

    def _hold_is_individuals(self, hold) -> bool:
        return isinstance(hold, list) and hold and isinstance(hold[0], dict) and "id" in hold[0]

    def _gather_scenario_for_day(self):
        """Mẫu gather của Ngày hiện tại. v1.2: Ngày 1 giữ id mẫu; Ngày kế cấp id mới (T331).

        `version` None (gọi DaySim thẳng, không qua runner) thì suy từ hình dạng `hold` cá thể.
        Session/headless/soak truyền `contract_version` của file contract.
        """
        sc = copy.deepcopy(self.tpl_gather)
        hold = sc.get("hold")
        if not self._hold_is_individuals(hold):
            return sc
        if self.version is not None:
            from ..inventory import uses_individuals
            if not uses_individuals(self.version):
                return sc
        if self.day <= 1:
            for it in hold:
                self.ids.reserve(it["id"])
        else:
            for it in hold:
                it["id"] = self.ids.new("I")  # kind/fresh ban đầu giữ nguyên từ mẫu
        return sc

    def _build_gather(self):
        t = self._gather_tuning()
        # Chỉ truyền contract_version khi runner đã có (None = gọi thẳng, suy từ hold). Không truyền item_ids —
        # `should_use_freshness(..., item_ids=...)` sẽ ép v1.2 cả khi hold còn dạng đếm.
        cand = {"day": self.day, "active_upgrades": dict(self.state.active_upgrades)}
        if self.version is not None:
            cand["contract_version"] = self.version
        kw = _kwargs_for(GatherSim, **cand)
        mons = t["gather"].get("monsters")
        if "day" not in kw and isinstance(mons, dict) and isinstance(mons.get("spawns"), list):
            # Dự phòng tới khi có T246: sim con coi như Ngày 1 → lọc sẵn spawns theo from_day của Ngày thật.
            mons = dict(mons)
            mons["spawns"] = [dict(sp, from_day=1) for sp in mons["spawns"] if sp.get("from_day", 1) <= self.day]
            t["gather"]["monsters"] = mons
        return GatherSim(t, self._gather_scenario_for_day(), self.streams, self.ids, **kw)

    def _build_quan(self, inventory):
        sc = copy.deepcopy(self.tpl_quan)
        sc["reputation"] = self.state.reputation  # uy tín xuyên Ngày (scenario day cấm quan.reputation)
        dishes = list(self.day_plan["dishes"])
        kw = _kwargs_for(QuanSim, plan_dishes=dishes)
        t = self.tuning
        if "plan_dishes" not in kw:
            # Dự phòng tới khi có T230: lọc menu theo kế hoạch TRƯỚC khi quán lọc nguyên liệu.
            t = dict(self.tuning)
            t["menu"] = {k: v for k, v in self.tuning["menu"].items() if k in self.day_plan["dishes"]}
        return QuanSim(t, sc, self.streams, self.ids, inventory=inventory, **kw)

    def _advance(self, out):
        """Đổi pha CÙNG tick với event kết thúc; không gọi child.step → không hao thêm (T330)."""
        old = self.child
        if self.phase == "gather":
            inv = old.inventory_items()  # ngất → giỏ đã xóa → {} hoặc [] (v1.2)
            if isinstance(inv, list):
                inv = [dict(it) for it in inv]
            self.phase = "quan"
            self.child = self._build_quan(inv)
            self._emit(out, "phase_start")
            self.phase_changed = True
        elif self.phase == "quan":
            st = self.state
            st.money += old.money
            st.earned += old.earned
            st.reputation = old.reputation
            self.phase = "shop"
            stock = getattr(old, "stock", {})
            if isinstance(stock, list):
                stock = [dict(it) for it in stock]  # cá thể dư → Shop không hao (T331)
            self.child = ShopSim(self.tuning["shop"], st, stock)
            self._emit(out, "phase_start")
            self.phase_changed = True
        else:  # shop đóng → Ngày hoàn tất
            self.state.days_completed += 1
            if self.state.days_completed >= self.days:
                self.done = True
                self.reason = "days_complete"
            else:
                self._start_day(self.day + 1, out)
