#!/usr/bin/env python3
"""從 data/projects.yml 生成專案總頁與各專案獨立頁。

用法：python3 _scripts/gen_projects.py
產出：projects/index.qmd + projects/<id>.qmd + llms.txt
唯一資料源是 data/projects.yml，不要手改產出檔。
"""
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "projects.yml"
OUT_DIR = ROOT / "projects"

STATUS_LABEL = {"live": "運行中", "beta": "測試中", "coming": "建置中"}


def load_data():
    with open(DATA, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    for key in ("categories", "projects"):
        if key not in data:
            sys.exit(f"projects.yml 缺少 {key}")
    return data


def card_html(p):
    status = STATUS_LABEL.get(p["status"], p["status"])
    coming = p["status"] == "coming"
    cta = '' if coming else f'<span class="pcard-cta">{p["cta"]}</span>'
    inner = (
        f'<img src="/assets/images/{p["image"]}" alt="{p["name"]}" loading="lazy">'
        f'<div class="pcard-body"><div class="pcard-head">'
        f'<h3>{p["name"]}</h3>'
        f'<span class="badge badge-{p["status"]}">{status}</span></div>'
        f'<p class="pcard-tagline">{p["tagline"]}</p>{cta}</div>'
    )
    if coming:
        return f'<div class="pcard pcard-coming reveal-fx">{inner}</div>'
    return f'<a class="pcard reveal-fx" href="/projects/{p["id"]}.html">{inner}</a>'


def gen_listing(data):
    parts = [
        "---",
        'title: "運行中的專案"',
        "toc: false",
        "---",
        "",
        "站上陳列的每一件，都是每天在運轉的工作系統。",
        "",
    ]
    for cid, cat in data["categories"].items():
        items = [p for p in data["projects"] if p["category"] == cid]
        if not items:
            continue
        items.sort(key=lambda p: (p["status"] == "coming", not p["featured"]))
        parts.append(f'## {cat["name"]}')
        parts.append("")
        parts.append(cat["mission"])
        parts.append("")
        parts.append("```{=html}")
        parts.append('<div class="pgrid">')
        parts.extend(card_html(p) for p in items)
        parts.append("</div>")
        parts.append("```")
        parts.append("")
    (OUT_DIR / "index.qmd").write_text("\n".join(parts), encoding="utf-8")


def gen_detail(p, cat):
    status = STATUS_LABEL.get(p["status"], p["status"])
    entry_btn = ""
    if p.get("url") and p["url"] != "#":
        entry_btn = f'<a class="btn-primary" href="{p["url"]}">{p["cta"]}</a>'
    gains_html = "".join(f"<li>{g}</li>" for g in p.get("solves", []))
    audience_html = ""
    if p.get("audience"):
        audience_html = f'<p class="detail-audience">適合：{p["audience"]}</p>'
    lines = [
        "---",
        f'pagetitle: "{p["name"]} — AI Cooperation"',
        f'description: "{p["tagline"]}"',
        "page-layout: custom",
        "toc: false",
        "---",
        "",
        "```{=html}",
        '<article class="detail">',
        '<header class="detail-head reveal-fx">',
        f'<span class="badge badge-{p["status"]}">{status}</span>'
        f' <span class="badge badge-cat">{cat["name"]}</span>',
        f'<h1>{p["name"]}</h1>',
        f'<p class="detail-tagline">{p["tagline"]}</p>',
        audience_html,
        f'{entry_btn}',
        "</header>",
        f'<img class="detail-hero reveal-fx" src="/assets/images/{p["image"]}"'
        f' alt="{p["name"]}">',
    ]
    if p.get("problem"):
        lines += [
            '<section class="detail-block reveal-fx">',
            "<h2>你可能正卡在這裡</h2>",
            f"<p>{p['problem']}</p>",
            "</section>",
        ]
    if p.get("how"):
        lines += [
            '<section class="detail-block reveal-fx">',
            "<h2>這個系統怎麼解</h2>",
            f"<p>{p['how']}</p>",
            "</section>",
        ]
    tech_html = "".join(f"<li>{t}</li>" for t in p.get("tech", []))
    if tech_html:
        lines += [
            '<section class="detail-block reveal-fx">',
            "<h2>技術架構</h2>",
            f'<ul class="detail-gains">{tech_html}</ul>',
            "</section>",
        ]
    if gains_html:
        lines += [
            '<section class="detail-block reveal-fx">',
            "<h2>用了之後，解決什麼</h2>",
            f'<ul class="detail-gains">{gains_html}</ul>',
            "</section>",
        ]
    if p.get("start"):
        lines += [
            '<section class="detail-block reveal-fx">',
            "<h2>怎麼開始</h2>",
            f"<p>{p['start']}</p>",
            f'{entry_btn}',
            "</section>",
        ]
    lines += [
        '<p class="detail-back"><a href="/projects/">← 回專案總覽</a></p>',
        "</article>",
        "```",
        "",
    ]
    (OUT_DIR / f'{p["id"]}.qmd').write_text("\n".join(lines), encoding="utf-8")


def gen_llms_txt(data):
    lines = [
        "# AI Cooperation（cooperation.tw）",
        "",
        "> 打造人機協作的基礎架構。智慧人人可用，差距在協作的架構——",
        "> 這裡陳列的每個專案、每門課，都在真實運轉。",
        "",
        "## 專案",
        "",
    ]
    for cid, cat in data["categories"].items():
        items = [p for p in data["projects"]
                 if p["category"] == cid and p["status"] != "coming"]
        if not items:
            continue
        lines.append(f'### {cat["name"]}')
        for p in items:
            url = p["url"] if p.get("url") and p["url"] != "#" else \
                f'https://cooperation.tw/projects/{p["id"]}.html'
            lines.append(f'- [{p["name"]}]({url}): {p["tagline"]}')
        lines.append("")
    lines += [
        "## 聯絡",
        "",
        "- Email: ai@cooperation.tw",
        "- GitHub: https://github.com/ai-cooperation",
        "- 網站: https://cooperation.tw",
    ]
    (ROOT / "llms.txt").write_text("\n".join(lines), encoding="utf-8")


def main():
    data = load_data()
    OUT_DIR.mkdir(exist_ok=True)
    for old in OUT_DIR.glob("*.qmd"):
        old.unlink()
    gen_listing(data)
    for p in data["projects"]:
        if p["status"] != "coming":
            gen_detail(p, data["categories"][p["category"]])
    gen_llms_txt(data)
    live = sum(1 for p in data["projects"] if p["status"] != "coming")
    print(f"OK: listing + {live} detail pages + llms.txt")


if __name__ == "__main__":
    main()
