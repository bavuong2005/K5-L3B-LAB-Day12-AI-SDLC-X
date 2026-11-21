"""Mở rộng `leaderboard`: bảng xếp hạng cục bộ top 10, lưu file JSON.

Store: {"entries":[{"name","score","days_completed","seed"}, ...]} luôn đã sắp (điểm giảm dần, hòa thì mục
ghi trước đứng trước), nên thứ tự hòa giữ nguyên sau khi mở lại. Chỉ chạy khi người dùng truyền cờ
(`--leaderboard` + `--player-name`, hoặc `--export-leaderboard`); mặc định không đụng gì.
"""

import json
import os

from .errors import BadInput

TOP = 10
DEFAULT_STORE = "leaderboard.json"
_KEYS = ("name", "score", "days_completed", "seed")


def _entry(e):
    if not isinstance(e, dict):
        raise BadInput("leaderboard: mục phải là object")
    name = e.get("name")
    if not isinstance(name, str) or not name.strip():
        raise BadInput("leaderboard: name phải là chuỗi khác rỗng")
    for k in ("score", "days_completed", "seed"):
        if isinstance(e.get(k), bool) or not isinstance(e.get(k), (int, float)):
            raise BadInput(f"leaderboard: {k} phải là số")
    return {k: e[k] for k in _KEYS}


def load(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as ex:
        raise BadInput(f"leaderboard: không đọc được {path}: {ex}")
    if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
        raise BadInput("leaderboard: store phải có mảng entries")
    return [_entry(e) for e in data["entries"]]


def _save(path, entries):
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"entries": entries}, f, ensure_ascii=False)
    os.replace(tmp, path)


def add(path, name, score, days_completed, seed):
    """Thêm một mục, giữ top 10 (chèn sau các mục cùng điểm). Trả bảng mới."""
    new = _entry({"name": name, "score": score, "days_completed": days_completed, "seed": seed})
    entries = load(path)
    i = len(entries)
    while i > 0 and entries[i - 1]["score"] < new["score"]:
        i -= 1
    entries.insert(i, new)
    entries = entries[:TOP]
    _save(path, entries)
    return entries


def export_entries(store):
    """Top 10 đã sắp, đọc từ store (cho UI)."""
    return sorted(load(store), key=lambda e: -e["score"])[:TOP]


def export(store, out):
    entries = sorted(load(store), key=lambda e: -e["score"])  # sort ổn định: giữ thứ tự ghi khi hòa
    _save(out, entries[:TOP])
    return entries[:TOP]


def handle_export(argv, prog_error):
    """Nếu argv có --export-leaderboard thì xuất rồi trả mã thoát; ngược lại None (chạy bình thường)."""
    argv = list(argv)
    if "--export-leaderboard" not in argv:
        return None
    import sys
    vals = {}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("--export-leaderboard", "--leaderboard") and i + 1 < len(argv):
            vals[a] = argv[i + 1]
            i += 2
        else:
            i += 1
    try:
        if "--export-leaderboard" not in vals:
            raise BadInput("--export-leaderboard cần đường dẫn")
        if len(argv) != 2 * len(vals):
            raise BadInput("--export-leaderboard chỉ đi cùng --leaderboard")
        export(vals.get("--leaderboard", DEFAULT_STORE), vals["--export-leaderboard"])
    except BadInput as e:
        sys.stderr.write(f"đầu vào sai: {e}\n")
        return 2
    except OSError as e:
        sys.stderr.write(f"lỗi ghi: {e}\n")
        return 1
    return 0
