"""Đóng gói bản chạy được cho GitHub Release.

    python3 tools/package.py [--version 1.0.0] [--out dist]

Tạo `<out>/chonoi-v<version>.zip` (thư mục gốc trong zip: `chonoi-v<version>/`).
Chỉ gồm mã chạy, test, tài liệu cần đọc; bỏ `__pycache__`, `*.bak`, `*.pyc`, `*.jsonl`,
`.git`, `.env*`. Chạy thử sau khi giải nén: `python3 -m chonoi.live --help`.
"""
import argparse, os, sys, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INCLUDE = ["chonoi", "tests", "tools", "docs", "game.contract.json", "README.md",
           "CHANGELOG.md", "CREDITS.md", "TEAM.md", "AGENTS.md"]
SKIP_DIRS = {"__pycache__", ".git", ".pytest_cache"}
SKIP_SUFFIX = (".pyc", ".bak", ".jsonl")
KEEP = ("tests/fixtures/",)  # fixture .jsonl vẫn giữ


def skip(rel):
    parts = rel.split("/")
    if any(p in SKIP_DIRS or p.startswith(".env") for p in parts):
        return True
    if rel.endswith(SKIP_SUFFIX) and not rel.startswith(KEEP):
        return True
    return False


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--version", default="1.0.0")
    ap.add_argument("--out", default="dist")
    a = ap.parse_args(argv)
    out_dir = a.out if os.path.isabs(a.out) else os.path.join(ROOT, a.out)
    os.makedirs(out_dir, exist_ok=True)
    top = f"chonoi-v{a.version}"
    path = os.path.join(out_dir, top + ".zip")
    n = 0
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for item in INCLUDE:
            full = os.path.join(ROOT, item)
            if os.path.isfile(full):
                z.write(full, f"{top}/{item}"); n += 1
                continue
            for d, dirs, files in os.walk(full):
                dirs.sort()
                for f in sorted(files):
                    rel = os.path.relpath(os.path.join(d, f), ROOT).replace(os.sep, "/")
                    if not skip(rel):
                        z.write(os.path.join(ROOT, rel), f"{top}/{rel}"); n += 1
    print(f"{path} ({n} file)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
