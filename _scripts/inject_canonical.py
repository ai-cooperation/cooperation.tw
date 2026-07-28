#!/usr/bin/env python3
"""Quarto post-render：對 _site 全部 HTML 注入 canonical，並把 sitemap 改寫成同款網址。

規則：index.html → 目錄網址（含尾斜線）；其他 → 保留 .html（全站內鏈都用 .html，
canonical 跟內鏈一致）。404.html 跳過。已有 canonical 的頁跳過。

sitemap.xml 的 <loc> 走同一個 canonical_from_rel()——Quarto 生成的 sitemap 一律列
實體檔案路徑（index.html），與 canonical 不一致會被 GSC 歸「替代頁面」，
單一函式同時餵兩邊，避免再分岔（2026-07-28 GSC 通知後補）。
"""
import re
from pathlib import Path

SITE_URL = "https://cooperation.tw"
SITE_DIR = Path(__file__).resolve().parent.parent / "_site"


def canonical_from_rel(rel: str) -> str:
    if rel == "index.html":
        return f"{SITE_URL}/"
    if rel.endswith("/index.html"):
        return f"{SITE_URL}/{rel[: -len('index.html')]}"
    return f"{SITE_URL}/{rel}"


def canonical_url(html_path: Path) -> str:
    return canonical_from_rel(html_path.relative_to(SITE_DIR).as_posix())


def rewrite_sitemap() -> None:
    sitemap = SITE_DIR / "sitemap.xml"
    if not sitemap.is_file():
        print("sitemap.xml 不存在，跳過改寫")
        return
    text = sitemap.read_text(encoding="utf-8")

    def repl(m: re.Match) -> str:
        return f"<loc>{canonical_from_rel(m.group(1))}</loc>"

    rewritten, count = re.subn(
        rf"<loc>{re.escape(SITE_URL)}/([^<]+)</loc>", repl, text
    )
    sitemap.write_text(rewritten, encoding="utf-8")
    print(f"sitemap locs rewritten: {count}")


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
    rewrite_sitemap()


if __name__ == "__main__":
    main()
