#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import datetime
import os
import re
import sys as _sys

# Python 2/3 compatibility: define 'unicode' on Py3
try:  # pragma: no cover - compatibility shim
    unicode  # type: ignore[name-defined]
except NameError:  # Py3
    unicode = str  # type: ignore[assignment]

# Compatibility helpers (no version-specific static imports)
# HTML escape (minimal, sufficient for our generated content)


def _escape(s):
    if s is None:
        return ""
    # ensure type
    try:
        # For Py2 compatibility where str may be bytes
        if isinstance(s, bytes):
            s = s.decode("utf-8", "ignore")
    except Exception:
        pass
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


# URL quote per path segment


def _build_quote():
    try:
        if getattr(_sys, "version_info", (3, 0))[0] >= 3:
            mod = __import__("urllib.parse", fromlist=["parse"])
            return getattr(mod, "quote")
        else:
            mod = __import__("urllib", fromlist=[""])
            return getattr(mod, "quote")
    except Exception:
        # Fallback: minimal percent-encoder for non-safe ASCII
        safe = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-~"

        def _q(s):
            if isinstance(s, unicode):  # type: ignore  # Py2 only
                bs = s.encode("utf-8")
            elif isinstance(s, bytes):
                bs = s
            else:
                bs = str(s).encode("utf-8")
            out = []
            for b in bs:
                if isinstance(b, str):  # Py2: b is str length-1
                    b = ord(b)
                if b in safe:
                    out.append(chr(b))
                else:
                    out.append("%{:02X}".format(b))
            return "".join(out)

        return _q


_quote = _build_quote()

ROOT = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(ROOT, "index.html")

INCLUDE_EXT = {
    ".html",
    ".pdf",
    ".xlsx",
    ".xls",
    ".docx",
    ".doc",
    ".csv",
    ".png",
    ".jpg",
    ".jpeg",
    ".svg",
    ".ico",
}
EXCLUDE_DIRS = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    ".venv1",
    ".venv_fix",
    "__pycache__",
    "dist",
    "build",
    ".next",
    ".DS_Store",
    ".idea",
}
EXCLUDE_FILES = set()

# Do not list index.html itself
EXCLUDE_FILES.add(os.path.normpath(INDEX))


def is_excluded_path(path):
    parts = os.path.relpath(path, ROOT).split(os.sep)
    return any(p in EXCLUDE_DIRS for p in parts)


def rel_web_path(path):
    rel = os.path.relpath(path, ROOT)
    return rel.replace(os.sep, "/")


def web_href(path):
    # Encode each part to support spaces and non-Latin characters
    rel = rel_web_path(path)
    return "/".join(_quote(part) for part in rel.split("/"))


def human_size(num):
    size = float(num)
    for unit in ["بايت", "KB", "MB", "GB"]:
        if size < 1024.0 or unit == "GB":
            if unit == "بايت":
                return "{0} {1}".format(int(size), unit)
            return "{0:.1f} {1}".format(size, unit)
        size /= 1024.0
    # Fallback (should never get here due to 'GB' guard)
    return "{0} GB".format(int(size))


def fmt_time(ts):
    dt = datetime.datetime.fromtimestamp(ts)
    return dt.strftime("%Y-%m-%d %H:%M")


def collect_files():
    items = []
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if not is_excluded_path(os.path.join(base, d))]
        for f in files:
            full = os.path.join(base, f)
            if is_excluded_path(full):
                continue
            if os.path.normpath(full) in EXCLUDE_FILES:
                continue
            ext = os.path.splitext(f)[1].lower()
            if ext in INCLUDE_EXT:
                items.append(full)
    # Sort by path depth then lexicographically
    items.sort(key=lambda p: (rel_web_path(p).count("/"), rel_web_path(p).lower()))
    return items


def group_by_top(paths):
    groups = {}
    for p in paths:
        rel = rel_web_path(p)
        top = rel.split("/", 1)[0] if "/" in rel else "(الجذر)"
        groups.setdefault(top, []).append(p)
    # Sort groups by name, keeping (الجذر) first
    ordered = {}
    if "(الجذر)" in groups:
        ordered["(الجذر)"] = groups.pop("(الجذر)")
    for k in sorted(groups.keys(), key=lambda x: x.lower()):
        ordered[k] = groups[k]
    return ordered


def render_list(paths):
    groups = group_by_top(paths)
    blocks = []
    if not paths:
        return "        <p>لا توجد ملفات متاحة للعرض حاليًا.</p>"
    for group, files in groups.items():
        items_html = []
        for p in files:
            href = web_href(p)
            text = _escape(rel_web_path(p))
            st = os.stat(p)
            size = human_size(st.st_size)
            mtime = fmt_time(st.st_mtime)
            items_html.append(
                '          <li><a href="{0}" target="_blank" rel="noopener">{1}</a>'.format(
                    href, text
                )
                + ' <span class="meta">— حجم: {0} • آخر تعديل: {1}</span></li>'.format(size, mtime)
            )
        block = [
            "      <details open>",
            "        <summary>{0}</summary>".format(_escape(group)),
            "        <ul>",
            "\n".join(items_html),
            "        </ul>",
            "      </details>",
        ]
        blocks.append("\n".join(block))
    return "\n".join(blocks)


def update_index(rendered):
    if not os.path.exists(INDEX):
        raise SystemExit("index.html not found. Create it first.")
    with open(INDEX, "r", encoding="utf-8") as f:
        html_text = f.read()
    pattern = re.compile(
        r"(<!--\s*AUTO_LIST_START\s*-->)(.*?)(<!--\s*AUTO_LIST_END\s*-->)",
        re.S,
    )
    replacement = r"\1\n" + rendered + "\n" + r"\3"
    new_html, count = pattern.subn(replacement, html_text, count=1)
    if count == 0:
        raise SystemExit("Markers not found in index.html")
    with open(INDEX, "w", encoding="utf-8") as f:
        f.write(new_html)


def main():
    parser = argparse.ArgumentParser(
        description="Generate or check index.html content list.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help=("Check rendering only; do not modify index.html. Exit non-zero on " "problems."),
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Force writing index.html (default behavior if no flags).",
    )
    args = parser.parse_args()

    files = collect_files()
    content = render_list(files)

    if args.check and not args.write:
        # Validate markers exist and rendering succeeded
        if not os.path.exists(INDEX):
            print("index.html not found.")
            raise SystemExit(2)
        with open(INDEX, "r", encoding="utf-8") as f:
            html_text = f.read()
        if "AUTO_LIST_START" not in html_text or "AUTO_LIST_END" not in html_text:
            print("Markers not found in index.html")
            raise SystemExit(3)
        # Basic sanity: ensure content is not empty text (allow empty repo message)
        if not content.strip():
            print("Rendered content is empty.")
            raise SystemExit(4)
        print("Check passed. {0} items would be listed.".format(len(files)))
        return

    # Default: write changes
    update_index(content)
    print("Updated index.html with {0} items.".format(len(files)))


if __name__ == "__main__":
    main()
