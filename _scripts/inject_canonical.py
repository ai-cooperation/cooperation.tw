#!/usr/bin/env python3
"""Quarto post-render：對 _site 全部 HTML 注入 canonical。

規則：index.html → 目錄網址（含尾斜線）；其他 → 保留 .html（全站內鏈都用 .html，
canonical 跟內鏈一致）。404.html 跳過。已有 canonical 的頁跳過。
"""
from pathlib import Path

SITE_URL = "https://cooperation.tw"
SITE_DIR = Path(__file__).resolve().parent.parent / "_site"


def canonical_url(html_path: Path) -> str:
    rel = html_path.relative_to(SITE_DIR).as_posix()
    if rel == "index.html":
        return f"{SITE_URL}/"
    if rel.endswith("/index.html"):
        return f"{SITE_URL}/{rel[: -len('index.html')]}"
    return f"{SITE_URL}/{rel}"


def main() -> None:
    if not SITE_DIR.is_dir():
        raise SystemExit(f"_site 不存在：{SITE_DIR}")
    injected = skipped = 0
    for page in SITE_DIR.rglob("*.html"):
        if page.name == "404.html" or "site_libs" in page.parts:
            continue
        text = page.read_text(encoding="utf-8", errors="ignore")
        if 'rel="canonical"' in text or "</head>" not in text:
            skipped += 1
            continue
        tag = f'<link rel="canonical" href="{canonical_url(page)}">\n</head>'
        page.write_text(text.replace("</head>", tag, 1), encoding="utf-8")
        injected += 1
    print(f"canonical injected: {injected}, skipped: {skipped}")


if __name__ == "__main__":
    main()
