#!/usr/bin/env python3
import os, re, html
from urllib.parse import quote

ROOT = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(ROOT, "index.html")

INCLUDE_EXT = {
    ".html", ".pdf", ".xlsx", ".xls", ".docx", ".doc", ".csv",
    ".png", ".jpg", ".jpeg", ".svg", ".ico"
}
EXCLUDE_DIRS = {".git", "node_modules", "venv", "__pycache__", "dist", "build", ".next", ".DS_Store", ".idea"}
EXCLUDE_FILES = set()

# Do not list index.html itself
EXCLUDE_FILES.add(os.path.normpath(INDEX))


def is_excluded_path(path: str) -> bool:
    parts = os.path.relpath(path, ROOT).split(os.sep)
    return any(p in EXCLUDE_DIRS for p in parts)


def rel_web_path(path: str) -> str:
    rel = os.path.relpath(path, ROOT)
    return rel.replace(os.sep, "/")


def web_href(path: str) -> str:
    # Encode each part to support spaces and non-Latin characters
    rel = rel_web_path(path)
    return "/".join(quote(part) for part in rel.split("/"))


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


def render_list(paths):
    li = []
    for p in paths:
        href = web_href(p)
        text = html.escape(rel_web_path(p))
        li.append(f'        <li><a href="{href}" target="_blank" rel="noopener">{text}</a></li>')
    if not li:
        li = ['        <li>لا توجد ملفات متاحة للعرض حاليًا.</li>']
    return "\n".join(li)


def update_index(rendered: str):
    if not os.path.exists(INDEX):
        raise SystemExit("index.html not found. Create it first.")
    with open(INDEX, "r", encoding="utf-8") as f:
        html_text = f.read()
    pattern = re.compile(r"(<!--\s*AUTO_LIST_START\s*-->)(.*?)(<!--\s*AUTO_LIST_END\s*-->)", re.S)
    replacement = r"\1\n      <ul>\n" + rendered + "\n      </ul>\n      " + r"\3"
    new_html, count = pattern.subn(replacement, html_text, count=1)
    if count == 0:
        raise SystemExit("Markers not found in index.html")
    with open(INDEX, "w", encoding="utf-8") as f:
        f.write(new_html)


def main():
    files = collect_files()
    content = render_list(files)
    update_index(content)
    print(f"Updated index.html with {len(files)} items.")


if __name__ == "__main__":
    main()