#!/usr/bin/env python3
"""從 data/tech-terms.yml + courses.yml + projects.yml 生成學習地圖頁。

用法：python3 _scripts/gen_method.py
產出：method/index.qmd
唯一資料源是上述三個 yml，不要手改產出檔。
"""
import sys
from html import escape
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "method"
AGENT_KB_URL = "https://agent-kb.cooperation.tw"

STATUS_LABEL = {"pilot": "預約試上", "planned": ""}

# 軸定義：白話一句 + 生活例子 + 對應作品（作品須是已上站的 live 專案）
AXIS_INFO = {
    "A": {
        "name": "看懂文件與影像",
        "define": "AI 幫你讀懂報告、照片、標籤與圖面，變成可以用的資訊。",
        "example": "拍一張食品標籤，就變成毛孩的飲食紀錄；一疊永續報告書，變成逐條對照原文出處的差距分析。",
        "projects": ["ifrs-s2", "medical-kb"],
    },
    "B": {
        "name": "把資料變成系統",
        "define": "把散落的表單與資料，變成會自動彙整的小系統。",
        "example": "同事用手機下單，後台自動整理成訂單表；22 間法院的公告，變成一張即時地圖。",
        "projects": ["foreclosure-map", "sustainability-platform"],
    },
    "C": {
        "name": "建自己的知識庫",
        "define": "建立可檢索、查得到來源的自家知識庫，重要判斷回查得到原文。",
        "example": "每天自動累積的產業情報，每一條都附來源；上課用的教材庫，AI 助手直接查得到。",
        "projects": ["insurance-kb", "agent-kb"],
    },
    "D": {
        "name": "讓 AI 自動運轉",
        "define": "讓 AI 照你定的規則自己跑：排程、監看、通知、產出。",
        "example": "研究想法丟進去，文獻、實驗、初稿整條管線自己跑完；生圖服務提交即回，背景慢慢算。",
        "projects": ["paperlab", "fluxgate"],
    },
}

FOUNDATION = """<section class="home-section">
<h2 class="reveal-fx">兩個底功 每門課都練</h2>
<div class="steps-grid steps-grid-2">
<div class="step-item reveal-fx"><h3>把需求說清楚</h3><p>AI 做得好不好，八成取決於你把問題說得清不清楚。需求拆解與提問方法是每門課的第一課。</p></div>
<div class="step-item reveal-fx" style="--rd:.08s"><h3>驗收與風險判斷</h3><p>AI 的產出不等於可以用。每門課都教你驗收自己的作品：哪裡要查證、哪裡是系統做不到的。</p></div>
</div>
</section>"""



def load(name: str) -> Any:
    try:
        with open(ROOT / "data" / name, encoding="utf-8") as f:
            return yaml.safe_load(f)
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        sys.exit(f"無法讀取 {name}：{exc}")


def course_chip(c: dict[str, Any]) -> str:
    # 僅開放試上課程掛「預約試上」徽章；未開課課程不掛標籤。
    badge = ('<span class="badge badge-pilot">預約試上</span>'
             if c["status"] == "pilot" else "")
    return (f'<a class="proof-card" href="/courses/{c["id"]}.html">'
            f'<h3>{escape(c["name"])}</h3>'
            f'<p>{escape(c["tagline"])}</p>{badge}</a>')


def project_chip(p: dict[str, Any]) -> str:
    return (f'<a class="proof-card" href="/projects/{p["id"]}.html">'
            f'<h3>{escape(p["name"])}</h3>'
            f'<p>{escape(p["tagline"])}</p>'
            '<span class="pcard-cta">看這個系統 →</span></a>')


def axis_section(aid: str, courses: list[dict], projects: dict,
                 axis_terms: dict[str, list[str]]) -> str:
    info = AXIS_INFO[aid]
    mine = [c for c in courses if aid in c.get("axes", [])]
    course_cards = "".join(course_chip(c) for c in mine)
    proj_cards = []
    for pid in info["projects"]:
        proj = projects.get(pid)
        if proj is None or proj.get("status") == "coming":
            sys.exit(f"AXIS_INFO {aid}.projects 含無效或未上站的專案：{pid}")
        proj_cards.append(project_chip(proj))
    terms = "、".join(axis_terms.get(aid, []))
    tech_line = (f'<p class="axis-tech">背後技術：{escape(terms)}</p>'
                 if terms else "")
    return f"""<section class="home-section" id="axis-{aid.lower()}">
<h2 class="reveal-fx">{aid}　{escape(info["name"])}</h2>
<p class="section-lead reveal-fx">{escape(info["define"])}<br>{escape(info["example"])}</p>
<img class="axis-visual reveal-fx" src="/assets/images/axis-{aid.lower()}.png" alt="{escape(info["name"])}" loading="lazy">
<h3 class="cgroup-label reveal-fx">練這個能力的課</h3>
<div class="proof-grid cols-{min(len(mine), 2)}">{course_cards}</div>
<h3 class="cgroup-label reveal-fx">用這個能力做出來的系統</h3>
<div class="proof-grid cols-{min(len(proj_cards), 2)}">{"".join(proj_cards)}</div>
{tech_line}
</section>"""


def ladder_section(levels: list[dict[str, Any]]) -> str:
    rows = []
    for lv in levels:
        chips = "".join(
            f'<span class="term-chip">{escape(t["label"])}</span>'
            for t in lv["terms"])
        rows.append(
            f'<div class="ladder-row reveal-fx"><div class="ladder-head">'
            f'<h3>{escape(lv["name"])}</h3>'
            f'<p class="ladder-stage">{escape(lv["stage"])}</p></div>'
            f'<div class="ladder-body"><p>{escape(lv["plain"])}</p>'
            f'<div class="term-row">{chips}</div></div></div>')
    return f"""<section class="home-section" id="ladder">
<h2 class="reveal-fx">往深走的路徑</h2>
<p class="section-lead reveal-fx">四個能力都能從 Level 1 走到 Level 3。每一級列出你會接觸到的詞——看不懂沒關係，到那一級自然會懂。</p>
<div class="ladder">{"".join(rows)}</div>
<p class="reveal-fx">每個詞的白話定義、應用場景與相關案例，都在
<a href="{AGENT_KB_URL}">Agent KB 概念字典</a>——學員上課用的同一套知識庫。</p>
</section>"""


def main() -> None:
    terms_data = load("tech-terms.yml")
    courses = load("courses.yml")["courses"]
    projects = {p["id"]: p for p in load("projects.yml")["projects"]}
    axis_terms = {a["id"]: a["terms"] for a in terms_data.get("axes", [])}

    parts = [
        "---",
        'pagetitle: "AI 學習地圖｜四個關鍵能力與三級深度"',
        'description: "AI Cooperation 的學習方法：看懂文件與影像、把資料變成系統、建自己的知識庫、讓 AI 自動運轉——四個關鍵能力、三級深度，每一級的課程與真實系統對照。"',
        "page-layout: custom",
        "toc: false",
        "---",
        "",
        "```{=html}",
        """<section class="hero hero-lite hero-lines">
<div class="hero-inner">
<span class="hero-kicker reveal-fx">學習地圖</span>
<h1 class="reveal-fx" style="--rd:.05s">四個關鍵能力<br>三級深度</h1>
<p class="hero-sub reveal-fx" style="--rd:.15s">情境是入口 <br class="br-m">能力才是你帶走的東西<br>每個能力都有課可以練 <br class="br-m">有真實系統當證據</p>
</div>
</section>""",
        FOUNDATION,
    ]
    for aid in ("A", "B", "C", "D"):
        parts.append(axis_section(aid, courses, projects, axis_terms))
    parts.append(ladder_section(terms_data["levels"]))
    parts.append("""<section class="ent-band">
<div class="ent-inner reveal-fx">
<div>
<h2>想一次走完整條路徑</h2>
<p class="ent-lead">企業內訓六小時走完四階段</p>
<p>用你們自己的工作流程當教材，從會使用到會設計，結業交付部門可以直接用的改善方案。</p>
<p class="ent-specs">小班實作｜六小時四階段｜學員無須程式背景</p>
</div>
<a class="btn-primary" href="/apply/enterprise.html">洽詢內訓方案</a>
</div>
</section>""")
    parts += ["```", ""]
    OUT_DIR.mkdir(exist_ok=True)
    (OUT_DIR / "index.qmd").write_text("\n".join(parts), encoding="utf-8")
    print("完成：method/index.qmd")


if __name__ == "__main__":
    main()
